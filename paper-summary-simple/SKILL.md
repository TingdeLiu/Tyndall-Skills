---
name: paper-summary-simple
description: 通过论文标题或链接快速生成中文摘要。当用户提供论文标题或链接（arXiv、OpenReview、会议论文等）并要求总结时自动触发。自动搜索并总结论文内容，以结构化 Markdown 格式保存到输出目录。适合快速了解论文核心思想。触发词示例："总结这篇论文"、"summarize this paper"、提供论文链接或标题。
---

# Paper Summary Simple

只要一个论文标题或一条链接，就产出一份结构化的中文摘要。不下载 PDF，不抽图，全靠网页信息。

想要深度分析和自动抽图，用 `pdf-figure-extractor` 把图切出来，再手动补进这份摘要里。

## 核心功能

- **输入极简**：论文标题或链接，二选一
- **自动获取**：链接走 WebFetch，标题走 WebSearch
- **中文总结**：中文撰写，技术术语保留英文原文
- **精华提炼**：开头就讲清这篇论文哪里值得借鉴
- **自动保存**：写成 Markdown 落盘

## 输出位置

默认写到当前工作目录下的 `paper-summaries/`，目录不存在就创建：

```
./paper-summaries/paper-summary-[paper-name].md
```

用户指定了别的目录就用用户的。想固定一个收口目录（例如博客仓库的草稿区），在调用时直接说明路径即可，例如：

```
总结这篇论文，存到 D:/blog/_drafts/
```

文件命名格式 `paper-summary-[paper-name].md`，如 `paper-summary-CLIP.md`、`paper-summary-Uni-NaVid.md`。

## 输出格式

### 标题格式

```markdown
## [Short Model/Method Name (year)]
———[Subtitle/Slogan]

📄 **Paper**: [arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX) · 🏛️ **VENUE YEAR**
```

**标题命名规范（硬性要求）：**

- **二级标题 `##` 必须用简短的模型/方法名**（如 `AgenticNav (2026)`、`TuckerNav (2026)`、`Harness VLA (2026)`）。
- ❌ **严禁把论文全名塞进 `##` 标题**（不要写 `## AgenticNav: Zero-Shot Vision-and-Language Navigation as a Tool-Calling Harness (2026)`），也不要在标题里写会议名（不要写 `## ... (ICLR 2026)`）。
- 年份只留四位数字（`(2026)`），会议/期刊名写在下面那行 `📄 **Paper**` 的 `🏛️ **VENUE YEAR**` 里。

**Paper 行格式规范：**

- **基本结构**：`📄 **Paper**: [链接文字](url)`，多个条目之间用 ` · ` 分隔。
- **所属期刊/会议**：末尾追加 ` · 🏛️ **VENUE YEAR**`，VENUE 照搬论文正式发表处。
  - 录用示例：`🏛️ **ICRA 2024**`、`🏛️ **AAAI 2026**`、`🏛️ **CVPR 2026**`、`🏛️ **ICLR 2026**`、`🏛️ **IEEE TPAMI 2025**`、`🏛️ **ECCV 2024**`、`🏛️ **ACL 2025**`、`🏛️ **IEEE RA-L**`
  - 带状态/出版社时照写：`🏛️ **AAAI 2026 (Poster)**`、`🏛️ **Vicinagearth (Springer) 2025**`
- **预印本（preprint）不加 `· 🏛️` 段**：只写 arXiv 链接，如 `📄 **Paper**: [arXiv:2512.08186](https://arxiv.org/abs/2512.08186)`。
- **venue 判定**：从抓到的网页/PDF 信息确定发表处；**没有明确信息就按预印本处理，不要臆测 venue**。
- **可选条目**：有代码/主页的话，在 venue 前用 ` · ` 追加，如 `· [Code](url)`、`· [Project Page](url)`。

> 不写作者信息行，不加生成时间/工具页脚。

### 内容结构

用 `### 标题` 和 `---` 分隔线，按顺序五个部分：

- `### 精华`（简短，最多 5 句）
  - 这个工作哪些点值得被借鉴
  - 提炼核心亮点和可迁移的思想
  - 聚焦方法论层面的启发

- `### 1. 研究背景/问题`（简短，2-3 句）
  - 论文解决的核心问题
  - 研究动机和背景

- `### 2. 主要方法/创新点`（核心内容，最详细）
  - 主要技术方法
  - 关键创新和贡献
  - 必要时带架构细节

- `### 3. 核心结果/发现`（关键发现）
  - 主要实验结果
  - 性能指标和对比
  - 重要观察结论

- `### 4. 局限性`（简短，1-2 句）
  - 局限性或未来工作，保持简洁

## 使用指南

### 语言和风格

- **输出语言**：中文撰写，但专有名词、技术术语、模型名称保留英文原文（VLM、VLN、Transformer、RL 等）
- **精华部分**：开头就提炼最值得借鉴的核心思想，最多 5 句
- **技术术语**：用清晰的技术语言，假设读者有领域知识
- **准确引用**：精确提取模型名称、算法、评估指标

### 重点分配

- **主要方法/创新点**：最重要，要详细写
- **精华部分**：提炼核心价值，帮读者快速抓要点
- **其他部分**：背景和局限性保持简洁

### 图片占位

在 `### 2. 主要方法/创新点` 的合适位置插入图片占位（用户自行替换图片路径）：

```markdown
<div align="center">
  <img src="/images/[topic]/[paper-name]-[descriptive-name].png" width="100%" />
  <figcaption>[简短中文描述]</figcaption>
</div>
```

**硬性规则 —— 否则图片无法正常显示：**

1. **`<div>` 内不能有空行**：`<div align="center">` 与 `<img>` 之间、`/>` 与 `<figcaption>` 之间、`</figcaption>` 与 `</div>` 之间都不能有空行。kramdown 遇到块内空行会切回 markdown 解析模式，把 `<img>` 当文本输出而不是渲染成图片。
2. **所有 HTML 属性必须用 ASCII 直引号 `"`（U+0022）**，禁止 Unicode 弯引号。

补充约定：

- 图片命名：`{PaperName}-{Description}.png`（如 `StreamVLN-architecture.png`、`DGNav-results.png`）
- **图片路径**：`[topic]` 对应你自己的 `images/` 子目录名，按论文主题选（例如 `vln`、`vla`、`vlm`、`agent`、`robotics_navigation`）。不往博客发就随便填，反正路径要手动替换。
- **自适应插入**：看论文内容判断关键图数量，在 `### 2.` 的合适位置插 1-3 张占位（架构图、流程图、结果对比图）
- 不加 `<!-- RENAME: ... -->` 注释（这个 skill 不做自动重命名）

## 工作流程

**步骤 1: 获取论文信息**

- 给的是链接（arXiv / OpenReview / 会议网站）：
  - 用 WebFetch 直接抓页面
  - 提取标题、作者、摘要
- 给的是标题：
  - 用 WebSearch 搜
  - 找到官方链接（优先 arXiv）
  - 抓详细信息

**步骤 2: 分析论文内容**

- 读摘要和关键部分
- 识别核心问题、方法、创新点
- 提取主要实验结果和结论

**步骤 3: 生成结构化摘要**

- 按五个部分的格式写中文摘要
- 从**精华**开始，提炼核心价值
- **主要方法/创新点**详细写技术细节
- 技术术语保留英文原文

**步骤 4: 保存**

- 文件名 `paper-summary-[paper-name].md`
- 写到输出目录（默认 `./paper-summaries/`，不存在就建）

**步骤 5: 确认完成**

- 显示保存的文件路径
- 给一段简短预览

## 使用示例

**给 arXiv 链接：**

```
用户: https://arxiv.org/abs/2301.12345

Claude:
1. 抓论文信息（标题、作者、摘要）
2. 分析内容
3. 生成五部分结构化摘要
4. 保存到 ./paper-summaries/paper-summary-MethodName.md
5. 显示完成信息
```

**给论文标题：**

```
用户: Vision-Language Navigation with Transformers

Claude:
1. 搜索论文找到官方链接
2. 抓详细信息
3. 分析并生成摘要
4. 保存
5. 显示完成信息
```

## 输出样例

```markdown
---
## Uni-NaVid (2024)
———Unified Vision-Language Navigation

📄 **Paper**: [arXiv:2301.xxxxx](https://arxiv.org/abs/2301.xxxxx) · 🏛️ **CVPR 2024**

### 精华

这篇论文展示了如何通过统一框架实现跨任务泛化，值得借鉴的点包括：利用大规模预训练模型的知识迁移能力、设计跨模态融合机制以整合视觉和语言信息、采用多任务训练策略提升模型鲁棒性。

---

### 1. 研究背景/问题

当前的视觉-语言导航系统难以在不同环境和任务变体中泛化。现有方法通常需要特定任务的训练，并且无法有效利用大规模预训练模型中编码的知识。

---

### 2. 主要方法/创新点

论文提出了 Uni-NaVid，一个统一的视觉-语言导航框架……

<div align="center">
  <img src="/images/vln/Uni-NaVid-architecture.png" width="100%" />
  <figcaption>Uni-NaVid 整体架构</figcaption>
</div>

主要创新包括：
- 新颖的跨模态融合机制
- 层级化动作规划模块
- 多任务训练策略

<div align="center">
  <img src="/images/vln/Uni-NaVid-results.png" width="100%" />
  <figcaption>不同基准测试的性能对比</figcaption>
</div>

---

### 3. 核心结果/发现

- 在 R2R 基准测试上达到了最先进的性能（SPL: 65.3%）
- 展示了强大的零样本迁移能力
- 平均比基线方法提升 12%

---

### 4. 局限性

该方法在训练过程中需要大量计算资源，并且在混乱环境中处理复杂空间推理时存在困难。
```

## 注意事项

1. **网络访问**：需要能访问论文网站（arXiv、OpenReview、会议网站）
2. **术语保留**：技术术语、模型名称、数据集名称保留英文原文
3. **文件命名**：自动从论文标题提取关键词作为文件名
4. **目录管理**：自动创建输出目录，避免文件名冲突

### Jekyll / MathJax 公式安全

**只有摘要要发到 Jekyll 博客时才需要管这一节。** kramdown 会在 MathJax 之前先解析 Markdown，所以公式里的某些字符会被吃掉：

- 绝对值不要用 `|...|`：`$|s_t| > \tau$` → `$\lvert s_t \rvert > \tau$`（`|` 会被当表格分隔符）
- 范数同理：用 `\lVert...\rVert` 代替 `\|...\|`
- `}` 后紧跟 `_` 会被当成斜体起始：
  - `$\pi^{\rightarrow}_{\theta_k}$` → `$\pi_{\theta_k}^{\rightarrow}$`（下标写在上标前）
  - `\mathcal{X}_{sub}` → `\mathcal X_{sub}`（单字符参数省大括号；`\mathbf` / `\mathbb` / `\mathrm` 同理）
- 行内公式含 `\mathbf{...}_`、`\bar{...}_`、`\hat{...}_` 等 `}_` 组合时，改用 `$$...$$`

## 这个 skill 不做什么

| | 这个 skill | 需要时换用 |
|---|---|---|
| 输入 | 标题或链接 | 有 PDF 在手就直接读 PDF |
| 图片 | 只插占位，不抽图 | `pdf-figure-extractor` 把图切出来 |
| 依赖 | 只要能联网 | 抽图需要 conda 环境 |
| 适用 | 快速掌握核心思想 | 需要逐图精读时另想办法 |
