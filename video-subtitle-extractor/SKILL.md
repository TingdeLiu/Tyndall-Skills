---
name: video-subtitle-extractor
description: Extract and save subtitles from video URLs as plain .txt files. Supports Bilibili (B站) and YouTube. Use when the user provides a Bilibili or YouTube video link and asks to extract, download, or save subtitles/captions. Triggers on phrases like "提取字幕", "下载字幕", "extract subtitles", "get subtitles", or when a bilibili.com / youtube.com / youtu.be URL is provided with a subtitle-related request. For the video file itself, watchable bilingual subtitles, or proofreading machine-translated captions, use video-download instead.
---

# Video Subtitle Extractor

Extract subtitles from Bilibili or YouTube videos and save as plain `.txt` files.

**Requires:** `yt-dlp` installed (`pip install yt-dlp`)

## Not this skill

This one produces a **plain-text transcript** — one language, no timestamps, no video.
It does not de-roll rolling auto-captions and does not proofread anything.

Use **video-download** instead when the user wants the video file, wants subtitles
they can actually watch (`.srt` / `.mkv` with bilingual tracks), or wants the machine
translation corrected. Its `fetch` step covers everything this skill does, so the only
reason to stay here is that a `.txt` is all that's wanted.

## Workflow

1. Run the extraction script with the video URL
2. Show the user the saved file path and a preview of the content

## Script

Run from this skill's directory (paths below are relative to the skill root):

```bash
python scripts/extract_subtitles.py <URL> [--output-dir <dir>] [--lang <code>]
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
python scripts/extract_subtitles.py "https://www.bilibili.com/video/BV1xx411c7mD"

# YouTube, save to Downloads
python scripts/extract_subtitles.py "https://youtu.be/dQw4w9WgXcQ" --output-dir "downloads"

# Force English
python scripts/extract_subtitles.py "https://www.youtube.com/watch?v=abc" --lang en
```

## Authentication (cookies)

YouTube and some Bilibili videos require login. Export cookies from your browser using the
[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
extension, then pass the file:

```bash
python scripts/extract_subtitles.py "<URL>" --cookies "path/to/cookies.txt"
```

Or drop it in this skill's `cookies/` directory and the script picks it up without `--cookies`. Only these exact names are recognised — anything else in the folder is ignored:

- YouTube: `www.youtube.com_cookies.txt` or `youtube.com_cookies.txt`
- Bilibili: `www.bilibili.com_cookies.txt` or `bilibili.com_cookies.txt`

> **Note:** `--cookies-from-browser chrome` fails when Chrome is running (database locked).
> `--cookies-from-browser edge` fails on Windows due to DPAPI encryption. Use a cookies.txt file instead.

Cookies expire. When a fetch that used to work starts demanding sign-in, re-export over the same file.

## Troubleshooting

**No subtitles found** — List available languages first:
```bash
yt-dlp --list-subs "<URL>"
```
Then re-run with `--lang <code>` from the list.

**HTTP 429 (Too Many Requests)** — YouTube rate-limiting. Wait a moment and retry.

**Bilibili "subtitles only available when logged in"** — Export Bilibili cookies and pass with `--cookies`.
