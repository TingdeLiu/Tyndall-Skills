---
name: pdf-e2c
description: Translate an English (academic/research) PDF into a clean Chinese-version PDF. Free-flowing single-column reflow (NOT layout-preserving, since Chinese and English occupy very different space), with figures/tables/equations cropped from the original PDF as pixel-perfect images and inserted near their references. Use when the user provides an English paper PDF and asks for a 中文版 / Chinese version / 翻译成中文 / "转为中文版本pdf". Triggers: "把这篇论文转成中文", "translate this paper to Chinese pdf", "英文论文转中文版", "pdf-e2c".
---

# pdf-e2c — English paper PDF → Chinese-version PDF

把英文论文 PDF 转成**自由流式排版**的中文 PDF。中文与英文占用空间差异大，所以
**不保留原双栏版式**，重排为单栏；**图/表/公式从原 PDF 高清裁切为图片**插入（"用原图"），
正文/标题/图注全部翻译为中文，参考文献按惯例保留英文。

Claude 自己做翻译和版面决策；脚本只负责机械的提取、裁切、排版。

## 环境

- Python 3，需装 `pip install pymupdf reportlab pillow`（无需专门 conda 环境）。
  下文一律写 `python`；若系统里有多个解释器，替换成实际路径（如 `C:/Users/<you>/miniconda3/python.exe`）。
- 脚本目录：本 skill 安装位置下的 `scripts/`（全局安装时为 `~/.claude/skills/pdf-e2c/scripts/`）。
- 中文字体：reportlab 内置 CID 字体 `STSong-Light`（宋体，免装字体文件）。
- 工作目录 `<workdir>`：建议在源 PDF 同级建 `<pdf目录>/cn_work/`，存放所有中间产物。

## 工作流（5 步）

### Step 1 — 提取文本块 + 页面预览
```
python scripts/extract_blocks.py "<input.pdf>" "<workdir>" [--dpi 100]
```
产出：`blocks.json`（每页文本块：bbox / font / size / is_math / text）、
`image_rects.json`（内嵌位图的位置矩形＝插图候选）、`preview/p*.png`（整页渲染）。

然后 **Read `blocks.json` 全文** 和若干 `preview/p*.png`，建立全文理解 + 看清版式
（双栏阅读顺序、哪里是图/表/公式/章节标题/参考文献）。

### Step 2 — 规划裁切区域，写 `<workdir>/crops.json`
依据 `image_rects.json`（图）、`blocks.json` 里 `is_math` 的块和表格块（小字号、多列），
为每个**图 / 表 / 公式**确定 `{page(1-based), rect:[x0,y0,x1,y1] pt}`。技巧：
- 图：用 `image_rects.json` 的 rect，上下各留 1–3pt；标题行不要框进去（标题另行翻译）。
- 表：框住表头到表尾（含横线），可参考相邻文本块 bbox 的并集。
- 公式：框住该公式行；行内公式可整行裁，或在译文里用纯文本内联（π_θ→πθ、下标写成 Ot）。
```
python scripts/crop_regions.py "<input.pdf>" "<workdir>"
```
产出 `assets/<name>.png`。**Read 抽查几张**（尤其表格/公式）确认无截断；不对就改 rect 重跑。

### Step 3 — 翻译全文（Claude 亲自做）
逐块把英文 prose / 标题 / 图表标题 / 摘要 / 关键词翻成**流畅的技术中文**：
- 术语统一、忠实；专有名词与模型名（CARLA、Qwen2.5-VL、LoRA、SLAM…）保留英文。
- 行内数学符号用纯文本内联（避免 ∈ ⊂ ∏ 等字体缺字符号，可改写为"属于/约/大于等于"等）。
- 把被分栏/分页**截断的同一段落合并**成一个连续段落。
- 参考文献**保留英文原文**（学术惯例）。

### Step 4 — 组装 `<workdir>/document.json`（有序内容流）
按论文阅读顺序排出 elements 列表，文字已是中文，图/表/公式用 `src`（=assets 文件名，免 .png）。
**图/表/公式就近放在其首次被引用处附近。** 元素类型见
`scripts/build_cn_pdf.py` 顶部 schema：
`title / author / affil / abstract / h1 / h2 / body(indent默认true) / bullet /
image(src,caption,max_ratio) / equation(src,max_ratio) / reference / refs_block / spacer`。
- `h1`＝章节（I. 引言 / II. 相关工作…），`h2`＝子节（A. … / B. …）。
- 整段图注放进 image 的 `caption`；参考文献用一个 `refs_block`（按 `[n]` 自动拆条）。
- `max_ratio`：整幅图≈1.0，窄表≈0.8–0.95，公式≈0.7–0.85。

### Step 5 — 构建 + 校验
```
python scripts/build_cn_pdf.py "<workdir>" --out "<同目录>/<原名>_中文版.pdf"
```
然后用 PyMuPDF 把成品逐页渲染成 png 并 **Read 抽查每页**：字体是否缺字（豆腐块）、
图表公式是否正确、排版是否美观。有问题就改 `document.json` / `crops.json` 重跑对应步骤。

```python
import fitz, os
d = fitz.open(out_pdf)
for i in range(d.page_count):
    d[i].get_pixmap(dpi=100).save(os.path.join(workdir, "preview_cn", f"v{i+1}.png"))
```

## 校验清单
- [ ] 无缺字/豆腐块（中文标点、破折号 —— 正常）。
- [ ] 每张图/表/公式都来自原图、清晰无截断、位置靠近引用处。
- [ ] 段落连贯（分栏截断已合并），术语统一，模型/数据集名保留英文。
- [ ] 章节层级正确，图注/参考文献格式整齐。
- [ ] 成品命名 `<原名>_中文版.pdf`，放在源 PDF 同目录。

## 备注
- 这是"阅读用"中文重排版本，不追求与原版逐像素对齐；用户已确认接受自由排版。
- 想换风格：字体（`--font`，需 reportlab 支持的 CID 名）、纸张（document.json `page:"letter"`）、
  字号/间距在 `build_cn_pdf.py` 的 `S` 样式表里改。
- 若 PDF >32MB 或读取失败，先用 `pdf-compressor` 压缩再处理。
- 仅处理用户提供的文档；翻译/摘录其自有文档无版权问题。
```
