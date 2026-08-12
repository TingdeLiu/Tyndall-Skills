#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download a video with its captions, then rebuild clean sidecar subtitles.

Subcommands:
    fetch <URL>   download video + captions into a work dir
    pairs         de-roll the captions into an aligned EN/ZH line table
    build         rebuild .srt files from the agent's proofread lines, archive

The agent's only job sits between `pairs` and `build`: read pairs.txt, write
zh_final.json (and optionally en_fixes.json). Everything else is mechanical.
"""

import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys

def force_utf8():
    """Keep Unicode printable on the Windows console. Called from main() only —
    rebinding std streams at import time would break any caller importing this."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream and hasattr(stream, "buffer"):
            setattr(sys, name,
                    io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_ROOT = os.path.dirname(SKILL_DIR)
# One cookies file serves every video skill; look in the sibling skill too so
# the user maintains a single copy.
COOKIES_DIRS = [
    os.path.join(SKILL_DIR, "cookies"),
    os.path.join(SKILLS_ROOT, "video-subtitle-extractor", "cookies"),
]
MAX_DUR_MS = 8000          # never leave one line on screen longer than this
MIN_DUR_MS = 1200          # fallback duration for the final cue

TS = re.compile(r"^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})")
NOISE = {"[music]", "[Music]", "[音乐]"}   # intro/outro music only; keep [applause] etc.


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #

def die(msg):
    print(f"[Error] {msg}")
    sys.exit(1)


def to_ms(ts):
    hh, mm, rest = ts.split(":")
    ss, ms = rest.split(",")
    return ((int(hh) * 60 + int(mm)) * 60 + int(ss)) * 1000 + int(ms)


def to_ts(ms):
    ms = max(0, int(ms))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def platform_of(url):
    if "bilibili.com" in url or "b23.tv" in url:
        return "bilibili"
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    return "unknown"


def default_cookies(platform):
    names = {
        "bilibili": ["www.bilibili.com_cookies.txt", "bilibili.com_cookies.txt"],
        "youtube": ["www.youtube.com_cookies.txt", "youtube.com_cookies.txt"],
    }
    for directory in COOKIES_DIRS:
        for name in names.get(platform, []):
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                return path
    return None


def safe_name(name):
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name.strip().rstrip(".")


# --------------------------------------------------------------------------- #
# srt parsing — by cue header, never by blank line
# --------------------------------------------------------------------------- #

def _is_header(lines, i):
    return (
        re.fullmatch(r"\d+", lines[i].strip())
        and i + 1 < len(lines)
        and TS.match(lines[i + 1].strip())
    )


def parse_srt(path):
    """Parse .srt into [(start, end, [text lines])].

    Auto-caption files put a blank line between the timestamp and the text, so
    splitting the file on blank lines silently drops the text of every such cue
    and shifts the whole timeline late. Cue headers are the only safe boundary.
    """
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        lines = f.read().splitlines()
    cues = []
    i, n = 0, len(lines)
    while i < n:
        if not _is_header(lines, i):
            i += 1
            continue
        m = TS.match(lines[i + 1].strip())
        j = i + 2
        text = []
        while j < n and not _is_header(lines, j):
            stripped = lines[j].strip()
            if stripped:
                text.append(re.sub(r"<[^>]+>", "", stripped))
            j += 1
        cues.append((m.group(1), m.group(2), text))
        i = j
    return cues


def is_rolling(cues):
    """Rolling captions repeat the previous cue's tail in the next cue."""
    repeats = total = 0
    for prev, cur in zip(cues, cues[1:]):
        if not prev[2] or not cur[2]:
            continue
        total += 1
        if prev[2][-1] in cur[2]:
            repeats += 1
    return total > 0 and repeats / total > 0.5


def deroll(cues):
    """Flatten captions into one entry per distinct line, timed at first sight."""
    rolling = is_rolling(cues)
    out = []
    for start, end, text in cues:
        if not text:
            continue
        # Rolling cues carry history; the last line is the new content. Static
        # cues are self-contained, so keep the whole cue as one line.
        line = text[-1] if rolling else " ".join(text)
        if line in NOISE:
            continue
        if out and out[-1]["text"] == line:
            out[-1]["end"] = end
            continue
        if rolling and out and len(text) > 1 and out[-1]["text"] == text[-1]:
            continue
        out.append({"start": start, "end": end, "text": line})
    return out, rolling


# --------------------------------------------------------------------------- #
# fetch
# --------------------------------------------------------------------------- #

def run_ytdlp(args, url, cookies, platform):
    cmd = [sys.executable, "-m", "yt_dlp"]
    if platform == "youtube":
        # Without a JS runtime YouTube returns image-only formats and captions fail.
        cmd += ["--js-runtimes", "node", "--remote-components", "ejs:github"]
    if cookies:
        cmd += ["--cookies", cookies]
    cmd += args + [url]
    return subprocess.run(cmd, text=True, encoding="utf-8", errors="replace")


def cmd_fetch(a):
    platform = platform_of(a.url)
    cookies = a.cookies or default_cookies(platform)
    os.makedirs(a.work, exist_ok=True)

    if cookies:
        print(f"[Info] cookies: {cookies}")
    elif platform == "youtube":
        print("[Warn] no cookies file — YouTube will likely demand sign-in")

    langs = a.sub_langs or (
        "zh-Hans,zh,zh-CN,en-orig,en" if platform == "bilibili"
        else "en-orig,en,zh-Hans,zh"
    )
    args = [
        "--write-subs", "--write-auto-subs",
        "--sub-langs", langs,
        "--convert-subs", "srt",
        "--no-progress",
        "-o", os.path.join(a.work, "media.%(ext)s"),
        "--write-info-json",
    ]
    if a.skip_video:
        args.append("--skip-download")
    else:
        args += [
            "-f", f"bv*[height<={a.height}]+ba/b[height<={a.height}]",
            "--merge-output-format", "mp4",
        ]

    if run_ytdlp(args, a.url, cookies, platform).returncode != 0:
        die("yt-dlp failed. Check cookies, or run "
            f'`python -m yt_dlp --list-subs "{a.url}"` to see what exists.')

    subs = sorted(glob.glob(os.path.join(a.work, "media.*.srt")))
    if not subs:
        die("no subtitles downloaded — the video may have none in these languages")
    print(f"[OK] captions: {[os.path.basename(s) for s in subs]}")

    info = os.path.join(a.work, "media.info.json")
    if os.path.isfile(info):
        with open(info, encoding="utf-8") as f:
            meta = json.load(f)
        print(f"[OK] title: {meta.get('title')}")
        print(f"[OK] {meta.get('duration_string')} | {meta.get('channel')}")


# --------------------------------------------------------------------------- #
# pairs
# --------------------------------------------------------------------------- #

def pick(work, prefixes):
    for p in prefixes:
        hit = sorted(glob.glob(os.path.join(work, f"media.{p}.srt")))
        if hit:
            return hit[0]
    return None


def cmd_pairs(a):
    en_src = pick(a.work, ["en-orig", "en", "en-US", "en-GB"])
    zh_src = pick(a.work, ["zh-Hans", "zh", "zh-CN", "ai-zh"])
    if not en_src and not zh_src:
        die(f"no usable .srt in {a.work} — run `fetch` first")

    base_src = en_src or zh_src
    base, rolling = deroll(parse_srt(base_src))
    print(f"[Info] base: {os.path.basename(base_src)} "
          f"({'rolling' if rolling else 'static'} captions) -> {len(base)} lines")

    other = {}
    if en_src and zh_src:
        zh_lines, _ = deroll(parse_srt(zh_src))
        other = {c["start"]: c["text"] for c in zh_lines}
        print(f"[Info] machine translation: {os.path.basename(zh_src)} "
              f"-> {len(zh_lines)} lines")

    with open(os.path.join(a.work, "en.json"), "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=1)

    if other:
        # De-rolled machine translation, English as fallback for untranslated
        # lines. `build --as-is` uses this when the user skips proofreading.
        zh_mt = [other.get(c["start"]) or c["text"] for c in base]
        with open(os.path.join(a.work, "zh_mt.json"), "w", encoding="utf-8") as f:
            json.dump(zh_mt, f, ensure_ascii=False, indent=1)

    missing = 0
    with open(os.path.join(a.work, "pairs.txt"), "w", encoding="utf-8") as f:
        for i, c in enumerate(base):
            zh = other.get(c["start"])
            if other and zh is None:
                missing += 1
            f.write(f'{i:>4} [{c["start"][3:]}]\n')
            f.write(f'  EN {c["text"]}\n')
            if other:
                f.write(f'  ZH {zh if zh is not None else "<<MISSING — translate from EN>>"}\n')

    print(f"[OK] {len(base)} lines -> {os.path.join(a.work, 'pairs.txt')}")
    if missing:
        print(f"[Info] {missing} lines have no machine translation; translate them from EN")
    print(f"[Next] write zh_final.json — a JSON array of exactly {len(base)} strings")


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #

def write_srt(base, lines, path):
    starts = [to_ms(c["start"]) for c in base]
    with open(path, "w", encoding="utf-8") as f:
        for i, text in enumerate(lines):
            start = starts[i]
            if i + 1 < len(starts):
                end = min(starts[i + 1] - 1, start + MAX_DUR_MS)
            else:
                end = to_ms(base[i]["end"])
            if end <= start:
                end = start + MIN_DUR_MS
            f.write(f"{i + 1}\n{to_ts(start)} --> {to_ts(end)}\n{text}\n\n")


def load_lines(work, name, base, required):
    path = os.path.join(work, name)
    if not os.path.isfile(path):
        if required:
            die(f"{name} not found in {work} — write it before running `build`")
        return None
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)

    if isinstance(data, dict):  # sparse {index: replacement}
        out = [c["text"] for c in base]
        for k, v in data.items():
            i = int(k)
            if not 0 <= i < len(out):
                die(f"{name}: index {i} out of range 0..{len(out) - 1}")
            out[i] = v
        return out

    if len(data) != len(base):
        die(f"{name} has {len(data)} lines, expected {len(base)}. "
            "Every line must be accounted for — no merging, no dropping.")
    blank = [i for i, t in enumerate(data) if not str(t).strip()]
    if blank:
        die(f"{name} has empty lines at {blank[:20]}")
    return [str(t) for t in data]


def mux(video, subs, out):
    """Remux video + sidecar .srt into one .mkv. Streams are copied, never re-encoded.

    mkv, not mp4: mp4 only carries mov_text subtitles, which many players
    handle poorly for multi-language tracks. mkv takes SRT natively.
    """
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", video]
    for path, _, _ in subs:
        cmd += ["-i", path]
    cmd += ["-map", "0:v", "-map", "0:a?"]
    for i in range(len(subs)):
        cmd += ["-map", str(i + 1)]
    cmd += ["-c", "copy", "-c:s", "srt"]
    for i, (_, lang, title) in enumerate(subs):
        cmd += [
            f"-metadata:s:s:{i}", f"language={lang}",
            f"-metadata:s:s:{i}", f"title={title}",
            f"-disposition:s:{i}", "default" if i == 0 else "0",
        ]
    cmd.append(out)
    return subprocess.run(cmd, text=True, encoding="utf-8", errors="replace")


def cmd_build(a):
    with open(os.path.join(a.work, "en.json"), encoding="utf-8") as f:
        base = json.load(f)

    title = a.title
    info = os.path.join(a.work, "media.info.json")
    if not title and os.path.isfile(info):
        with open(info, encoding="utf-8") as f:
            title = json.load(f).get("title")
    title = safe_name(title or "video")

    dest = os.path.join(a.out, title)
    os.makedirs(dest, exist_ok=True)

    if a.as_is:
        zh = load_lines(a.work, "zh_mt.json", base, required=False)
        print("[Info] machine translation, structure repaired but NOT proofread")
    else:
        zh = load_lines(a.work, "zh_final.json", base, required=not a.en_only)
    en = load_lines(a.work, "en_fixes.json", base, required=False)
    if en is None:
        en = [c["text"] for c in base]

    made = []
    tracks = []               # (path, ISO-639-2 code, player-facing label)
    if zh:
        p = os.path.join(dest, f"{title}.zh-Hans.srt")
        write_srt(base, zh, p)
        made.append(p)
        tracks.append((p, "zho", "简体中文"))
    p = os.path.join(dest, f"{title}.en.srt")
    write_srt(base, en, p)
    made.append(p)
    tracks.append((p, "eng", "English"))

    video = None
    for src in glob.glob(os.path.join(a.work, "media.mp4")) + \
               glob.glob(os.path.join(a.work, "media.mkv")) + \
               glob.glob(os.path.join(a.work, "media.webm")):
        video = os.path.join(dest, f"{title}{os.path.splitext(src)[1]}")
        shutil.move(src, video)
        break

    if video and not a.no_mux:
        if not shutil.which("ffmpeg"):
            print("[Warn] ffmpeg not found — leaving the video and .srt side by side")
        else:
            out = os.path.join(dest, f"{title}.mkv")
            tmp = out + ".tmp.mkv" if video == out else out
            if mux(video, tracks, tmp).returncode != 0:
                print("[Warn] mux failed — keeping the video and .srt side by side")
            else:
                if tmp != out:
                    os.replace(tmp, out)
                elif video != out:
                    os.remove(video)
                video = out

    if video:
        made.append(video)
    for p in made:
        print(f"[OK] {p}")
    print(f"\n[Done] {dest}")


# --------------------------------------------------------------------------- #

def main():
    force_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="download video + captions")
    f.add_argument("url")
    f.add_argument("--work", "-w", required=True, help="scratch dir for this video")
    f.add_argument("--height", default="1080", help="max video height (default 1080)")
    f.add_argument("--sub-langs", help="override caption languages")
    f.add_argument("--cookies", "-c", help="cookies.txt path")
    f.add_argument("--skip-video", action="store_true", help="captions only")
    f.set_defaults(func=cmd_fetch)

    p = sub.add_parser("pairs", help="de-roll captions into an aligned table")
    p.add_argument("--work", "-w", required=True)
    p.set_defaults(func=cmd_pairs)

    b = sub.add_parser("build", help="rebuild .srt from proofread lines and archive")
    b.add_argument("--work", "-w", required=True)
    b.add_argument("--out", "-o", required=True, help="parent dir for the video folder")
    b.add_argument("--title", help="override folder/file name")
    b.add_argument("--en-only", action="store_true", help="skip the Chinese track")
    b.add_argument("--no-mux", action="store_true",
                   help="leave the video and .srt side by side instead of one .mkv")
    b.add_argument("--as-is", action="store_true",
                   help="archive without proofreading, using the machine translation")
    b.set_defaults(func=cmd_build)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
