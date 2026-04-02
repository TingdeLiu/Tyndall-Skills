# Tyndall-Skills

精选的自定义 Claude Code 技能（SKILL.md 模板）和自动化脚本集合，旨在扩展 AI 能力并简化复杂的开发和生产力工作流程。

[English](README.md) | 中文

## 技能快速跳转
- [PDF 压缩器](#1-pdf-压缩器-pdf-compressor)
- [PDF 图表提取器](#2-pdf-图表提取器-pdf-figure-extractor)
- [视频字幕提取器](#3-视频字幕提取器-video-subtitle-extractor)
- [如何将技能添加到 Claude Code](#如何将技能添加到-claude-code)

---

## 可用技能

### 1. PDF 压缩器 (`pdf-compressor`)
使用 Ghostscript 自动压缩大型 PDF 文件，确保它们符合 API 限制或优化处理速度。

- **触发条件：** “压缩 report.pdf”、“减小 PDF 大小”，或在文件 > 10MB 时自动激活。
- **核心功能：** 
  - 多种质量预设（`screen`、`ebook`、`printer`、`prepress`）。
  - 自动备份原始文件。
  - 针对包含大量图像的文档显著减小体积。
- **设置与前提条件：**
  - **依赖项：** [Ghostscript](https://ghostscript.com/releases/gsdnld.html)。
  - 确保 `gswin64c` (Windows) 或 `gs` (Linux/macOS) 已添加到系统 PATH。

### 2. PDF 图表提取器 (`pdf-figure-extractor`)
使用 [TF-ID](https://github.com/ai8hyf/TF-ID)（基于 Florence2）目标检测模型从 PDF 文档中提取图表和表格。

- **触发条件：** “提取此 PDF 中的所有图表”、“获取 paper.pdf 中的表格”。
- **核心功能：**
  - 高精度检测学术论文布局元素。
  - 输出裁剪后的图像和 Markdown 索引，方便查看。
  - 支持特定页码范围提取。
- **设置与前提条件：**
  1. **安装 Poppler：**
     - **Windows：** 从 [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) 下载并将 `bin` 文件夹添加到系统 PATH。
     - **macOS：** `brew install poppler`
     - **Linux：** `sudo apt-get install poppler-utils`
  2. **创建 Conda 环境：**
     ```bash
     conda create -n TF-ID python=3.10 -y
     conda activate TF-ID
     pip install torch torchvision transformers timm einops pillow opencv-python pdf2image accelerate
     ```

### 3. 视频字幕提取器 (`video-subtitle-extractor`)
从 Bilibili 和 YouTube 视频中提取字幕并保存为纯 `.txt` 文件。

- **触发条件：** “从这个 YouTube 链接提取字幕：[URL]”、“获取 Bilibili 视频的字幕”。
- **核心功能：**
  - 支持 Bilibili 和 YouTube。
  - 智能语言优先级（默认为中文/英文）。
  - 通过 `cookies.txt` 支持登录限制视频。
- **设置与前提条件：**
  - **依赖项：** `pip install yt-dlp`。
  - **Cookie 设置（可选）：** 若要提取需登录或大会员可见的视频字幕：
    1. 使用浏览器扩展（如“Get cookies.txt LOCALLY”）导出你的 Cookie。
    2. 将下载好的 Cookie 文件直接放入 `video-subtitle-extractor/cookies` 文件夹即可（无需改名）。
  - 确保 `yt-dlp` 在你的环境中可以访问。

---

## 如何将技能添加到 Claude Code

要让 Claude Code “学习”这些技能，你有两个选择：

### 选项 A：全局注册（推荐）
将技能文件夹复制到本地 Claude Code 技能目录。这使得该技能在你所有的项目中都可用。
```bash
# Windows (将 'skill-folder-name' 替换为例如 'pdf-compressor')
xcopy /E /I .\skill-folder-name %USERPROFILE%\.claude\skills\skill-folder-name

# macOS/Linux
cp -r ./skill-folder-name ~/.claude/skills/
```

### 选项 B：上下文引用
如果你不想全局安装它们，只需在对话中引用 `SKILL.md` 文件：
> “请根据 @pdf-compressor/SKILL.md 帮我压缩这个文件”

---
*由 [Tingde Liu](https://github.com/TingdeLiu) 创建并维护。*
