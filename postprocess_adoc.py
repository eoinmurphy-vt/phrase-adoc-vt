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
    Also replaces 'modules/en' with 'modules/{lang_code}'.
    """
    parts = rel.split(os.sep)

    # Check if the first folder looks like a locale (e.g., de_de, fr_fr)
    if len(parts) > 0 and (len(parts[0]) == 5 and "_" in parts[0]):
        lang_folder = parts[0]   # e.g., de_de
        lang_code = lang_folder.split("_")[0] # e.g., de

        # Strip language prefix folder
        new_rel_parts = parts[1:]
        
        # Build path string from parts
        new_rel = os.path.join(*new_rel_parts)

        # Normalize path separators to forward slashes for string replacement checks
        normalized_path = new_rel.replace("\\", "/")
        
        # Replace modules/en/ with modules/<lang_code>/ if present
        if "modules/en" in normalized_path:
             normalized_path = normalized_path.replace("modules/en", f"modules/{lang_code}")
        
        # Convert back to OS separator if needed
        final_rel = normalized_path.replace("/", os.sep)
        
        return os.path.join(DST_DIR, final_rel)
    
    else:
        # Fallback: Just mirror the path
        return os.path.join(DST_DIR, rel)


# --- MAIN EXECUTION LOGIC ---

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
# IMPORTANT: When scanning root, exclude common non-content folders to be safe
EXCLUDED_DIRS = {'.git', '.github', 'logs', 'scripts', 'final', 'processed', 'source', 'node_modules'}

for root, dirs, files in os.walk(scan_path):
    # In-place modification of dirs to skip excluded folders
    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
    
    for filename in files:
        if not filename.endswith(".adoc"):
            continue
            
        # Full path to source file
        full_path = os.path.join(root, filename)
        
        # Determine relative path for mapping
        if is_fallback:
            # If scanning root, rel path starts from root (e.g., fr_fr/docs/...)
            rel = os.path.relpath(full_path, ".")
            # FILTER: If running at root, ONLY process paths starting with a lang code pattern
            # This prevents processing random READMEs or scripts.
            # Checks for pattern: 2 letters + underscore + 2 letters (e.g., fr_fr) at start
            first_folder = rel.split(os.sep)[0]
            if not re.match(r'^[a-z]{2}_[a-z]{2}', first_folder):
                continue
        else:
            rel = os.path.relpath(full_path, SRC_DIR)

        file_count += 1
        dst_path = map_output_path(full_path, rel)

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        text = detect_and_convert_to_utf8(full_path)
        text = cleanup_text(text)

        with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

        stats["processed"] += 1
        log(f"✓ Restored {dst_path} (from {full_path})")

if file_count == 0:
    log(f"❌ No .adoc files processed. Checked '{SRC_DIR}' and fallback patterns.")

# Summary
log("\nSummary:")
log(f"  ✅ Processed files: {stats['processed']}")
log(f"  ⚠️ Encoding errors fixed: {stats['errors']}")
log(f"  ✅ Cleaned files: {stats['cleaned']}")
log(f"\nCompleted: {datetime.datetime.now()}")