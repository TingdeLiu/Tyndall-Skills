# Tyndall-Skills

精选的自定义 Claude Code 技能（SKILL.md 模板）和自动化脚本集合，旨在扩展 AI 能力并简化复杂的开发和生产力工作流程。

[English](README.md) | 中文

## 技能一览

| # | 技能 | 做什么 | 依赖 |
|:--:|---|---|---|
| 1 | [**Claude Code 状态栏**](#1-claude-code-状态栏-cc-plus)<br>`cc-plus` | 自定义状态栏 —— 模型、上下文进度条、会话花费、速率限制 —— 外加完成提示音和一只金色卡皮巴拉 🐣 | Python 3 **或** Node |
| 2 | [**PDF 压缩器**](#2-pdf-压缩器-pdf-compressor)<br>`pdf-compressor` | 把超大 PDF 压到符合 API 限制，四档质量预设，自动备份原文件 | Ghostscript |
| 3 | [**PDF 图表提取器**](#3-pdf-图表提取器-pdf-figure-extractor)<br>`pdf-figure-extractor` | 用 TF-ID 模型检测并裁切论文里的图和表，附带 Markdown 索引 | Conda 环境 + Poppler |
| 4 | [**英文论文转中文 PDF**](#4-英文论文转中文-pdf-pdf-e2c)<br>`pdf-e2c` | 把英文论文重排成单栏中文 PDF，图/表/公式从原 PDF 高清裁切插回 | `pymupdf` `reportlab` `pillow` |
| 5 | [**视频字幕提取器**](#5-视频字幕提取器-video-subtitle-extractor)<br>`video-subtitle-extractor` | 从 YouTube / Bilibili 扒下字幕存成纯 `.txt` —— 只想要文字稿时用它 | `yt-dlp` |
| 6 | [**视频 + 双语字幕**](#6-视频下载与双语字幕-video-download)<br>`video-download` | 下载视频、拆掉滚动字幕并校对，打包成一个内嵌双语轨的 `.mkv` | `yt-dlp` `node` `ffmpeg` |
| 7 | [**项目架构摘要**](#7-项目架构摘要-project-summary)<br>`project-summary` | 读一个仓库（URL 或本地路径），生成 `architecture.md` 和自动选型的 ASCII 架构图 | 无 |
| 8 | [**Claude 风格 HTML**](#8-claude-风格-html-claude-html)<br>`claude-html` | 把 Anthropic 的视觉语言做成可用的设计系统：两个模板、四类架构图、零 JavaScript | 无 |
| 9 | [**说人话**](#9-说人话-speak-human)<br>`speak-human` | 把术语重讲成：一句话结论 + 一个类比 + 一张 ASCII 图 + 一张术语对照表 | 无 |
| 10 | [**Excalidraw 架构图**](#10-excalidraw-架构图生成-obsidian-excalidraw)<br>`obsidian-excalidraw` | 把文本变成 Obsidian 可直接打开的 Excalidraw 图，专攻 AI 模型架构（VLA、Transformer、Diffusion Policy） | Python 3 + Obsidian |

→ [如何将技能添加到 Claude Code](#如何将技能添加到-claude-code)

---

## 可用技能

### 1. Claude Code 状态栏 (`cc-plus`)
跨平台的 Claude Code 增强技能，为 Windows 和 macOS 同时提供自定义状态栏与响应完成提示音。

![Claude Code 状态栏效果](images/claude-status.png)

- **触发条件：** “配置 Claude Code 状态栏”、”Claude 回复完成后播放提示音”，或 bash/jq 状态栏脚本失败时使用。
- **核心功能：**
  - 显示模型名称、按使用量上色的上下文进度条、当前会话累计花费（美元）以及 5 小时 / 7 天速率限制百分比。
  - Claude 完成响应后自动播放提示音（叮咚 / 铃声 / 蜂鸣），macOS 使用 `afplay`，Windows 使用 PowerShell。
  - 颜色警告阈值可通过 `WARN_PCT` / `DANGER_PCT` 环境变量自定义。
  - 自动检测 Python 或 Node.js —— 不依赖 `jq`，无 Unicode 编码错误。
  - **彩蛋宠物 🐣：** 状态栏行尾住着一只可选的金色卡皮巴拉 `(^oo^)` —— 它会在刷新之间做待机动画（嚼东西、眨眼），并根据上下文用量 / 花费 / 速率限制冒出小表情（`♥♥♥` `zzz` `!!!`）。纯本地运行，**0 token 消耗**。
- **设置与前提条件：**
  - 系统 PATH 中需要 Python 3 或 Node.js。
  - 将该技能安装到 `~/.claude/skills/cc-plus/`（参见 [如何将技能添加到 Claude Code](#如何将技能添加到-claude-code)），然后对 Claude 说 **”帮我配置 Claude Code 状态栏”** —— 它会自动检测操作系统和运行时，询问提示音偏好，并完成脚本与 `settings.json` 的全部配置。

#### 🐣 认识你的宠物 —— 金色卡皮巴拉

状态栏行尾住着一只金色的小卡皮巴拉，移植自 Claude Code 内置的 companion 彩蛋。它只是一行文字，却是**活的**：每次状态栏刷新都会重新读取当前时间和会话状态，所以这小家伙会不停地动、不停地对你的状态做出反应。

**待机动画**（时间驱动，刷新之间持续变化）
- 嚼东西：`(^oo^)` → `(^Oo^)` → `(^oO^)`
- 眨眼：偶尔快速 `(-oo-)` 一下

**心情** —— 眼睛随上下文用量变化：

| 上下文 | 眼睛 | 状态 |
|---|---|---|
| < 50% | `^` | 开心 —— `(^oo^)` |
| 50 – WARN | `·` | 清醒 —— `(·oo·)` |
| WARN – DANGER | `-` | 疲惫 —— `(-oo-)` |
| ≥ DANGER | `×` | 累瘫 —— `(×oo×)` |

**偶发反应** —— 时不时冒出一个符号 + 一句暖心/俏皮的话；话语从短语池里随时间轮换，所以每次都不太一样：

| 符号 | 触发条件 | 短语示例（卡皮巴拉淡定治愈风） |
|---|---|---|
| `♥♥♥` | ctx 宽裕时 | you got this · proud of you · we're vibing |
| `~~~` | 随机 | la la la~ · just chillin' · doot doot doot |
| `zzz` | ctx ≥ WARN | 5 more minutes · so very sleepy · ok... carry on |
| `$$$` | 花费 ≥ $1 | worth every cent · treat yourself · ooh, fancy |
| `!!!` | 限额 ≥ 90% | breathe, you ok? · ease up soon · take a lil break |

所以你会时不时看到 `(^oo^) ♥♥♥ you got this` 或 `(×oo×) !!! breathe, you ok?` 这样的画面。

**技术原理**
- **0 token，纯本地** —— 它由状态栏脚本本地计算、画在你的终端里，**任何内容都不会发给模型**。
- 符号是金色加粗，话语用暗色柔和呈现，不抢状态栏其它信息。
- 想换台词？编辑 `statusline.py` / `statusline.js` 里的 `QUIPS` 表即可。
- 容错设计 —— 一旦出错宠物就静默隐藏，状态栏其余部分完全不受影响。

### 2. PDF 压缩器 (`pdf-compressor`)
使用 Ghostscript 自动压缩大型 PDF 文件，确保它们符合 API 限制或优化处理速度。

- **触发条件：** “压缩 report.pdf”、“减小 PDF 大小”，或在文件 > 10MB 时自动激活。
- **核心功能：** 
  - 多种质量预设（`screen`、`ebook`、`printer`、`prepress`）。
  - 自动备份原始文件。
  - 针对包含大量图像的文档显著减小体积。
- **设置与前提条件：**
  - **依赖项：** [Ghostscript](https://ghostscript.com/releases/gsdnld.html)。
  - 确保 `gswin64c` (Windows) 或 `gs` (Linux/macOS) 已添加到系统 PATH。

### 3. PDF 图表提取器 (`pdf-figure-extractor`)
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

### 4. 英文论文转中文 PDF (`pdf-e2c`)
把英文论文转成排版干净的中文版 PDF —— 重排为单栏自由流式，图、表、公式全部从原 PDF 高清裁切后插回对应位置附近。

- **触发条件：** “把这篇论文转成中文”、“英文论文转中文版”、“translate this paper to Chinese pdf”。
- **核心功能：**
  - **刻意不保留原版式** —— 中英文占用空间差异大，硬塞进原双栏框架只会挤成一团，所以重排为单栏。
  - 图 / 表 / 公式是原 PDF 的像素级裁切（“用原图”），不重绘、不重新渲染。
  - 正文、标题、图注全部翻译为中文；参考文献按惯例保留英文。
  - 翻译和版面决策由 Claude 完成，脚本只负责机械的提取 → 裁切 → 排版。
- **设置与前提条件：**
  - `pip install pymupdf reportlab pillow`
  - 中文字体使用 reportlab 内置 CID 字体 `STSong-Light`，无需安装字体文件。

### 5. 视频字幕提取器 (`video-subtitle-extractor`)
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

### 6. 视频下载与双语字幕 (`video-download`)
下载视频本体、重建字幕，并打包成一个内嵌双语字幕轨的 `.mkv`，同时把 `.srt` 留在旁边方便继续编辑和检索。它是 `video-subtitle-extractor` 的搭档：那个给你可读的文字稿，这个给你能看的片子。

- **触发条件：** “下载视频”、“双语字幕”、“校对字幕”，通常伴随一个 YouTube / Bilibili 链接。
- **核心功能：**
  - **拆掉滚动字幕。** 自动字幕每一条都重复上一条再追加一行，中间用 10ms 的填充条撑着 —— 18 分钟的演讲会变成约 980 条字幕、实际只有约 490 行内容，直接播放就是不停闪烁的重复文字。这一步把时间轴重建干净。
  - **先校对听错的词，再看中文。** 机翻是“忠实”的 —— 它忠实地翻译了语音识别听错的东西：`LLMs` 听成 `Hums`，中文就成了「哼唱」；`agentic` 听成 `a gentic`，就成了「基因」。所以英文校对必须跑在中文之前，否则就是垃圾进垃圾出。
  - 技术术语保留英文（`agent`、`prompt`、`PR`、`token`、库名），只翻译有公认中文译法的概念。
  - 昂贵的校对环节会先问你 —— 拒绝的话仍然会得到拆好的字幕和 `.mkv`，只是里面是未经校对的机翻。
  - 用 `-c copy` 封装：不转码、无画质损失，中文轨默认开启。
- **设置与前提条件：** PATH 中需要 `yt-dlp`（`pip install yt-dlp`）、`node` 和 `ffmpeg`。登录限制视频的 Cookie 配置方式与 `video-subtitle-extractor` 相同 —— 两个技能共用同一个 cookies 文件夹。

### 7. 项目架构摘要 (`project-summary`)
分析 GitHub 项目（远程仓库 URL 或本地路径），自动生成中文版 `architecture.md`，并配套自动选型的 ASCII 架构图。

- **触发条件：** “分析这个 GitHub 项目”、“生成 architecture.md”、“总结项目结构”。
- **核心功能：**
  - 通过决策树自动选择架构图类型（线性流水线 / 分层架构 / 模块依赖树 / 微服务交互 / 请求处理流 / 嵌套组件）。
  - ASCII 图宽度自适应（80 / 120 列），并处理中英文字符双倍宽对齐。
  - 输出结构化的 `architecture.md`，涵盖技术栈、核心组件、数据流与关键设计决策。
- **设置与前提条件：** 无 —— 仅使用 Claude Code 内置的文件与 Shell 工具。
- **示例输出（节选）：**

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

### 8. Claude 风格 HTML (`claude-html`)
一套完整的设计系统，用 Anthropic / Claude 的克制视觉语言产出 HTML —— 象牙暖底、陶土橙（`#D97757`）点缀、零 JavaScript，明暗双主题开箱即用。

- **触发条件：** “做个 HTML 报告 / 复盘 / 看板”、“Claude 风格”、“Anthropic 风格”、“简约风格”，或把已有页面改造成这套风格。
- **核心功能：**
  - **两个可直接在浏览器打开的模板：** `project.html`（项目架构 + 工作进度）和 `starter.html`（数据报告 / 复盘）—— 改内容远比从零写快。
  - **内置四类架构图** —— 系统管线、模型分层、模块依赖、训练闭环，并规定了图上到底该标什么（频率、延迟、参数量、张量维度、真实 topic 与模块名）。
  - **零 JavaScript。** 交互一律用纯 CSS 方案（radio / checkbox / details），图表一律内联 SVG —— 所以它在 artifact、邮件客户端、离线存档这些会剥掉 JS 的环境里照样能看。
  - **有主张的风格铁律**，防止它滑向千篇一律的 AI 审美：陶土橙只做点缀绝不做主色，状态色用土色系，边框 1px、几乎不用阴影，靠留白而非线条做分隔。
  - 可选的 `harvest_openspec.py` 能把 OpenSpec 项目里的近期变更收割成 `progress.json`，直接喂给进度看板。
- **设置与前提条件：** HTML 本身零依赖。OpenSpec 收割脚本需要 Python 3 和一个用 OpenSpec 管理的项目。

### 9. 说人话 (`speak-human`)
把满是术语的内容重新讲一遍 —— 一句话结论、一个从头贯穿到尾的生活化类比、一张 ASCII 图、落回你这件事具体要干嘛，外加一张术语对照表。只换说法，不换意思。

- **触发条件：** “说人话”、“讲人话”、“听不懂”、“太专业了”、“用大白话解释”，或用 `/speak-human` 让它重讲上一条回复。也可以直接翻译粘贴进来的报错、技术文档、论文段落。
- **核心功能：**
  - **固定五块输出结构**，确保关键部分不会被省掉 —— 尤其是「具体到你这件事」那一块，没有它，比方就是悬空的，用户看完还是不知道该干嘛。
  - **三档难度**，说「还是不懂」就降档并换一个新类比，说「不用这么啰嗦」就升档。
  - 语言硬规矩：英文缩写不许裸奔、一句话只说一件事且不超过 30 字、数字必须给参照物（`300 毫秒` → “大概眨一次眼”）、禁用书面腔。
  - **准确性优先于简单** —— 前提、限制、风险一个都不能因为「简化」被删掉，类比失真的地方必须自己说明。
  - 八种 ASCII 图模板（流程、分层、前后对比、闭环、时间线、占比、包含、取舍），中文字宽对齐的坑已经处理好。
- **设置与前提条件：** 无。

### 10. Excalidraw 架构图生成 (`obsidian-excalidraw`)
把文本内容生成为 Obsidian 可直接打开的 Excalidraw `.md` 图，重点优化了 AI 模型架构图 —— VLA、Transformer、Diffusion Policy、多系统管线。

- **触发条件：** “画图”、“架构图”、“模型结构”、“流程图”、“思维导图”、“Excalidraw”、“diagram”。
- **核心功能：**
  - **用 `Builder` 类代替手写 JSON** —— 七个 helper（`rect` / `text` / `arrow` / `ellipse` / `subbox` / `parent_box` / `module`）替你处理索引分配、元素双向绑定和序列化。
  - **写入前自动跑 7 项 sanity check**，覆盖 Excalidraw 文件格式里所有已知踩坑点。
  - 面向架构图的约定：每次维度变化都标注张量形状，前向过程从左到右、层级关系从上到下，支持子系统分组（System 1/2、训练/推理、感知/动作）。
  - 附带配色字典和一份 AI 架构图范式参考库。
- **设置与前提条件：** 运行 builder 需要 Python 3。查看和编辑结果需要 Obsidian + Excalidraw 插件。

---

## 如何将技能添加到 Claude Code

有三种方式让 Claude Code “学习”这些技能，挑最方便的即可。

### 选项 A：直接把链接丢给 Claude（最推荐，最省事）
最省事的方式：把本仓库链接粘贴给 Claude Code，剩下的交给它 —— 它会自己读取仓库、找到你需要的技能，并帮你安装或直接运行，无需手动复制、无需折腾路径。
> “这是一个技能仓库：https://github.com/TingdeLiu/Tyndall-Skills —— 帮我安装其中的 cc-plus 状态栏技能。”

### 选项 B：全局注册
将技能文件夹复制到本地 Claude Code 技能目录。这使得该技能在你所有的项目中都可用。
```bash
# Windows (将 'skill-folder-name' 替换为例如 'pdf-compressor')
xcopy /E /I .\skill-folder-name %USERPROFILE%\.claude\skills\skill-folder-name

# macOS/Linux
cp -r ./skill-folder-name ~/.claude/skills/
```

### 选项 C：上下文引用
如果你不想全局安装它们，只需在对话中引用 `SKILL.md` 文件：
> “请根据 @pdf-compressor/SKILL.md 帮我压缩这个文件”

---
*由 [Tingde Liu](https://github.com/TingdeLiu) 创建并维护。*
