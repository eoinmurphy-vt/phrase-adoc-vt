import os
import re
import datetime
import chardet
from pathlib import Path

SRC_DIR = "translated"
DST_DIR = "final"
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
    Performs post-translation cleanup, including the full reversal of the 
    literal monospace and entity conversion.
    """
    before = text

    # --- START: REVERT MONOSPACE AND ENTITIES (The new, robust logic) ---

    # 1. Revert Quoted Double Entity: &quot;`+text+`&quot; -> "`text`"
    # Note: We must ensure the backticks are included in the replacement.
    pattern_double_quote = r'&quot;`\+([^`+]+)\+`&quot;'
    text = re.sub(pattern_double_quote, r'"\g<1>"', text)

    # 2. Revert Quoted Single Entity: &apos;`+text+`&apos; -> '`text`'
    pattern_single_quote = r'&apos;`\+([^`+]+)\+`&apos;'
    text = re.sub(pattern_single_quote, r"'\g<1>'", text)

    # 3. Revert Plain Literal Monospace: `+text+` -> `text`
    # This also acts as a final cleanup for residual `+` marks.
    pattern_plain = r'`\+([^`+]+)\+`'
    text = re.sub(pattern_plain, r'`\g<1>`', text)
    
    # --- END: REVERT MONOSPACE AND ENTITIES ---

    # Convert [literal]#text# back to monospaced (Kept from original logic)
    text = re.sub(r'\[literal\]#([^#]+)#', r'[monospaced]#\1#', text, flags=re.IGNORECASE)

    # Collapse weird "+word+" inserts produced by translation (Kept from original logic)
    text = re.sub(r'\+([A-Za-z0-9/_\.-]+)\+', r'\1', text)

    # Note: The original line `text = re.sub(r'&quot;(`[^`]+`)&quot;', r'"\1"', text)` is now 
    # redundant because of step 1, but we keep the logic that follows it:
    
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
    text = cleanup_text(text) # <--- The updated cleanup function is called here

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