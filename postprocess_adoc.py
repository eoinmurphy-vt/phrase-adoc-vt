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
    "skipped": 0,
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


BACKTICK_PATTERNS = [
    # Handles quoted form:  &quot;`+text+`&quot;
    (r'&quot;`\+(.+?)\+`&quot;', r"`\1`"),

    # Handles: `+text+`
    (r'`\+(.+?)\+`', r"`\1`"),

    # Handles: +`text`+
    (r'\+`(.+?)`\+', r"`\1`"),
]


def revert_backtick_wrapping(text):
    before = text
    for pattern, replacement in BACKTICK_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def cleanup_text(text):
    before = text

    # Reverse preprocessed backtick logic
    text = revert_backtick_wrapping(text)

    # literal → monospaced (existing behaviour)
    text = re.sub(
        r'\[literal\]#([^#]+)#',
        r'[monospaced]#\1#',
        text,
        flags=re.IGNORECASE
    )

    # Remove "+word+" artifacts
    text = re.sub(r'\+([A-Za-z0-9/_\.-]+)\+', r'\1', text)

    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove trailing spaces
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
log(f"  ⏩ Skipped non-code reverts: {stats['skipped']}")
log(f"  ✅ Cleaned files: {stats['cleaned']}")
log(f"\nCompleted: {datetime.datetime.now()}")
