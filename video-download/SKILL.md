---
name: video-download
description: Download a video with proofread bilingual subtitles, archived as a single .mkv. Use when the user wants the video file itself, wants watchable bilingual subtitles, or asks to fix machine-translated captions — usually alongside a YouTube/Bilibili URL ("下载视频", "双语字幕", "校对字幕"). For a plain-text transcript and no video, use video-subtitle-extractor instead.
---

# Video Download

Download a video, rebuild its captions, and archive it as a single `.mkv` carrying both subtitle tracks — with the `.srt` files kept alongside so they stay editable and greppable.

**Requires:** `yt-dlp` (`pip install yt-dlp`), `node`, `ffmpeg`.

## Why this isn't just yt-dlp

Two things make raw auto-captions unusable, and both are invisible until you look at the file:

**They are rolling captions.** Every cue repeats the previous cue's text and adds one line, padded with 10ms filler cues. A 18-minute talk becomes ~980 cues holding ~490 real lines. Played as-is, the subtitle flickers and stutters with duplicate text. Step 3 **de-rolls** them.

**The machine translation is faithful.** It faithfully translates whatever the speech recogniser heard — so `LLMs` misheard as `Hums` arrives in Chinese as 「哼唱」, `agentic` as 「基因」, `docs` as 「码头」. The Chinese looks like a translation error but the damage was done upstream. Garbage in, garbage out — which is why proofreading runs the English pass first.

## Workflow

`SCRIPT` = this skill's `scripts\subs.py` (globally installed: `~\.claude\skills\video-download\scripts\subs.py`)
`WORK` = a fresh scratch dir for this video.

### 1. Fetch

```
python <SCRIPT> fetch "<URL>" --work <WORK> [--height 1080] [--skip-video]
```

Prints the title, duration and which caption languages landed.
**Done when** at least one `media.*.srt` exists. If yt-dlp reports sign-in or bot checks, go to [Cookies](#cookies) — that is a hard block, not a retry.

### 2. Stop and ask

Report the title, duration, channel and caption languages, then ask whether to go on to proofreading and the `.mkv`. Proofreading is the expensive part of this skill — it reads several hundred lines and rewrites every one — so the user decides whether it is worth spending, on this video, now.

**If they decline**, finish the job anyway, just without the proofreading pass:

```
python <SCRIPT> pairs --work <WORK>
python <SCRIPT> build --work <WORK> --out <DEST> --as-is
```

That still de-rolls the captions (so the subtitle no longer flickers) and still produces the `.mkv` — it just carries the machine translation untouched. Say so plainly when you report the path, then stop. Steps 3–5 are skipped entirely.

**If they accept**, continue.

**Done when** the user has answered — never assume the expensive path.

### 3. De-roll into an aligned table

```
python <SCRIPT> pairs --work <WORK>
```

Writes `pairs.txt` (`EN` / `ZH` per line, with timestamps) and `en.json` (the timeline).
**Done when** it prints the line count `N`. That number governs everything downstream.

### 4. Proofread — this is your work

Read `pairs.txt` in full. Write `<WORK>/zh_final.json`: a JSON array of **exactly N strings**, index-aligned to the table. If a line has no `ZH` (marked `<<MISSING>>`, or the video had no Chinese track at all), translate it from the English.

Run two passes over each line:

**Pass 1 — what did the recogniser mishear?** Proper nouns and technical terms take the worst damage, and they are exactly the words that carry the meaning. Real examples from one AI-engineering talk: `Hums`→LLMs, `a gentic`→agentic, `as GP`→ast-grep, `RIP Grep`→ripgrep, `open claw`→OpenClaw, `cloud code`→Claude Code, `Matt PCO`→Matt Pocock, `docks`→docs, `monor repo`→monorepo, `React slot`→React slop, `pack work`→Packwerk. When a word makes no sense in context, assume a mishear and reconstruct it from the domain — don't translate the nonsense.

**Pass 2 — is the Chinese right once the English is?** Watch for terms translated that should have stayed English, and for acronyms read as ordinary words (`PR` as 公关, `token` as 代币, `verifier` as 验证人员).

**Keep technical terms in English.** In a technical talk `loop`, `agent`, `skill`, `prompt`, `PR`, `token`, `slop`, `workflow`, library names — all read better untranslated. Translate only concepts with settled Chinese equivalents (控制论, 传感器, 控制器, 执行器, 设定点). Ask the user if a talk sits outside this convention.

Lines are sentence fragments cut on the caption timeline, so a Chinese sentence will span several of them — that is expected. Keep each line's content within its own slot rather than merging: **the count must stay N**, and `build` rejects the file otherwise.

Optionally write `<WORK>/en_fixes.json` to repair the English track too — a sparse map `{"12": "corrected text", ...}` keyed by line index. Fix only misheard words; leave the speaker's own disfluencies (`uh`, false starts, self-corrections) exactly as transcribed. It stays a transcript, not a rewrite.

Flag any reconstruction you are guessing at when you report back — a wrong proper noun is invisible to the user but a wrong `read-only`/`write-only` inverts a sentence.

**Done when** `zh_final.json` holds N non-empty strings and every one was checked against its English line.

### 5. Build and archive

```
python <SCRIPT> build --work <WORK> --out <DEST> [--title "..."] [--en-only] [--no-mux]
```

Creates `<DEST>/<title>/` holding `<title>.mkv`, `<title>.zh-Hans.srt`, `<title>.en.srt`. Cue timing comes from the de-rolled timeline: each line runs until the next begins, capped at 8s.

The `.mkv` carries both subtitles as selectable tracks, Chinese on by default, remuxed with `-c copy` — no re-encoding, no quality loss, a second or two. The `.srt` files stay on disk so subtitles remain editable and greppable; `--no-mux` skips the remux and leaves the original container.

**Done when** the three files are listed. Report the folder path and any guessed reconstructions.

## Cookies

YouTube demands a login. `--cookies-from-browser chrome` **cannot work on Windows** — Chrome 127+ encrypts its cookie store with App-Bound Encryption, so it fails whether or not Chrome is running. Edge fails on DPAPI. Firefox is unaffected if it is installed and logged in.

Otherwise export a cookies file with [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc), named `www.youtube.com_cookies.txt` / `www.bilibili.com_cookies.txt`. `fetch` finds it in either skill's `cookies\` folder, so one copy serves both:

```
<skills-dir>\video-download\cookies\
<skills-dir>\video-subtitle-extractor\cookies\   ← shared with the sibling skill
```

where `<skills-dir>` is `~\.claude\skills` for a global install.

Cookies expire. When a fetch that used to work starts demanding sign-in, re-export over the same file.

## Notes

- `fetch` caps at 1080p by default; raise with `--height 2160` when the source has it.
- YouTube 1080p is usually AV1 — fine in VLC/mpv/PotPlayer, but re-encode for older devices or editors.
- Static (human-authored) captions are detected and passed through without de-rolling.
- Re-running `build` after editing `zh_final.json` is cheap; the video is only moved once.
