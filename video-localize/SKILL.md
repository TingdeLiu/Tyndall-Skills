---
name: video-localize
description: Create a Chinese-localized video from a YouTube/Bilibili link with proofread Chinese subtitles and optional Chinese dubbing using IndexTTS-2.5. Use for Chinese voice-over, dubbed videos, or video localization workflows. For downloading a video with subtitles but no dubbing, use video-download; for a plain-text transcript, use video-subtitle-extractor.
---

# Video Localize

Choose this skill when the desired output is a Chinese-localized video, especially one with Chinese audio. Keep `video-download` for downloading and subtitle-only requests; the skills serve distinct needs and remain independently usable.

Download a video, rebuild its captions, and archive it as a single `.mkv` carrying both subtitle tracks — with the `.srt` files kept alongside so they stay editable and greppable. Optionally speak the Chinese track as a dub, carried in the same `.mkv` as a second audio track.

**Requires:** `yt-dlp` (`pip install yt-dlp`), `node`, `ffmpeg`. Dubbing additionally needs a local IndexTTS-2.5 — see [Dubbing](#dubbing).

## Why this isn't just yt-dlp

Two things make raw auto-captions unusable, and both are invisible until you look at the file:

**They are rolling captions.** Every cue repeats the previous cue's text and adds one line, padded with 10ms filler cues. A 18-minute talk becomes ~980 cues holding ~490 real lines. Played as-is, the subtitle flickers and stutters with duplicate text. Step 3 **de-rolls** them.

**The machine translation is faithful.** It faithfully translates whatever the speech recogniser heard — so `LLMs` misheard as `Hums` arrives in Chinese as 「哼唱」, `agentic` as 「基因」, `docs` as 「码头」. The Chinese looks like a translation error but the damage was done upstream. Garbage in, garbage out — which is why proofreading runs the English pass first.

## Workflow

`SCRIPT` = `<skill-dir>/scripts/subs.py`
`DUB` = `<skill-dir>/scripts/dub.py`
`<skill-dir>` = the directory containing this SKILL.md; resolve scripts relative to it, regardless of installation location.
`WORK` = a fresh scratch dir for this video.

### 1. Fetch

```
python <SCRIPT> fetch "<URL>" --work <WORK> [--height 1080] [--skip-video]
```

Prints the title, duration and which caption languages landed.
**Done when** at least one `media.*.srt` exists. If yt-dlp reports sign-in or bot checks, go to [Cookies](#cookies) — that is a hard block, not a retry.

### 2. Confirm the requested scope

Report the title, duration, channel and caption languages. If the user already requested proofread Chinese subtitles and/or Chinese dubbing, proceed within that scope. Otherwise ask which of those outputs they want before the expensive steps. These are the two expensive parts of the skill: proofreading reads several hundred lines and rewrites every one, dubbing costs roughly the video's own runtime on the GPU. The user decides whether either is worth spending, on this video, now.

Dubbing depends on proofreading, so it is not offered on its own: the voice reads whatever the text says, and machine-translation errors that a reader forgives — 「哼唱」 for `LLMs` — are far more jarring spoken aloud.

**If they decline**, finish the job anyway, just without the proofreading pass:

```
python <SCRIPT> pairs --work <WORK>
python <SCRIPT> build --work <WORK> --out <DEST> --as-is
```

That still de-rolls the captions (so the subtitle no longer flickers) and still produces the `.mkv` — it just carries the machine translation untouched. Say so plainly when you report the path, then stop. Steps 3–5 are skipped entirely.

**If they accept**, continue.

**Done when** the requested scope is clear from the current request or a follow-up answer.

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

### 5. Dub the Chinese track — when requested

```
python <DUB> all --work <WORK>
```

Speaks `zh_final.json` with IndexTTS-2.5 — cloning the speaker's own voice out of the source audio — and lays the result on the original timeline as `<WORK>/dub.wav`.

Run this when Chinese dubbing has been requested; do not ask for the same authorization again. If not requested, ask before adding it. Synthesis runs at roughly real time on a 16GB GPU, so an 18-minute talk costs about 18 minutes, and the first run needs the one-time setup in [Dubbing](#dubbing).

The number to read is the **line offset** `assemble` prints last — how far each caption line lands from its cue. That is what a viewer sees. Under about 1s at the median with the 90th percentile inside 3s plays cleanly; past that, roughly one line in ten is visibly out of step. Ignore the clip-drift line above it: it measures where clips *start*, which on a long clip says nothing about where its later lines land, and it will flatter a bad result.

If the offset is poor, reach for clip size before rewriting Chinese — `--max-chars` a step either side of the default, re-running `segment` each time. Only when that bottoms out is the translation genuinely too long.

**Done when** `dub.wav` exists. Report the line-offset figures, not the clip drift.

### 6. Build and archive

```
python <SCRIPT> build --work <WORK> --out <DEST> [--title "..."] [--en-only] [--no-mux] [--no-dub]
```

Creates `<DEST>/<title>/` holding `<title>.mkv`, `<title>.zh-Hans.srt`, `<title>.en.srt`. Cue timing comes from the de-rolled timeline: each line runs until the next begins, capped at 8s.

The `.mkv` carries both subtitles as selectable tracks, Chinese on by default, remuxed with `-c copy` — no re-encoding, no quality loss, a second or two. The `.srt` files stay on disk so subtitles remain editable and greppable; `--no-mux` skips the remux and leaves the original container.

`build` picks up `<WORK>/dub.wav` on its own when step 5 produced one. The dub becomes the default audio track and the original English is kept as a second, selectable one — nothing is discarded, and viewers who want the original still have it. Only the dub is re-encoded (it arrives as PCM); video and original audio are still copied. `--no-dub` archives subtitles only.

**Done when** the files are listed. Report the folder path and any guessed reconstructions.

## Dubbing

### One-time setup

IndexTTS-2.5 is a separate checkout with its own virtualenv and ~8GB of weights; it is not installed with this skill. Choose a local checkout directory, represented below as `<INDEX_TTS_DIR>`. The setup is per machine:

```
git clone --depth 1 https://github.com/index-tts/index-tts.git <INDEX_TTS_DIR>
cd <INDEX_TTS_DIR>
uv sync
.venv\Scripts\modelscope.exe download --model IndexTeam/IndexTTS-2.5 --local_dir checkpoints
python <DUB> setup --indextts-dir <INDEX_TTS_DIR>
```

`uv sync` pulls torch 2.8 + cu128, which is what RTX 50-series (Blackwell, `sm_120`) needs — an older CUDA build imports fine and even reports `cuda.is_available() == True`, then dies on the first kernel with `no kernel image is available`. ModelScope is the faster mirror inside mainland China; `hf download IndexTeam/IndexTTS-2.5` is the equivalent elsewhere.

Budget ~15GB and an hour of downloading for the whole setup: the venv is ~4GB, `checkpoints` is 5.2GB, and the **first `synth` fetches another ~4.3GB on its own** — a w2v-bert feature extractor and a speaker encoder the checkpoint doesn't bundle. The standard Hugging Face endpoint is used by default. If needed for your network, explicitly set `HF_ENDPOINT` to a trusted mirror before synthesis. It is a one-time cost; later videos start straight into synthesis.

`setup` records the path in `tts.json`. `dub.py` re-execs itself into that venv whenever it needs the model, so every command in this file still runs under the ordinary `python`.

### Why the dub is not one clip per caption line

Caption lines are breath-sized fragments — `and that's why we` / `need to think about`. Fed to a TTS one at a time, every half-sentence gets its own falling final contour, and the result is unmistakably machine-read. `segment` regroups them into whole sentences first; everything downstream works on sentences.

### Where the sentence boundaries come from

Not from the caption timing. De-rolling stretches each line's `end` forward to the next line's `start`, so silences are absorbed into the preceding line and **every gap measures 0ms** — a speaker's two-second pause leaves no trace in `en.json`. Segmenting on caption timing alone therefore degrades into cutting every N characters.

The audio still has the pauses. `segment` runs ffmpeg's `silencedetect` over the media file and cuts there instead: a silence over 320ms ends a sentence, a shorter one becomes a comma. The commas are what stop the voice reading three clauses in a single breath. With no media file (`--skip-video`) there is nothing to listen to, and it falls back to a character count after warning.

### Why clip count matters more than word count

Every clip carries a fixed cost — onset, decay, the final falling contour — of about **1.5 seconds regardless of length**. A three-character line still takes 1.3s to say. `duration_factor` does not touch it: dropping 0.92 → 0.84 cut per-character time by 12% and the fixed cost by **0%**.

That makes clip count, not word count, the number to watch. On the 24-minute interview this was built against, closing a clip at every full stop gave 283 clips — **7 minutes of pure overhead**, a third of all speech, none of it recoverable by speeding up, and the track finished 12.8s behind the picture. Removing that rule and letting the size caps decide fixed it without shortening the translation at all; three passes spent trimming the Chinese had been treating the symptom.

So `segment` deliberately does **not** break at a full stop. A TTS reads consecutive sentences perfectly well, and gives them a more connected line than rendering each alone. Only a real pause in the audio, or a size cap, closes a clip.

But bigger is not simply better — clip size trades one error against another, and the curve is U-shaped:

| clips (24 min video) | line offset, median | 90th pct | max |
|---|---|---|---|
| 210 | 0.9s | 4.2s | 8.5s |
| **159** | **0.7s** | **2.7s** | **5.3s** |
| 105 | 1.0s | 3.4s | 7.0s |
| 76 | 1.7s | 6.1s | 11.8s |

Too many clips and the fixed cost drags the whole track late. Too few and each clip spans so many caption lines that its internal pacing — which the TTS decides, not the timeline — drifts away from the picture. The caps above sit near the bottom of that curve, around one clip per 9 seconds of video.

**Measure the line offset, not the clip drift.** `assemble` reports how late each clip *starts*, but a viewer sees where each *line* lands, and inside a long clip those are very different numbers: at 105 clips the worst clip start was 1.1s late while the worst line was 7.0s off. Judge the result on the line figure.

### Fitting a sentence into its slot

Each clip gets the window up to the next one. Whether Chinese is shorter than the English it replaces depends on the source: an unhurried talk leaves room to spare, while a dense interview can want more time than the picture has.

Fitting the whole track is `synth --pace`, which takes `auto` (fit the total to the timeline) or a fixed factor. One small global adjustment is far less audible than letting a handful of sentences race — 0.95 passes unnoticed, and below about 0.85 the voice starts to sound hurried. Clips that still overrun are re-synthesised tighter, never below 0.82, and anything that still doesn't fit is reported rather than quietly degraded. Such a clip pushes the next one later instead of talking over it, and the drift does not accumulate — the next clip with room in front of it snaps back to its own timestamp.

Translate for the mouth, not the eye. Subtitles tolerate extra words because reading outruns speech; a dub pays for every character. Connectives that make a subtitle read well (「这么说吧」「你知道」) are the first thing to cut. But check the clip count first — see above; on a dense source that is usually the real problem, and it costs no words at all.

### Voice

`voice` cuts the densest stretch of speech out of the source — skipping the first 5% so it can't grab intro music or applause — and uses it as the cloning prompt, so the dub keeps the original speaker's voice across the language change. Listen to `voice_ref.wav` before committing to a long run; if it caught applause or a second speaker, pass `--voice <your own clip.wav>` to `synth`.

`--lang zhen` (the default) is the mixed Chinese/English mode, and it matters here: proofreading deliberately leaves `agent`, `prompt`, `Claude Code` in English, and plain `zh` mangles them.

### Re-running

The subcommands are separate so a bad step is cheap to redo. `synth --resume` keeps the clips already made; `assemble` alone re-lays them after you delete the few you want regenerated; `build` after a re-dub takes seconds.

## Cookies

Some videos require authentication or trigger bot checks. Try the normal fetch first. If authentication is required, use a Netscape-format cookies file with `fetch --cookies <path>`. Treat it as a login credential: keep it local and never commit it.

Automatic lookup checks `<skill-dir>/cookies/` and the optional sibling `video-subtitle-extractor/cookies/` for `www.youtube.com_cookies.txt`, `youtube.com_cookies.txt`, `www.bilibili.com_cookies.txt`, or `bilibili.com_cookies.txt`. The sibling skill is not required; an explicit file path works independently.

Browser-cookie extraction depends on the browser, operating system, encryption and permissions. If it fails, use a locally exported cookies file rather than repeatedly retrying.

Cookies expire. When a fetch that used to work starts demanding sign-in, re-export over the same file.

## Notes

- `fetch` caps at 1080p by default; raise with `--height 2160` when the source has it.
- YouTube 1080p is usually AV1 — fine in VLC/mpv/PotPlayer, but re-encode for older devices or editors.
- Static (human-authored) captions are detected and passed through without de-rolling.
- Re-running `build` after editing `zh_final.json` is cheap; the video is only moved once.
- Editing `zh_final.json` after a dub invalidates it — the audio still speaks the old text. Re-run `dub.py all` (or at least `segment` + `synth`) before rebuilding.
- The dub lives at `<WORK>/dub.wav` until `build` remuxes it. To pull it back out of a finished `.mkv`: `ffmpeg -i <title>.mkv -map 0:a:0 dub.wav`.
- IndexTTS-2.5's licence is bilibili's own, not a standard open-source one. Read `checkpoints/LICENSE` before publishing dubs commercially.
