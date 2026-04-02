#!/usr/bin/env python3
"""
Extract subtitles from Bilibili or YouTube video URLs using yt-dlp.
Saves subtitles as a plain .txt file in the current directory.

Usage:
    python extract_subtitles.py <video_url> [--output-dir <dir>] [--lang <lang_code>]

Examples:
    python extract_subtitles.py https://www.bilibili.com/video/BV1xx411c7mD
    python extract_subtitles.py https://www.youtube.com/watch?v=dQw4w9WgXcQ --lang en
    python extract_subtitles.py https://youtu.be/dQw4w9WgXcQ --output-dir C:/subtitles
"""

import argparse
import io
import os
import re
import subprocess
import sys
import glob
import tempfile

# Fix Windows console encoding so all Unicode prints succeed
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def detect_platform(url: str) -> str:
    if "bilibili.com" in url or "b23.tv" in url:
        return "bilibili"
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    return "unknown"


def srt_to_text(srt_content: str) -> str:
    """Convert SRT subtitle content to plain text, removing timestamps and indices."""
    lines = srt_content.splitlines()
    text_lines = []
    skip_next = False

    for line in lines:
        line = line.strip()
        # Skip numeric indices
        if re.match(r"^\d+$", line):
            skip_next = True
            continue
        # Skip timestamp lines
        if re.match(r"^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}", line):
            skip_next = False
            continue
        # Skip empty lines (used as separators)
        if not line:
            if text_lines and text_lines[-1] != "":
                text_lines.append("")
            continue
        if skip_next:
            skip_next = False
            continue
        # Remove HTML tags (e.g. <i>, <b>, <font ...>)
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            text_lines.append(line)

    # Collapse multiple blank lines
    result = []
    prev_blank = False
    for line in text_lines:
        if line == "":
            if not prev_blank:
                result.append("")
            prev_blank = True
        else:
            result.append(line)
            prev_blank = False

    return "\n".join(result).strip()


def vtt_to_text(vtt_content: str) -> str:
    """Convert WebVTT subtitle content to plain text."""
    lines = vtt_content.splitlines()
    text_lines = []

    for line in lines:
        line = line.strip()
        if line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        # Skip VTT metadata headers (Kind: captions, Language: en, etc.)
        if re.match(r"^(Kind|Language|Position|Align|Size|Line)\s*:", line):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}[\.,]\d{3}\s*-->\s*", line) or \
           re.match(r"^\d{2}:\d{2}[\.,]\d{3}\s*-->\s*", line):
            continue
        if re.match(r"^\d+$", line):
            continue
        if not line:
            if text_lines and text_lines[-1] != "":
                text_lines.append("")
            continue
        # Remove HTML tags and VTT cue settings
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\{[^}]+\}", "", line)
        if line:
            text_lines.append(line)

    # Remove duplicate consecutive lines (common in auto-generated VTT)
    deduped = []
    for line in text_lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)

    # Collapse multiple blank lines
    result = []
    prev_blank = False
    for line in deduped:
        if line == "":
            if not prev_blank:
                result.append("")
            prev_blank = True
        else:
            result.append(line)
            prev_blank = False

    return "\n".join(result).strip()


COOKIES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies")
COOKIES_CANDIDATES = {
    "bilibili": ["www.bilibili.com_cookies.txt", "bilibili.com_cookies.txt"],
    "youtube":  ["www.youtube.com_cookies.txt", "youtube.com_cookies.txt"],
}

def find_default_cookies(platform: str) -> str | None:
    """Return the first matching cookies file for the platform, or any .txt file in the dir."""
    if not os.path.isdir(COOKIES_DIR):
        return None
        
    # 1. Try specific candidates first
    for name in COOKIES_CANDIDATES.get(platform, []):
        path = os.path.join(COOKIES_DIR, name)
        if os.path.isfile(path):
            return path
            
    # 2. Search for any .txt file that contains the platform name
    all_files = os.listdir(COOKIES_DIR)
    for f in all_files:
        if f.endswith(".txt") and platform.lower() in f.lower():
            return os.path.join(COOKIES_DIR, f)
            
    # 3. If only one .txt file exists in the directory, use it as a fallback
    txt_files = [f for f in all_files if f.endswith(".txt")]
    if len(txt_files) == 1:
        return os.path.join(COOKIES_DIR, txt_files[0])
        
    return None


def build_yt_dlp_command(url: str, platform: str, tmp_dir: str, lang: str, cookies: str = None) -> list:
    """Build the yt-dlp command for subtitle extraction."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-sub",
        "--write-auto-sub",
        "--sub-format", "vtt/srt/best",
        "-o", os.path.join(tmp_dir, "%(title)s"),
    ]
    if cookies:
        cmd += ["--cookies", cookies]

    if platform == "bilibili":
        # Bilibili typically has zh-Hans or ai-zh subtitles
        if lang:
            cmd += ["--sub-lang", lang]
        else:
            cmd += ["--sub-lang", "zh-Hans,ai-zh,zh,zh-CN,ai-en"]
    else:
        # YouTube: requires JS runtime to solve n-challenge, otherwise only image
        # formats are returned and subtitle download fails
        cmd += ["--js-runtimes", "node", "--remote-components", "ejs:github"]
        if lang:
            cmd += ["--sub-lang", lang]
        else:
            cmd += ["--sub-lang", "zh-Hans,zh,zh-CN,en"]

    cmd.append(url)
    return cmd


def find_subtitle_files(tmp_dir: str) -> list:
    """Find all subtitle files downloaded in tmp_dir."""
    patterns = ["*.vtt", "*.srt", "*.ass", "*.ssa"]
    found = []
    for pat in patterns:
        found.extend(glob.glob(os.path.join(tmp_dir, pat)))
    return found


def extract_subtitles(url: str, output_dir: str, lang: str = None, cookies: str = None):
    platform = detect_platform(url)
    if platform == "unknown":
        print(f"[Warning] Unrecognized platform for URL: {url}")
        print("Attempting extraction anyway...")

    if not cookies:
        cookies = find_default_cookies(platform)
        if cookies:
            print(f"[Info] Using cookies: {cookies}")

    print(f"[Info] Platform: {platform.upper()}")
    print(f"[Info] Downloading subtitles...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        cmd = build_yt_dlp_command(url, platform, tmp_dir, lang, cookies)

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

        if result.returncode != 0:
            print("[Error] yt-dlp failed:")
            print(result.stderr)
            sys.exit(1)

        subtitle_files = find_subtitle_files(tmp_dir)

        if not subtitle_files:
            print("[Error] No subtitle files found.")
            print("The video may not have subtitles, or the language is unavailable.")
            print("\nyt-dlp output:")
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            print("\nTo list available subtitles, run:")
            print(f'  yt-dlp --list-subs "{url}"')
            sys.exit(1)

        os.makedirs(output_dir, exist_ok=True)
        saved_files = []

        for sub_file in subtitle_files:
            with open(sub_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            ext = os.path.splitext(sub_file)[1].lower()
            if ext == ".vtt":
                text = vtt_to_text(content)
            elif ext == ".srt":
                text = srt_to_text(content)
            else:
                # For .ass/.ssa, just strip obvious tags
                text = re.sub(r"\{[^}]+\}", "", content)
                text = re.sub(r"^(Script Info|V4\+ Styles|Events|Dialogue|Comment).*$",
                              "", text, flags=re.MULTILINE)
                text = "\n".join(l for l in text.splitlines() if l.strip())

            # Build output filename from subtitle filename
            base_name = os.path.splitext(os.path.basename(sub_file))[0]
            # Remove yt-dlp language suffix like .zh-Hans from the base name
            base_name = re.sub(r"\.[a-z]{2}(-[A-Za-z]+)*$", "", base_name)
            # Sanitize filename
            safe_name = re.sub(r'[\\/*?:"<>|]', "_", base_name)
            out_path = os.path.join(output_dir, safe_name + ".txt")

            # Avoid overwriting if multiple languages
            counter = 1
            original_out = out_path
            while os.path.exists(out_path):
                out_path = original_out.replace(".txt", f"_{counter}.txt")
                counter += 1

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)

            saved_files.append(out_path)
            print(f"[OK] Saved: {out_path}")

        return saved_files


def main():
    parser = argparse.ArgumentParser(description="Extract subtitles from Bilibili/YouTube to .txt")
    parser.add_argument("url", help="Video URL (Bilibili or YouTube)")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory (default: current dir)")
    parser.add_argument("--lang", "-l", help="Subtitle language code (e.g. zh-Hans, en, zh)")
    parser.add_argument("--cookies", "-c", help="Path to cookies.txt file for login-required videos")
    args = parser.parse_args()

    saved = extract_subtitles(args.url, args.output_dir, args.lang, args.cookies)
    print(f"\n[Done] {len(saved)} subtitle file(s) saved.")


if __name__ == "__main__":
    main()
