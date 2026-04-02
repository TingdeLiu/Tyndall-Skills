# Tyndall-Skills

A curated collection of custom Claude Code skills (SKILL.md templates) and automation scripts designed to extend AI capabilities and streamline complex development and productivity workflows.

English | [中文](README_CN.md)

## Skills Quick Link
- [PDF Compressor](#1-pdf-compressor-pdf-compressor)
- [PDF Figure Extractor](#2-pdf-figure-extractor-pdf-figure-extractor)
- [Video Subtitle Extractor](#3-video-subtitle-extractor-video-subtitle-extractor)
- [How to Add Skills to Claude Code](#how-to-add-skills-to-claude-code)

---

## Available Skills

### 1. PDF Compressor (`pdf-compressor`)
Automatically compresses large PDF files using Ghostscript to ensure they fit within API limits or to optimize processing speed.

- **Triggers:** "Compress report.pdf", "Reduce size of PDF", or automatically for files > 10MB.
- **Key Features:** 
  - Multiple quality presets (`screen`, `ebook`, `printer`, `prepress`).
  - Automatic backup of original files.
  - Significant size reduction for image-heavy documents.
- **Setup & Prerequisites:**
  - **Dependency:** [Ghostscript](https://ghostscript.com/releases/gsdnld.html).
  - Ensure `gswin64c` (Windows) or `gs` (Linux/macOS) is in your PATH.

### 2. PDF Figure Extractor (`pdf-figure-extractor`)
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

### 3. Video Subtitle Extractor (`video-subtitle-extractor`)
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

---

## How to Add Skills to Claude Code

To let Claude Code "learn" these skills, you have two options:

### Option A: Global Registration (Recommended)
Copy the skill folder to your local Claude Code skills directory. This makes the skill available in all your projects.
```bash
# Windows (Replace 'skill-folder-name' with e.g., 'pdf-compressor')
xcopy /E /I .\skill-folder-name %USERPROFILE%\.claude\skills\skill-folder-name

# macOS/Linux
cp -r ./skill-folder-name ~/.claude/skills/
```

### Option B: Contextual Reference
If you don't want to install them globally, simply reference the `SKILL.md` file in your chat:
> "Help me compress this file based on @pdf-compressor/SKILL.md"

---
*Created and maintained by [Tingde Liu](https://github.com/TingdeLiu).*
