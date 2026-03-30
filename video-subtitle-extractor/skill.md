---
name: video-subtitle-extractor
description: Extract and save subtitles from video URLs as plain .txt files. Supports Bilibili (B站) and YouTube. Use when the user provides a Bilibili or YouTube video link and asks to extract, download, or save subtitles/captions. Triggers on phrases like "提取字幕", "下载字幕", "extract subtitles", "get subtitles", or when a bilibili.com / youtube.com / youtu.be URL is provided with a subtitle-related request.
---

# Video Subtitle Extractor

Extract subtitles from Bilibili or YouTube videos and save as plain `.txt` files.

**Requires:** `yt-dlp` installed (`pip install yt-dlp`)

## Workflow

1. Run the extraction script with the video URL
2. Show the user the saved file path and a preview of the content

## Script

```
python C:\Users\tingd\.claude\skills\video-subtitle-extractor\scripts\extract_subtitles.py <URL> [--output-dir <dir>] [--lang <code>]
```

**Arguments:**
- `<URL>` — Bilibili or YouTube video URL (required)
- `--output-dir` / `-o` — Where to save the .txt file (default: current directory)
- `--lang` / `-l` — Subtitle language code (optional)
- `--cookies` / `-c` — Path to cookies.txt file (required for login-gated videos)

**Default language priority:**
- Bilibili: `zh-Hans` → `ai-zh` → `zh` → `zh-CN`
- YouTube: `zh-Hans` → `zh` → `zh-CN` → `en`

## Common examples

```bash
# Bilibili (auto-detect language)
python ...extract_subtitles.py "https://www.bilibili.com/video/BV1xx411c7mD"

# YouTube, save to Downloads
python ...extract_subtitles.py "https://youtu.be/dQw4w9WgXcQ" --output-dir "C:/Users/tingd/Downloads"

# Force English
python ...extract_subtitles.py "https://www.youtube.com/watch?v=abc" --lang en
```

## Authentication (cookies)

YouTube and some Bilibili videos require login. Export cookies from your browser using the
[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
extension, then pass the file:

```bash
python ...extract_subtitles.py "<URL>" --cookies "C:/path/to/cookies.txt"
```

Store the cookies file at a stable path (e.g. `C:\Users\tingd\.claude\skills\video-subtitle-extractor\cookies\www.youtube.com_cookies.txt`) and reuse it.

> **Note:** `--cookies-from-browser chrome` fails when Chrome is running (database locked).
> `--cookies-from-browser edge` fails on Windows due to DPAPI encryption. Use a cookies.txt file instead.

## Troubleshooting

**No subtitles found** — List available languages first:
```bash
yt-dlp --list-subs "<URL>"
```
Then re-run with `--lang <code>` from the list.

**HTTP 429 (Too Many Requests)** — YouTube rate-limiting. Wait a moment and retry.

**Bilibili "subtitles only available when logged in"** — Export Bilibili cookies and pass with `--cookies`.
