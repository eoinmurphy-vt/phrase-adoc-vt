import os
import re
import datetime
import chardet
from pathlib import Path

# --- CONFIGURATION FROM ENV VARS ---
# We read from environment variables, falling back to defaults if not set.
SRC_DIR = os.getenv("SRC_DIR", "translated")
DST_DIR = os.getenv("DST_DIR", "final")
LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DST_DIR, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
run_id = os.getenv("GITHUB_RUN_ID", "local")
LOG_FILE = f"{LOG_DIR}/postprocess_log_{timestamp}_{run_id}.txt"

stats = {
    "processed": 0,
    "errors": 0,
    "skipped": 0, # Note: This stat is no longer relevant as the revert_backticks function is removed
    "cleaned": 0,
}


def log(msg):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def detect_and_convert_to_utf8(file_path):
    with open(file_path, "rb") as f:
        raw = f.read()

    info = chardet.detect(raw)
    encoding = info.get("encoding") or "utf-8"
    confidence = info.get("confidence", 0)

    try:
        text = raw.decode(encoding)
        log(f"✓ {file_path} decoded as {encoding} ({confidence:.2f})")
    except Exception:
        stats["errors"] += 1
        log(f"⚠ Decode failed for {encoding}, forcing UTF-8 replacement")
        text = raw.decode("utf-8", errors="replace")

    return text


# --- OBSOLETE FUNCTION REMOVED: revert_backticks() ---


def cleanup_text(text):
    """
    Performs post-translation cleanup, utilizing the robust revert logic
    to restore literal monospace back to standard AsciiDoc.
    """
    before = text

    # --- STEP 1: REVERT ENTITIES (Double Quotes) ---
    # Finds: &quot;`+CONTENT+`&quot;
    # Replaces with: "`CONTENT`"
    # Matches: Entity + Backtick + Plus + Content (No Newlines) + Plus + Backtick + Entity
    pattern_dq = re.compile(r'&quot;\`\+([^\`\n]+)\+\`&quot;')
    text = pattern_dq.sub(r'"`\1`"', text)


    # --- STEP 2: REVERT ENTITIES (Single Quotes) ---
    # Finds: &apos;`+CONTENT+`&apos;
    # Replaces with: '`CONTENT`'
    pattern_sq = re.compile(r'&apos;\`\+([^\`\n]+)\+\`&apos;')
    text = pattern_sq.sub(r"'`\1`'", text)


    # --- STEP 3: REVERT PLAIN WRAPPERS ---
    # Finds: `+CONTENT+`
    # Replaces with: `CONTENT`
    # This catches any remaining blocks that weren't quoted.
    pattern_plain = re.compile(r'\`\+([^\`\n]+)\+\`')
    text = pattern_plain.sub(r'`\1`', text)


    # --- STEP 4: OTHER CLEANUP TASKS (Preserved from original) ---

    # Convert [literal]#text# back to monospaced
    text = re.sub(r'\[literal\]#([^#]+)#', r'[monospaced]#\1#', text, flags=re.IGNORECASE)

    # Collapse weird "+word+" inserts produced by translation tools
    text = re.sub(r'\+([A-Za-z0-9/_\.-]+)\+', r'\1', text)

    # Normalize line endings + remove stray CR
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove repeated whitespace or accidental duplicates
    text = re.sub(r'[ ]{2,}$', '', text, flags=re.MULTILINE)

    if text != before:
        stats["cleaned"] += 1

    return text


def map_output_path(src_path: str, rel: str) -> str:
    """
    Smart Path Mapper.
    Detects language folders (e.g., de_de) and maps them to standard structure.
    """
    parts = rel.split(os.sep)

    # Check if the first folder looks like a locale (e.g., de_de, fr_fr)
    if len(parts) > 1 and (len(parts[0]) == 5 and "_" in parts[0]):
        lang_folder = parts[0]   # e.g., de_de
        lang_code = lang_folder.split("_")[0] # e.g., de

        # Strip language prefix folder
        new_rel_parts = parts[1:]
        new_rel = os.path.join(*new_rel_parts)

        # Replace modules/en/ with modules/<lang_code>/ if present
        if "/modules/en/" in f"/{new_rel}".replace("\\", "/"):
             new_rel = new_rel.replace("/modules/en/", f"/modules/{lang_code}/").replace("\\modules\\en\\", f"\\modules\\{lang_code}\\")
        
        return os.path.join(DST_DIR, new_rel)
    
    else:
        # Fallback: Just mirror the path
        return os.path.join(DST_DIR, rel)


# --- MAIN EXECUTION START ---

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"Postprocess started: {datetime.datetime.now()}\n\n")

# Logic to handle missing 'translated' folder (root push)
scan_path = Path(SRC_DIR)
is_fallback = False

if not scan_path.exists():
    log(f"⚠️  Folder '{SRC_DIR}' not found. Phrase likely pushed to root.")
    log("🔄  Switching to scan current directory for language folders (xx_xx)...")
    scan_path = Path(".")
    is_fallback = True
else:
    log(f"📂  Scanning configured directory: {SRC_DIR}")

# Walk recursively
file_count = 0
for path in scan_path.rglob("*.adoc"):
    # SKIP: The destination directory itself
    if str(path).startswith(DST_DIR) or str(path).startswith(f"./{DST_DIR}"):
        continue
    # SKIP: Hidden git folders
    if ".git" in str(path):
        continue
    # SKIP: Source directory if we are in fallback mode (don't process English source)
    if is_fallback and "source" in str(path):
        continue

    # Determine relative path for mapping
    if is_fallback:
        # If scanning root, rel path is just the path (e.g., fr_fr/docs/...)
        rel = str(path)
        # FILTER: If running at root, ONLY process paths starting with a lang code pattern
        # This prevents processing random READMEs or scripts.
        if not re.match(r'^[a-z]{2}_[a-z]{2}', str(path)):
            continue
    else:
        rel = os.path.relpath(str(path), SRC_DIR)

    file_count += 1
    dst_path = map_output_path(str(path), rel)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    text = detect_and_convert_to_utf8(str(path))
    text = cleanup_text(text)

    with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    stats["processed"] += 1
    log(f"✓ Restored {dst_path} (from {path})")

if file_count == 0:
    log(f"❌ No .adoc files processed. Checked '{SRC_DIR}' and fallback patterns.")

# Summary
log("\nSummary:")
log(f"  ✅ Processed files: {stats['processed']}")
log(f"  ⚠️ Encoding errors fixed: {stats['errors']}")
log(f"  ✅ Cleaned files: {stats['cleaned']}")
log(f"\nCompleted: {datetime.datetime.now()}")