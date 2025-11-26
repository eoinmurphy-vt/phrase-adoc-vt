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

    text = text.replace("\r\n", "\n").replace("\r", "\n")      # Force LF only
    text = re.sub(r'\u00A0', ' ', text)                      # Non-breaking space
    text = re.sub(r'\t', '    ', text)                       # Tabs → spaces
    text = re.sub(r'[ ]{2,}$', '', text, flags=re.MULTILINE) # Trailing spaces

    if text != before:
        stats["normalized"] += 1

    return text


def preprocess_content(text: str) -> str:
    """
    Minimal, safe transformations:
    1) Quoted backticks -> &quot;`+...+`&quot;  (only if inner not already plus-wrapped)
    2) Unquoted backticks -> `+...+`          (only if inner not already plus-wrapped)
    3) [monospaced]#x# -> [literal]#x#
    """

    # ---- 1) Quoted backtick spans
    # Match: a double quote, optional whitespace, a backtick, inner (no backtick),
    #        backtick, optional whitespace, closing double quote.
    # We only match if the inner does NOT start or end with '+' (avoid reprocessing).
    #
    # Regex explanation:
    #   "            opening double quote
    #   \s*`         optional spaces then a backtick
    #   (?!\+)([^`]*?)(?<!\+)   capture inner that doesn't start or end with '+'
    #   `\s*"        closing backtick, optional spaces, closing double quote
    #
    # Replacement: &quot;`+inner+`&quot;
    quoted_pattern = re.compile(r'"\s*`(?!\+)([^`]+?)(?<!\+)`\s*"', flags=re.DOTALL)
    text = quoted_pattern.sub(lambda m: f'&quot;`+{m.group(1)}+`&quot;', text)

    # ---- 2) Unquoted backtick spans (remaining)
    # Match lone `...` where inner does not start or end with '+'
    # This avoids double-wrapping already-processed `+...+` or `+`+ cases.
    inline_pattern = re.compile(r'`(?!\+)([^`]+?)(?<!\+)`', flags=re.DOTALL)
    text = inline_pattern.sub(r'`+\1+`', text)

    # ---- 3) monospaced → literal (unchanged)
    text = re.sub(r'\[monospaced\]#([^#]+)#', r'[literal]#\1#', text, flags=re.IGNORECASE)

    return text


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
    text = preprocess_content(text)

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
