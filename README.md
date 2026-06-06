# Tyndall-Skills

A curated collection of custom Claude Code skills (SKILL.md templates) and automation scripts designed to extend AI capabilities and streamline complex development and productivity workflows.

English | [中文](README_CN.md)

## Skills Quick Link
- [Claude Code Statusline](#1-claude-code-statusline-cc-plus)
- [PDF Compressor](#2-pdf-compressor-pdf-compressor)
- [PDF Figure Extractor](#3-pdf-figure-extractor-pdf-figure-extractor)
- [Video Subtitle Extractor](#4-video-subtitle-extractor-video-subtitle-extractor)
- [Project Summary](#5-project-summary-project-summary)
- [How to Add Skills to Claude Code](#how-to-add-skills-to-claude-code)

---

## Available Skills

### 1. Claude Code Statusline (`cc-plus`)
A cross-platform Claude Code enhancement that adds a custom status line and a completion notification sound on Windows and macOS.

![Claude Code status line](images/claude-status.png)

- **Triggers:** "Set up a statusline", "Configure Claude Code statusLine", "Play a sound when Claude finishes", or failures of bash/jq-based statusline scripts.
- **Key Features:**
  - Shows model name, color-coded context-usage bar, session cost (USD), and 5h/7d rate-limit percentages.
  - Plays a notification sound (Ding / Chime / Beep) via `afplay` on macOS or PowerShell on Windows when Claude finishes a response.
  - Color thresholds configurable via `WARN_PCT` / `DANGER_PCT` environment variables.
  - Auto-detects Python or Node.js — no `jq` dependency, no Unicode encoding errors.
  - **Easter-egg buddy 🐣:** an optional golden capybara `(^oo^)` lives at the end of the status line — it idle-animates between refreshes (chews, blinks) and reacts to your context / cost / rate-limit state with little emotes (`♥♥♥` `zzz` `!!!`). Fully local, **0 tokens**.
- **Setup & Prerequisites:**
  - Python 3 or Node.js available in PATH.
  - Install the skill into `~/.claude/skills/cc-plus/` (see [How to Add Skills to Claude Code](#how-to-add-skills-to-claude-code)), then ask Claude **"set up my Claude Code statusline"** — it'll detect your OS and runtime, ask for your sound preference, and wire up the script + `settings.json` automatically.

#### 🐣 Meet your buddy — the golden capybara

Tucked at the end of the status line lives a tiny golden capybara, ported from Claude Code's internal companion easter-egg. It's a single line of text, but it's *alive*: every status-bar refresh re-samples the wall clock and your session state, so the little guy keeps fidgeting and reacting.

**Idle animation** (time-driven — changes between refreshes)
- Chewing: `(^oo^)` → `(^Oo^)` → `(^oO^)`
- Blinking: every so often a quick `(-oo-)`

**Mood** — the eyes follow your context usage:

| Context | Eyes | State |
|---|---|---|
| < 50% | `^` | happy — `(^oo^)` |
| 50 – WARN | `·` | awake — `(·oo·)` |
| WARN – DANGER | `-` | tired — `(-oo-)` |
| ≥ DANGER | `×` | exhausted — `(×oo×)` |

**Occasional emotes** — now and then a symbol + a warm/silly quip pops out; the quip rotates through a pool so it's never quite the same twice:

| Symbol | When | Sample quips |
|---|---|---|
| `♥♥♥` | context is roomy | you got this · proud of you · we're vibing |
| `~~~` | random | la la la~ · just chillin' · doot doot doot |
| `zzz` | context ≥ WARN | 5 more minutes · so very sleepy · ok... carry on |
| `$$$` | cost ≥ $1 | worth every cent · treat yourself · ooh, fancy |
| `!!!` | rate limit ≥ 90% | breathe, you ok? · ease up soon · take a lil break |

So you'll catch things like `(^oo^) ♥♥♥ you got this` or `(×oo×) !!! breathe, you ok?`.

**Under the hood**
- **0 tokens, fully local** — it's computed by the statusline script and drawn in your terminal; nothing is ever sent to the model.
- The symbol is bold gold, the quip is dimmed, so it never crowds the rest of the bar.
- Want different lines? Edit the `QUIPS` table in `statusline.py` / `statusline.js`.
- Fails silent — if anything ever goes wrong the buddy just hides, the rest of the status line is untouched.

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

### 4. Video Subtitle Extractor (`video-subtitle-extractor`)
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

### 5. Project Summary (`project-summary`)
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

---

## How to Add Skills to Claude Code

There are three ways to let Claude Code "learn" these skills — pick whichever is most convenient.

### Option A: Just Hand Claude the Link (Recommended — Easiest)
The least-effort path: paste this repo's URL into Claude Code and let it do the rest — it will read the repo, find the skill you need, and install or run it for you. No manual copying, no path juggling.
> "Here's a skills repo: https://github.com/TingdeLiu/Tyndall-Skills — install the `cc-plus` statusline skill for me."

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
