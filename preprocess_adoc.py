import os
import sys
import re
import chardet
import datetime
from pathlib import Path

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
run_id = os.getenv("GITHUB_RUN_ID", "local")
LOG_FILE = f"{LOG_DIR}/preprocess_log_{timestamp}_{run_id}.txt"

stats = {"processed": 0, "errors": 0, "normalized": 0}


def log(msg: str):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as logf:
        logf.write(msg + "\n")


def detect_and_read_utf8(path):
    """Detect encoding and return text decoded as UTF-8."""
    with open(path, "rb") as f:
        raw = f.read()

    info = chardet.detect(raw)
    encoding = info.get("encoding") or "utf-8"
    confidence = info.get("confidence", 0)

    try:
        text = raw.decode(encoding)
        log(f"✓ Decoded {path} as {encoding} ({confidence:.2f})")
    except Exception:
        log(f"⚠ Decode failed ({encoding}), forcing UTF-8 replacement")
        stats["errors"] += 1
        text = raw.decode("utf-8", errors="replace")

    return text


def normalize_ascii(text: str) -> str:
    """Basic cleanup: normalize whitespace, fix accidental CRLF, sanitize soft breaks."""
    before = text

    text = text.replace("\r\n", "\n").replace("\r", "\n")        # Force LF only
    text = re.sub(r'\u00A0', ' ', text)                          # Non-breaking space
    text = re.sub(r'\t', '    ', text)                           # Tabs → spaces
    text = re.sub(r'[ ]{2,}$', '', text, flags=re.MULTILINE)     # Trailing spaces

    if text != before:
        stats["normalized"] += 1

    return text


def preprocess_content(text: str) -> str:
    """Light transformations for translation prep: Convert monospace to literal (+...+) 
    and encode surrounding quotes to entities."""
    
    # --- START OF REPLACEMENT LOGIC ---
    
    # Regex Breakdown:
    # (['"]?)   : Group 1 - Match an optional quote (' or ")
    # `         : Match a literal backtick
    # ([^`]+)   : Group 2 - Match content inside (not backticks)
    # `         : Match a literal closing backtick
    # \1        : Match whatever was captured in Group 1 (the matching closing quote)
    
    pattern = r"(['\"]?)`([^`]+)`\1"

    def replacement_func(match):
        quote = match.group(1)   # The quote found (or empty string)
        content = match.group(2) # The text inside the backticks
        
        # 1. Ensure content is wrapped in +...+, avoiding double wrapping
        if content.startswith('+') and content.endswith('+'):
            inner = content
        else:
            inner = f"+{content}+"

        # 2. Check the surrounding quote and convert to entity
        if quote == '"':
            # Case: "`text`" -> &quot;`+text+`&quot;
            return f'&quot;`{inner}`&quot;'
        elif quote == "'":
            # Case: '`text`' -> &apos;`+text+`&apos;
            return f'&apos;`{inner}`&apos;'
        else:
            # Case: `text` -> `+text+` (No quotes)
            return f'`{inner}`'

    # Substitute using the callback function
    return re.sub(pattern, replacement_func, text)

    # --- END OF REPLACEMENT LOGIC ---


def main():
    if len(sys.argv) < 2:
        log("ERROR: No input file provided.")
        sys.exit(1)

    src_file = sys.argv[1]
    if not os.path.isfile(src_file):
        log(f"ERROR: File does not exist: {src_file}")
        sys.exit(1)

    log(f"Starting preprocess: {src_file}")

    # Compute output path (mirror directory structure)
    rel_path = os.path.relpath(src_file, "source")
    out_path = os.path.join("processed", rel_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    text = detect_and_read_utf8(src_file)
    text = normalize_ascii(text)
    text = preprocess_content(text) # <--- The updated function is called here

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    stats["processed"] += 1
    log(f"Saved processed file → {out_path}")

    # Summary
    log("\nSummary:")
    log(f"  ✅ Processed: {stats['processed']}")
    log(f"  ⚠️ Encoding issues fixed: {stats['errors']}")
    log(f"  ✅ Normalized files: {stats['normalized']}")

    log(f"\nCompleted at {datetime.datetime.now()}")


if __name__ == "__main__":
    main()