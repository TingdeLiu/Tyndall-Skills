# Tyndall-Skills

A curated collection of custom Claude Code skills (SKILL.md templates) and automation scripts designed to extend AI capabilities and streamline complex development and productivity workflows.

## Available Skills

### 1. PDF Compressor (`pdf-compressor`)
Automatically compresses large PDF files using Ghostscript to ensure they fit within API limits or to optimize processing speed.
- **Triggers:** Automatically activates for PDFs > 10MB, when API limits (32MB) are exceeded, or upon manual request.
- **Key Features:** 
  - Multiple quality presets (`screen`, `ebook`, `printer`, `prepress`).
  - Automatic backup of original files.
  - Significant size reduction for image-heavy documents.
- **Dependencies:** [Ghostscript](https://ghostscript.com/releases/gsdnld.html).

### 2. PDF Figure Extractor (`pdf-figure-extractor`)
Extracts figures and tables from PDF documents using the TF-ID (Florence2-based) object detection model.
- **Triggers:** Triggered by requests like "extract all figures from this PDF" or "get the tables from paper.pdf".
- **Key Features:**
  - High-accuracy detection of academic paper layout elements.
  - Outputs cropped images and a Markdown index for easy review.
  - Supports specific page range extraction.
- **Dependencies:** Conda environment `TF-ID`, `pdf2image`, `transformers`, `pillow`.

### 3. Video Subtitle Extractor (`video-subtitle-extractor`)
Extracts and saves subtitles from Bilibili (B站) and YouTube videos as plain `.txt` files.
- **Triggers:** Triggered when a video URL is provided with a request for subtitles, captions, or transcripts.
- **Key Features:**
  - Supports both Bilibili and YouTube.
  - Smart language priority (defaults to Chinese/English).
  - Support for login-gated videos via `cookies.txt`.
- **Dependencies:** `yt-dlp`.

## Setup & Usage | 安装与使用

### 1. Prerequisites | 环境准备
Ensure you have the core dependencies installed for each skill:
- **PDF Compressor:** [Ghostscript](https://ghostscript.com/releases/gsdnld.html)
- **PDF Figure Extractor:** Requires a specific Conda environment and system-level `poppler`:
  1. **Install Poppler:**
     - **Windows:** Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) and add the `bin` folder to your System PATH.
     - **macOS:** `brew install poppler`
     - **Linux:** `sudo apt-get install poppler-utils`
  2. **Create Conda Environment:**
     ```bash
     conda create -n TF-ID python=3.10 -y
     conda activate TF-ID
     pip install torch torchvision transformers timm einops pillow opencv-python pdf2image accelerate
     ```
- **Video Subtitle Extractor:** `pip install yt-dlp`

### 2. Add to Claude Code | 注册到 Claude Code
To let Claude Code "learn" these skills, you have two options:

**Option A: Global Registration (Recommended)**
Copy the skill folders to your local Claude Code skills directory:
```bash
# Windows
xcopy /E /I .\pdf-compressor %USERPROFILE%\.claude\skills\pdf-compressor
# macOS/Linux
cp -r ./pdf-compressor ~/.claude/skills/
```

**Option B: Contextual Reference**
If you don't want to install them globally, simply reference the `SKILL.md` file in your chat:
> "Help me compress this file based on @pdf-compressor/SKILL.md"

### 3. Usage Steps | 使用步骤
Once registered, you can use natural language to trigger the workflows:

1. **Invoke:** Type a command like "Compress report.pdf" or "Extract subtitles from this YouTube link: [URL]".
2. **Review:** Claude will check the dependencies and file size automatically.
3. **Confirm:** For commands that modify files or run scripts, Claude will ask for your confirmation.
4. **Result:** The processed files (compressed PDFs, extracted images, or subtitle text) will be saved to the specified directory.

---
*Created and maintained by [Tingde Liu](https://github.com/TingdeLiu).*
