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
    Convert:
      de_de/docs/.../modules/en/pages/file.adoc
    Into:
      docs/.../modules/de/pages/file.adoc
    """

    # Detect language folder
    lang_folder = rel.split(os.sep)[0]  # de_de or fr_fr
    lang_code = lang_folder.split("_")[0]  # de, fr, it, es, etc.

    # Strip language prefix folder
    rel = os.path.join(*rel.split(os.sep)[1:])

    # Replace modules/en/ with modules/<lang_code>/
    rel = rel.replace("/modules/en/", f"/modules/{lang_code}/")

    # Construct final path
    return os.path.join(DST_DIR, rel)

# Start log
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"Postprocess started: {datetime.datetime.now()}\n\n")


# Walk all language folders recursively
for path in Path(SRC_DIR).rglob("*.adoc"):
    src_path = str(path)
    rel = os.path.relpath(src_path, SRC_DIR)

    # language folder → correct docs/modules/<lang>/
    dst_path = map_output_path(src_path, rel)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    text = detect_and_convert_to_utf8(src_path)
    text = cleanup_text(text)

    with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    stats["processed"] += 1
    log(f"✓ Restored {dst_path} (from {src_path})")


# Summary
log("\nSummary:")
log(f"  ✅ Processed files: {stats['processed']}")
log(f"  ⚠️ Encoding errors fixed: {stats['errors']}")
log(f"  ✅ Cleaned files: {stats['cleaned']}")
log(f"\nCompleted: {datetime.datetime.now()}")