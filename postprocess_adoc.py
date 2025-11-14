import os
import re
import codecs
import datetime
import chardet
from pathlib import Path

SRC_DIR = "translated"
DST_DIR = "final"
LOG_FILE = "postprocess_log.txt"

os.makedirs(DST_DIR, exist_ok=True)

stats = {"processed": 0, "errors": 0, "skipped": 0}

def log(msg):
    """Append a line to the log file and print to console."""
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as log_f:
        log_f.write(msg + "\n")

def detect_and_convert_to_utf8(file_path):
    """Detect encoding and return UTF-8 text content."""
    with open(file_path, "rb") as f:
        raw_data = f.read()
    detection = chardet.detect(raw_data)
    encoding = detection["encoding"] or "utf-8"
    confidence = detection.get("confidence", 0)

    try:
        text = raw_data.decode(encoding)
        log(f"✅ {file_path} decoded successfully as {encoding} ({confidence:.2f})")
    except (UnicodeDecodeError, LookupError):
        stats["errors"] += 1
        log(f"⚠️ {file_path} could not be decoded as {encoding}, forcing UTF-8 replacement.")
        text = raw_data.decode("utf-8", errors="replace")

    return text

def revert_backticks(match):
    """Revert literal monospaced (`+code+`) → simple monospaced (`code`) safely."""
    inner = match.group(1).strip()

    # Context-aware check: revert if it looks like real code, not punctuation or quote
    if re.search(r'[A-Za-z0-9._/\-]', inner):
        return f"`{inner}`"
    else:
        stats["skipped"] += 1
        return f"`+{inner}+`"

# Start new log file
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"Postprocess started: {datetime.datetime.now()}\n\n")

# Walk through translated directory
for root, _, files in os.walk(SRC_DIR):
    for file in files:
        if not file.endswith(".adoc"):
            continue

        src_path = os.path.join(root, file)
        rel_path = os.path.relpath(src_path, SRC_DIR)
        dst_path = os.path.join(DST_DIR, rel_path)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        # Read & normalize encoding
        content = detect_and_convert_to_utf8(src_path)

        # 1. Revert literal monospaced → simple monospaced (handles embedded +)
        content = re.sub(r'`\+(.*?)\+`', revert_backticks, content)

        # 2. Revert [literal]#text# → [monospaced]#text#
        content = re.sub(r'\[literal\]#([^#]+)#', r'[monospaced]#\1#', content, flags=re.IGNORECASE)

        # 3. Normalize line endings and ensure UTF-8 encoding
        content = content.replace("\r\n", "\n").encode("utf-8", errors="ignore").decode("utf-8").replace("\r", "\n")

        # Save final files --- Save clean UTF-8 (LF) explicitly ---
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)


        log(f"📝 Saved {dst_path} as UTF-8 (LF) — final restored from {src_path}")
        stats["processed"] += 1

# Write summary
log("\nSummary:")
log(f"  ✅ Final Files restored: {stats['processed']}")
log(f"  ⚠️ Encoding errors fixed: {stats['errors']}")
log(f"  ⏩ Skipped non-code reverts: {stats['skipped']}")
log(f"\nCompleted: {datetime.datetime.now()}")
