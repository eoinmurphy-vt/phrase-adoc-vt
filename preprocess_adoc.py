import os, re, codecs, datetime, chardet

SRC_DIR = "source"
DST_DIR = "processed"
LOG_FILE = "preprocess_log.txt"

os.makedirs(DST_DIR, exist_ok=True)

stats = {"processed": 0, "errors": 0, "skipped": 0}

def log(msg):
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

def replace_backticks(match):
    inner = match.group(1)

    # Skip apostrophe-like usage (e.g., It`s)
    if re.search(r"\w`\w", inner):
        stats["skipped"] += 1
        return f"`{inner}`"

    # Skip if no code-like patterns
    if not re.search(r'[A-Z]|\.|_|/|-|\d', inner):
        stats["skipped"] += 1
        return f"`{inner}`"

    # Convert to literal monospaced
    return f"`+{inner}+`"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"Preprocess started: {datetime.datetime.now()}\n\n")

for root, _, files in os.walk(SRC_DIR):
    for file in files:
        if not file.endswith(".adoc"):
            continue

        src_path = os.path.join(root, file)
        rel_path = os.path.relpath(src_path, SRC_DIR)
        dst_path = os.path.join(DST_DIR, rel_path)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        content = detect_and_convert_to_utf8(src_path)

        # 1. Convert backticks → literal monospaced
        content = re.sub(r'`([^`\n]+)`', replace_backticks, content)

        # 2. Convert [monospaced]#text# → [literal]#text#
        content = re.sub(r'\[monospaced\]#([^#]+)#', r'[literal]#\1#', content, flags=re.IGNORECASE)

        # 3. Normalize UTF-8 line endings
        content = content.replace("\r\n", "\n").encode("utf-8", errors="ignore").decode("utf-8")

        with codecs.open(dst_path, "w", encoding="utf-8") as f:
            f.write(content)

        log(f"Processed: {src_path} → {dst_path}")
        stats["processed"] += 1

log("\nSummary:")
log(f"  ✅ Files processed: {stats['processed']}")
log(f"  ⚠️ Encoding errors fixed: {stats['errors']}")
log(f"  ⏩ Backticks skipped (apostrophes/plain): {stats['skipped']}")
log(f"\nCompleted: {datetime.datetime.now()}")
