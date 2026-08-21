# Tyndall-Skills

A curated collection of custom Claude Code skills (SKILL.md templates) and automation scripts designed to extend AI capabilities and streamline complex development and productivity workflows.

English | [中文](README_CN.md)

## Skills at a Glance

| # | Skill | What it does | Needs |
|:--:|---|---|---|
| 1 | [**Claude Code Statusline**](#1-claude-code-statusline-claude-code-statusline)<br>`claude-code-statusline` | Custom status line — model, context bar, session cost, rate limits — plus a completion sound and a golden capybara buddy 🐣 | Python 3 **or** Node |
| 2 | [**PDF Compressor**](#2-pdf-compressor-pdf-compressor)<br>`pdf-compressor` | Shrinks oversized PDFs to fit API limits, with four quality presets and automatic backup | Ghostscript |
| 3 | [**PDF Figure Extractor**](#3-pdf-figure-extractor-pdf-figure-extractor)<br>`pdf-figure-extractor` | Detects and crops figures & tables out of papers using the TF-ID model, with a Markdown index | Conda env + Poppler |
| 4 | [**English → Chinese Paper PDF**](#4-english-to-chinese-paper-pdf-pdf-e2c)<br>`pdf-e2c` | Rebuilds an English paper as a single-column Chinese PDF, figures/tables/equations cropped from the original | `pymupdf` `reportlab` `pillow` |
| 5 | [**Video Subtitle Extractor**](#5-video-subtitle-extractor-video-subtitle-extractor)<br>`video-subtitle-extractor` | Pulls subtitles off YouTube / Bilibili as plain `.txt` — when you just want the transcript | `yt-dlp` |
| 6 | [**Video + Bilingual Subtitles**](#6-video-download-with-bilingual-subtitles-video-download)<br>`video-download` | Downloads the video, de-rolls and proofreads the captions, archives it as one `.mkv` with both tracks | `yt-dlp` `node` `ffmpeg` |
| 7 | [**Project Summary**](#7-project-summary-project-summary)<br>`project-summary` | Reads a repo (URL or local) and writes `architecture.md` with an auto-chosen ASCII architecture diagram | — |
| 8 | [**Claude-Style HTML**](#8-claude-style-html-claude-html)<br>`claude-html` | Anthropic's visual language as a working design system: two templates, four diagram classes, zero JavaScript | — |
| 9 | [**Plain-Language Explainer**](#9-plain-language-explainer-speak-human)<br>`speak-human` | Re-explains jargon as one conclusion + one analogy + an ASCII diagram + a term-mapping table | — |
| 10 | [**Excalidraw Diagrams**](#10-excalidraw-diagram-generator-obsidian-excalidraw)<br>`obsidian-excalidraw` | Turns text into Obsidian-ready Excalidraw diagrams, tuned for AI model architectures (VLA, Transformer, Diffusion Policy) | Python 3 + Obsidian |

→ [How to Add Skills to Claude Code](#how-to-add-skills-to-claude-code)

---

## Available Skills

### 1. Claude Code Statusline (`claude-code-statusline`)
A cross-platform Claude Code enhancement that adds a custom status line and a completion notification sound on Windows and macOS.

![Claude Code status line](images/claude-status.png)

- **Triggers:** "Set up a statusline", "Configure Claude Code statusLine", "Play a sound when Claude finishes", or failures of bash/jq-based statusline scripts.
- **Key Features:**
  - Shows model name, color-coded context-usage bar, session cost (USD), and 5h/7d rate-limit percentages.
  - Plays a notification sound (Ding / Chime / Beep) via `afplay` on macOS or PowerShell on Windows when Claude finishes a response.
  - Color thresholds configurable via `WARN_PCT` / `DANGER_PCT` environment variables.
  - Auto-detects Python or Node.js — no `jq` dependency, no Unicode encoding errors.
  - **Easter-egg buddy 🐣:** a golden capybara lives at the end of the status line — it poses (`\(^ww^)/` `~(-oo-)~`), chews, blinks and winks between refreshes, and rotates through **9 moods** driven by your context / cost / rate-limit state, each with its own symbols and quip pool (`♥♥♥ chef's kiss` · `zZz /compact soon?` · `!?! everything is soup`). It also **earns colour as you work** — gold by default, unlocking coloured symbols, a coloured face, and finally a flowing rainbow as today's API time passes 1 / 3 / 8 hours. Fully local, **0 tokens**.
- **Setup & Prerequisites:**
  - Python 3 or Node.js available in PATH.
  - Install the skill into `~/.claude/skills/claude-code-statusline/` (see [How to Add Skills to Claude Code](#how-to-add-skills-to-claude-code)), then ask Claude **"set up my Claude Code statusline"** — it'll detect your OS and runtime, ask for your sound preference, and wire up the script + `settings.json` automatically.

#### 🐣 Meet your buddy — the golden capybara

Tucked at the end of the status line lives a tiny golden capybara, ported from Claude Code's internal companion easter-egg. It's a single line of text, but it's *alive*: every status-bar refresh re-samples the wall clock and your session state, so the little guy keeps fidgeting, posing and talking.

**It's built from four layers** — so you never get a lone bare face just sitting there:

```
\(^ww^)/  ♥♥♥  proud of you
│         │    └─ quip — dimmed, lands on 3 frames out of 4
│         └────── symbol — on every frame, so it's never a bare face
└──────────────── pose + face — paws, water, chewing, blinking, winking
```

- **Pose** — `\ /` paws up, `/` waving, `~ ~` floating in the water, `?` head tilt
- **Face** — eyes track context usage; the mouth chews through `oo → Oo → oO → ww → vv`, with the occasional blink `(-oo-)` and wink `(^oo-)`
- **Symbol** — shows on *every* frame, so the buddy is never just a face
- **Quip** — lands on 3 frames out of 4, rotating through the current mood's pool

**Eyes** follow your context usage:

| Context | Eyes | State |
|---|---|---|
| < 50% | `^` | happy — `(^oo^)` |
| 50 – WARN | `·` | awake — `(·oo·)` |
| WARN – DANGER | `-` | tired — `(-oo-)` |
| ≥ DANGER | `×` | exhausted — `(×oo×)` |

**Nine moods** — your session state picks one, and everyday moods rotate through whatever beats are left:

| Mood | When | Symbols | Sample quips |
|---|---|---|---|
| `alert` | rate limit ≥ 90% | `!!!` `! !` `!?!` | breathe, you ok? · go outside, i'll wait · hydrate maybe? |
| `fried` | context ≥ DANGER | `×××` `!?!` `@@@` | brain full, send help · /compact. please. · everything is soup |
| `sleepy` | context ≥ WARN | `zzz` `zZz` `- - -` | eyelids: heavy · /compact soon? · maybe wrap this one up |
| `rich` | cost ≥ $5 | `$$$` `★★★` `$★$` | simply built different · capy has a corp card · wow. ok. luxury. |
| `cash` | cost ≥ $1 | `$$$` `¢¢¢` | worth every cent · investing in ourselves · the tokens flow |
| `happy` | context < 50% (everyday) | `♥♥♥` `✧✧✧` `♪♥♪` | you got this · chef's kiss · ship it, friend · big brain hours |
| `chill` | everyday rotation | `♪♪♪` `. . .` `♪ ♪` | no thoughts, just grass · unbothered. moisturized. · floating along |
| `snack` | everyday rotation | `*nom*` `*munch*` `°°°` | is that a tangerine? · one (1) melon please · grass o'clock |
| `silly` | everyday rotation | `^_^` `:3` `owo` `>_<` | capybara.exe running · pro sitting expert · will work for melon |

- Ordinary state moods (`sleepy` / `cash` / `rich`) own 2 beats in 3; the third goes to an everyday mood so it never gets samey.
- **The two real warnings (`alert` / `fried`) own every beat** — when something's actually wrong the buddy doesn't wander off into "la la la~".

So you'll catch things like `\(^ww^)/ ♥♥♥ proud of you`, `~(-oo-)~ zZz so very sleepy`, or `\(×oo×)/ !?! /compact. please.`

**Colour tiers — the more you use it today, the flashier it gets**

The buddy starts gold. As **today's cumulative API working time** climbs, it unlocks more colour:

| API time today | Tier | Look |
|---|:--:|---|
| < 1 h | 1 | all gold — `(^oo^) ♥♥♥` |
| 1 – 3 h | 2 | the **symbol** takes the mood's colour (happy pink, chill blue, snack orange…) |
| 3 – 8 h | 3 | **face and symbol** both coloured — pale face, vivid symbol |
| ≥ 8 h | 4 | the **whole critter goes rainbow**, per character, hue scrolling with the clock |

- It counts `cost.total_api_duration_ms` — time actually spent calling the API. Leaving a session idle earns you nothing.
- Note this runs much *slower* than the wall clock for ordinary serial use (roughly 15% of it), but *faster* when you fan out — ten agents running in parallel for a minute bank ten minutes of API time. So tier 4 is really the "I ran a lot of parallel work today" achievement.
- Each session only knows its own duration, so the daily total is accumulated in `~/.claude/statusline-buddy.json` (`{"date":…,"sessions":{"<session_id>":<ms>}}`), **reset every midnight**.
- The status line re-renders several times a second, so it **only writes to disk when the current session gains ≥5s of API time** — otherwise it's read-only.
- Needs a 256-colour terminal (Windows Terminal, iTerm2, and essentially every modern one qualify).

| Env var | Effect |
|---|---|
| `BUDDY_TIERS="60,180,480"` | Minute thresholds that unlock tiers 2 / 3 / 4 |
| `BUDDY_TIER=4` | Pin a tier to preview it (never writes the state file) |
| `BUDDY_NOW=<int>` | Freeze the animation phase for frame-by-frame debugging |

**Under the hood**
- **0 tokens, fully local** — it's computed by the statusline script and drawn in your terminal; nothing is ever sent to the model.
- The symbol is bold, the quip is dimmed, so it never crowds the rest of the bar.
- Want different lines? Edit the `MOODS` table in `statusline.py` / `statusline.js` — every mood's `pose` / `sym` / `says` list is free to grow. Two conventions: keep quips under 24 chars so narrow terminals don't wrap, and keep `pose` and `sym` on different characters or you get muddle like `zZ z Z z`.
- Fails silent — if anything ever goes wrong the buddy just hides, the rest of the status line is untouched. If the state file can't be read or written it quietly falls back to tier 1.

### 2. PDF Compressor (`pdf-compressor`)
Automatically compresses large PDF files using Ghostscript to ensure they fit within API limits or to optimize processing speed.

- **Triggers:** "Compress report.pdf", "Reduce size of PDF", or automatically for files > 10MB.
- **Key Features:** 
  - Multiple quality presets (`screen`, `ebook`, `printer`, `prepress`).
  - Automatic backup of original files.
  - Significant size reduction for image-heavy documents.
- **Setup & Prerequisites:**
  - **Dependency:** [Ghostscript](https://ghostscript.com/releases/gsdnld.html).
  - Ensure `gswin64c` (Windows) or `gs` (Linux/macOS) is in your PATH.

### 3. PDF Figure Extractor (`pdf-figure-extractor`)
Extracts figures and tables from PDF documents using the [TF-ID](https://github.com/ai8hyf/TF-ID) (Florence2-based) object detection model.

- **Triggers:** "Extract all figures from this PDF", "Get the tables from paper.pdf".
- **Key Features:**
  - High-accuracy detection of academic paper layout elements.
  - Outputs cropped images and a Markdown index for easy review.
  - Supports specific page range extraction.
- **Setup & Prerequisites:**
  1. **Install Poppler:**
     - **Windows:** Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) and add `bin` to System PATH.
     - **macOS:** `brew install poppler`
     - **Linux:** `sudo apt-get install poppler-utils`
  2. **Create Conda Environment:**
     ```bash
     conda create -n TF-ID python=3.10 -y
     conda activate TF-ID
     pip install torch torchvision transformers timm einops pillow opencv-python pdf2image accelerate
     ```

### 4. English-to-Chinese Paper PDF (`pdf-e2c`)
Turns an English research paper into a clean Chinese-version PDF — reflowed to a single column, with every figure, table and equation cropped straight out of the original PDF at full resolution and placed back near its reference.

- **Triggers:** "把这篇论文转成中文", "translate this paper to Chinese pdf", "英文论文转中文版".
- **Key Features:**
  - **Not** layout-preserving by design — Chinese and English occupy very different space, so the double-column original is reflowed into free-flowing single column instead of being squeezed into the old frame.
  - Figures/tables/equations are pixel-perfect crops of the source PDF ("用原图"), never re-rendered or re-drawn.
  - Body text, headings and captions are translated; references stay in English as convention dictates.
  - Claude does the translation and layout calls; the scripts only do the mechanical extract → crop → typeset work.
- **Setup & Prerequisites:**
  - `pip install pymupdf reportlab pillow`
  - Chinese font uses reportlab's built-in CID font `STSong-Light` — no font files to install.

### 5. Video Subtitle Extractor (`video-subtitle-extractor`)
Extracts and saves subtitles from Bilibili and YouTube videos as plain `.txt` files.

- **Triggers:** "Extract subtitles from this YouTube link: [URL]", "Get captions from Bilibili video".
- **Key Features:**
  - Supports both Bilibili and YouTube.
  - Smart language priority (defaults to Chinese/English).
  - Support for login-gated videos via `cookies.txt`.
- **Setup & Prerequisites:**
  - **Dependency:** `pip install yt-dlp`.
  - **Cookie Setup (Optional):** To extract subtitles from login-gated or members-only videos:
    1. Use a browser extension (e.g., "Get cookies.txt LOCALLY") to export your cookies.
    2. Save the downloaded cookie file directly into the `video-subtitle-extractor/cookies` folder (no renaming necessary).
  - Ensure `yt-dlp` is accessible in your environment.

### 6. Video Download with Bilingual Subtitles (`video-download`)
Downloads the video itself, rebuilds its captions, and archives everything as a single `.mkv` carrying both subtitle tracks — with the `.srt` files kept alongside so they stay editable and greppable. The companion to `video-subtitle-extractor`: that one gives you a transcript, this one gives you something watchable.

- **Triggers:** "下载视频", "双语字幕", "校对字幕", usually alongside a YouTube/Bilibili URL.
- **Key Features:**
  - **De-rolls rolling captions.** Auto-captions repeat the previous cue and append one line, padded with 10ms filler cues — an 18-minute talk becomes ~980 cues holding ~490 real lines, which plays as flickering, stuttering duplicate text. This fixes the timeline.
  - **Proofreads the mishears first.** Machine translation is *faithful* — it faithfully translates whatever the recogniser misheard, so `LLMs`→`Hums` arrives in Chinese as 「哼唱」, `agentic`→`a gentic` as 「基因」. The English pass runs before the Chinese pass, because garbage in, garbage out.
  - Keeps technical terms in English (`agent`, `prompt`, `PR`, `token`, library names); translates only concepts with settled Chinese equivalents.
  - Asks before the expensive proofreading pass — decline and you still get de-rolled captions and the `.mkv`, just with the machine translation untouched.
  - Remuxed with `-c copy`: no re-encoding, no quality loss, Chinese track on by default.
- **Setup & Prerequisites:** `yt-dlp` (`pip install yt-dlp`), `node`, and `ffmpeg` in PATH. Cookie setup for login-gated videos works the same way as `video-subtitle-extractor` — and the two skills share one cookies folder.

### 7. Project Summary (`project-summary`)
Analyzes a GitHub project (URL or local path) and generates a comprehensive `architecture.md` in Simplified Chinese, with auto-selected ASCII architecture diagrams.

- **Triggers:** "Analyze this GitHub project", "Generate architecture.md", "Summarize project structure".
- **Key Features:**
  - Auto-selects diagram style (pipeline / layered / dependency tree / microservices / request flow / nested components) via a decision tree.
  - Width-adaptive ASCII diagrams (80 / 120 columns) with CJK double-width alignment rules.
  - Produces a structured `architecture.md` covering tech stack, components, data flow, and design decisions.
- **Setup & Prerequisites:** None — uses only Claude Code's built-in file and shell tools.
- **Example output (excerpt):**

  ```
  ┌─────────────────────────────────────┐
  │            主应用入口                │
  │           main.py / index.js         │
  └──────┬──────────────┬───────────────┘
         │              │
         ▼              ▼
  ┌──────────┐    ┌──────────┐
  │  模块 A  │    │  模块 B  │
  │  auth/   │    │  api/    │
  └────┬─────┘    └────┬─────┘
       │               │
       ▼               ▼
  ┌──────────┐    ┌──────────┐
  │  工具库  │    │  数据库  │
  │  utils/  │    │   db/    │
  └──────────┘    └──────────┘
  ```

### 8. Claude-Style HTML (`claude-html`)
A complete design system for producing HTML in Anthropic's / Claude's understated visual language — ivory ground, clay-orange (`#D97757`) accents, no JavaScript, and both light and dark themes working out of the box.

- **Triggers:** "make an HTML report / retrospective / dashboard", "Claude 风格", "Anthropic 风格", "简约风格", or turning an existing page into this style.
- **Key Features:**
  - **Two ready-to-open templates:** `project.html` (project architecture + work progress) and `starter.html` (data report / retrospective) — editing content beats writing from zero.
  - **Four built-in architecture diagram classes** — system pipeline, model layers, module dependencies, training loops — with rules for what actually belongs on a diagram (frequency, latency, parameter count, tensor shapes, real topic names).
  - **Zero JavaScript.** All interaction is pure CSS (radio / checkbox / details), all charts are inline SVG — so it survives artifacts, email clients, and offline archives where JS is stripped.
  - **Opinionated style rules** that keep it from drifting into generic AI aesthetics: clay is an accent and never the body color, status colors stay earthy, borders are 1px and shadows nearly absent, whitespace does the separating.
  - Optional `harvest_openspec.py` pulls recent changes out of an OpenSpec project into `progress.json` for the progress board.
- **Setup & Prerequisites:** None for the HTML itself. The OpenSpec harvester needs Python 3 and an OpenSpec-managed project.

### 9. Plain-Language Explainer (`speak-human`)
Re-explains jargon-dense content in plain language — one-sentence conclusion, a single everyday analogy carried all the way through, an ASCII diagram, what it means for *your* situation, and a term-mapping table. It changes how something is said, never what it says.

- **Triggers:** "说人话", "讲人话", "听不懂", "太专业了", "用大白话解释", or `/speak-human` to redo the previous reply. Also works on pasted error messages, docs, and paper excerpts.
- **Key Features:**
  - **Fixed five-block output** so nothing important gets dropped — especially the "具体到你这件事" block, without which an analogy floats free and the reader still doesn't know what to do.
  - **Three difficulty levels** that adjust on "还是不懂" (down a level, new analogy) or "不用这么啰嗦" (up a level).
  - Hard language rules: no bare acronyms, one idea per sentence under 30 characters, numbers get a reference point (`300ms` → "about one blink"), no written-register filler.
  - **Accuracy outranks simplicity** — caveats, limits and risks may never be deleted in the name of "keeping it simple", and a distorting analogy has to say where it distorts.
  - Eight ASCII diagram templates (flow, layers, before/after, loop, timeline, proportion, containment, trade-off) with CJK column-width alignment handled.
- **Setup & Prerequisites:** None.

### 10. Excalidraw Diagram Generator (`obsidian-excalidraw`)
Generates Excalidraw diagrams as Obsidian-ready `.md` files, with first-class support for AI model architecture diagrams — VLA, Transformer, Diffusion Policy, multi-system pipelines.

- **Triggers:** "画图", "架构图", "模型结构", "流程图", "思维导图", "Excalidraw", "diagram".
- **Key Features:**
  - **A `Builder` class instead of hand-written JSON** — seven helpers (`rect` / `text` / `arrow` / `ellipse` / `subbox` / `parent_box` / `module`) that handle index allocation, bidirectional element binding and serialization for you.
  - Runs **7 sanity checks before writing**, covering every known pitfall in the Excalidraw file format.
  - Architecture-aware conventions: tensor shapes annotated at every dimension change, left→right for forward passes, top→bottom for hierarchy, subsystem grouping (System 1/2, train/inference, perception/action).
  - Includes a palette dictionary and a reference library of AI architecture patterns.
- **Setup & Prerequisites:** Python 3 to run the builder. Obsidian with the Excalidraw plugin to view/edit the result.

---

## How to Add Skills to Claude Code

There are three ways to let Claude Code "learn" these skills — pick whichever is most convenient.

### Option A: Just Hand Claude the Link (Recommended — Easiest)
The least-effort path: paste this repo's URL into Claude Code and let it do the rest — it will read the repo, find the skill you need, and install or run it for you. No manual copying, no path juggling.
> "Here's a skills repo: https://github.com/TingdeLiu/Tyndall-Skills — install the `claude-code-statusline` skill for me."

### Option B: Global Registration
Copy the skill folder to your local Claude Code skills directory. This makes the skill available in all your projects.
```bash
# Windows (Replace 'skill-folder-name' with e.g., 'pdf-compressor')
xcopy /E /I .\skill-folder-name %USERPROFILE%\.claude\skills\skill-folder-name

# macOS/Linux
cp -r ./skill-folder-name ~/.claude/skills/
```

### Option C: Contextual Reference
If you don't want to install them globally, simply reference the `SKILL.md` file in your chat:
> "Help me compress this file based on @pdf-compressor/SKILL.md"

---
*Created and maintained by [Tingde Liu](https://github.com/TingdeLiu).*
