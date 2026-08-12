---
name: obsidian-excalidraw
description: Generate Excalidraw diagrams from text content for Obsidian, with first-class support for AI model architecture diagrams (VLA, Transformer, Diffusion Policy, multi-system pipelines). Use when user asks to draw, visualize, or diagram concepts. Triggers on "Excalidraw", "画图", "流程图", "思维导图", "架构图", "模型结构", "可视化", "diagram", "architecture".
metadata:
  version: 2.0.0
---

# Excalidraw Diagram Generator

Create Excalidraw diagrams in Obsidian-ready `.md` files. Optimized for AI/ML model architecture diagrams (encoders, fusion modules, policy heads, controllers, multi-system pipelines), but supports general flowcharts, mind maps, and concept diagrams.

> 🛠️ **核心工具：[`references/builder_template.py`](references/builder_template.py)** — 提供 `Builder` 类（封装 rect/text/arrow/ellipse/subbox/parent_box/module 7 个 helper），自动处理索引分配、双向绑定、JSON 序列化，并在 `.write()` 前跑 7 项 sanity check（覆盖 §7 所有已知踩坑）。**画图首选用它，不要手写 JSON**。配色直接用 `PALETTE` 字典。

## Workflow

1. **Identify diagram class** — AI architecture vs. general (flowchart / mind map / hierarchy / etc.). Architecture diagrams use the AI Specialization rules in §3.
2. **Plan structure before code**:
   - Modules and their type (encoder / fusion / policy / controller / output / annotation)
   - Data flow direction (left→right for forward pass, top→bottom for hierarchy)
   - Tensor shapes at every dimension change
   - Subsystems to group (System 1/2, train/inference, perception/action)
   - **Per-module decision**: simple module (`Builder.module()`) vs. parent + sub-boxes (`Builder.parent_box()` + `.subbox()`) — see §3.3 升级触发条件
3. **Generate via Python builder** — use `references/builder_template.py`:
   ```python
   from builder_template import Builder, PALETTE
   b = Builder()
   px, fx, sx, sf, _ = PALETTE["llm"]
   b.parent_box("dit", "dit_t", 920, 220, 360, 140, px, fx, "Wan 2.1-14B DiT")
   b.subbox("sub_a", "txt_a", 930, 252, 165, 50, sx, sf, "VAE 8x8/4x4")
   # ... arrows, more modules
   b.write("MyDiagram.architecture.md")  # validates before write
   ```
   `Builder.write()` runs all 7 sanity checks (index, dup id, container binding, arrow binding, overflow, curly braces, dangling refs) and aborts on any issue. **Never** write JSON by hand.
4. **Save** as `[主题].[类型].md` in cwd (e.g. `InternVLA-N1.architecture.md`). Builder writes Obsidian-wrapped markdown directly.
5. **Confirm to user** — file path, diagram type, 1-line rationale. If user reports rendering issues, see §7 Error Prevention.

**手写 JSON 仅当**：调试现有图、用户给了已有 JSON 要修。其他场合一律用 builder。

---

## 1. Diagram Types

| 类型 | 英文 | 使用场景 |
|------|------|---------|
| **AI 架构图** | AI Architecture | 模型结构、双系统、VLA/VLM/RL 管线 — 见 §3 |
| **流程图** | Flowchart | 步骤、工作流、任务执行顺序 |
| **思维导图** | Mind Map | 概念发散、主题分类 |
| **层级图** | Hierarchy | 组织结构、系统拆解 |
| **关系图** | Relationship | 要素间影响、依赖、互动 |
| **对比图** | Comparison | 方案/观点对照 |
| **时间线** | Timeline | 事件发展、模型演化 |
| **矩阵图** | Matrix | 双维度分类、优先级、定位 |
| **场景剧本** | Scenario Script | 用户旅程、角色交互、情境步骤 |

---

## 2. Output Format (Obsidian Wrapper)

**严格按以下结构输出：**

```markdown
---
excalidraw-plugin: parsed
tags: [excalidraw]
---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'

# Excalidraw Data

## Text Elements
{文本1} ^id1

{文本2} ^id2

...

%%
## Drawing
\`\`\`json
{完整 Excalidraw JSON}
\`\`\`
%%
```

**Text Elements 部分必须列出每个文本元素**，格式：
- 文本内容 + 空格 + `^uniqueId`（block reference）
- `^id` 必须与 JSON 中对应 text element 的 `id` 字段完全一致
- 多行文本直接换行写，最后一行末尾贴 `^id`
- 元素之间用空行分隔
- 这是 Obsidian Excalidraw 插件的双向同步源 — markdown 视图编辑文本会同步到 JSON，反之亦然
- 留空也能渲染（插件会从 JSON 反填），但**列出来更稳**，且符合用户现有文件惯例

**其他规则：**
- 顶层 frontmatter 仅 `excalidraw-plugin: parsed` + `tags: [excalidraw]`
- `## Drawing` 下的 JSON 必须用 `%%` 包围（隐藏 markdown 渲染）
- code fence **只用 `json`，绝不用 `compressed-json`**。`compressed-json` 是插件运行时格式，手写 base64 必坏
- **JSON 必须单行紧凑** — 顶层 `{...}` 一行开头一行结尾，每个 element 单独占一行。**禁止**对 element 对象进行多行缩进（pretty-print）。原因：Obsidian 插件首次打开会触发 auto-compress 把 JSON 压成 base64，多行 + 中文 + 长字符串容易在压缩输出中插入意外换行，导致 base64 损坏 → 整图无法渲染。

✅ 推荐写法（每 element 一行）：
```json
{"type":"excalidraw","version":2,"source":"...","elements":[
{"id":"box1","type":"rectangle",...全部字段在同一行...},
{"id":"text1","type":"text",...全部字段在同一行...},
{"id":"arr1","type":"arrow",...全部字段在同一行...}
],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"},"files":{}}
```

❌ 禁止写法（element 跨多行）：
```json
{
  "id": "box1",
  "type": "rectangle",
  "x": 100,
  ...
}
```

### 2.1 Raw JSON Mode（罕用）

仅当用户**明确**要求 "纯 JSON"、"excalidraw.com"、"raw"、"裸 JSON"、`.excalidraw` 文件时使用。
跳过 Obsidian 包裹，直接输出（不带 markdown code fence）：

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [...],
  "appState": {"gridSize": null, "viewBackgroundColor": "#ffffff"},
  "files": {}
}
```

默认仍然走 Obsidian 模式（§2 主格式）。设计规则、配色、AI 架构特化（§3-§5）两种模式均适用。

---

## 3. AI Model Architecture Specialization

**核心原则**（来自 NN-diagram 最佳实践）：
- **张量形状必须标注** — 每个维度变化点都写形状，否则读者要猜
- **颜色按模块类型分配** — 功能性，不是审美。同类模块同色
- **视觉对应架构** — Transformer 堆叠用 `×N`、残差用 bypass 箭头、Diffusion 画噪声→去噪管线
- **真实命名** — 写 `Qwen-VL-2.5 7B` 而不是 `LLM`，写 `DepthAnythingV2` 而不是 `Depth Encoder`

### 3.1 模块色彩语义表

每类模块固定色对，便于跨图一致：

| 模块类型 | 父描边 | 父填充 | 子描边 | 子填充 | 用途示例 |
|----------|-------|-------|-------|-------|---------|
| **输入/传感器** | `#0891b2` | `#cffafe` | `#0e7490` | `#ecfeff` | RGB-D, IMU, 文本指令 |
| **Vision Encoder** | `#1e40af` | `#dbeafe` | `#2563eb` | `#eff6ff` | DINOv2, SigLIP, ViT |
| **Language / LLM** | `#6d28d9` | `#ede9fe` | `#7c3aed` | `#f5f3ff` | Qwen-VL, Llama, T5 |
| **Fusion / Attention** | `#be185d` | `#fce7f3` | `#db2777` | `#fdf2f8` | Cross-Attn, Q-Former |
| **Policy / Decoder** | `#047857` | `#d1fae5` | `#059669` | `#ecfdf5` | Diffusion, Transformer Dec |
| **Action / Output** | `#c2410c` | `#fed7aa` | `#ea580c` | `#ffedd5` | 7-DOF, 轨迹, 抓取 |
| **Controller / 系统** | `#475569` | `#f1f5f9` | `#64748b` | `#f8fafc` | MPC, PID, SLAM |
| **标注 / 元信息** | `#b45309`虚线 | `#fef3c7` | `#d97706` | `#fffbeb` | 张量形状、耗时、参数量 |
| **强调 / 创新点** | `#dc2626` | `#fee2e2` | `#ef4444` | `#fef2f2` | 关键创新、问题点 |

**配对规则**：父框深描边 + 浅填充；子框是父的"调浅一档"（stroke 浅 ~10%，fill 几乎纯白带一丝色调）。文字色统一 `#1f2937`（暗灰）。
**这套配色已固化在 `references/builder_template.py` 的 `PALETTE` 字典里**，画图直接 `from builder_template import PALETTE`。

### 3.2 标准流水线布局（VLA/VLM 模型）

横向 6 段式 — 自左向右，每段 **200–240px 宽**（早期 180 太窄，文字易溢出），模块间距 **20–30px**（窄间距给箭头）：

```
┌─输入层─┐ ┌─编码层─┐ ┌─融合层─┐ ┌─规划层─┐ ┌─执行层─┐ ┌─控制层─┐
│ RGB-D  │→│  ViT   │→│ Q-Form │→│  LLM   │→│ Policy │→│  MPC   │
│ Text   │ │ LLM enc│ │   +    │ │  CoT   │ │  Diff  │ │  PID   │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
   180       200        200        220       240(hero)   180
```

含子框的 hero 模块（如 LLM/DiT）通常用 **300–360px 宽** 来容纳 2×2 子网格。
垂直方向（`y` 轴）用于多模态并列输入或 System1/System2 分层。

### 3.3 模块盒规范

每个模块 = 矩形容器 + **container-binding 居中文本**（`Builder.module()` 一行搞定）。文本格式：

```
[模块名]
=====
- 模型/算法名
- 维度/参数量
- 关键属性
```

- 标题用 `[名称]`（不再用 `━━━━━━` 分隔线 — 容易在压缩 JSON 时破坏；用 `=====` 5–10 个等号代替更稳）
- bullet 用 `-`（container-binding 文本不会被 markdown 解析，连字符没问题）
- **必须用 container binding**（rect 的 `boundElements` ↔ text 的 `containerId`）— Excalidraw 自动垂直+水平居中。自由文本垂直居中常顶部对齐
- **盒尺寸看内容定**（由 §3.3「文字宽度估算」反推）：
  - 3–4 行短内容（fs=13）：`width ≥ 180, height 120`
  - 5 行内容（fs=13）：`width ≥ 200, height 140`
  - ≥6 行：直接升级子框（见下文「内容多怎么办」）
- `roundness: {type: 3}`（圆角矩形）

参考已有图：`OpenVLA.md` 的 Vision Encoder 盒、`NavDP架构.md` 的 RGB编码器盒。

#### 文字宽度估算（避免溢出）

Excalifont（`fontFamily: 5`）平均字宽 ≈ `fontSize × 0.6` 像素。每行能放多少字符：

```
max_chars_per_line ≈ (box_width − 20) / (fontSize × 0.6)
```

| 盒宽 | fs=11 | fs=12 | fs=13 | fs=14 |
|------|-------|-------|-------|-------|
| 140  | 18    | 17    | 15    | 14    |
| 180  | 24    | 22    | 21    | 19    |
| 200  | 27    | 25    | 23    | 21    |
| 240  | 33    | 30    | 28    | 26    |

**自检脚本**（生成前必跑）：

```python
for e in elements:
    if e['type']=='text' and not e.get('autoResize', False):
        max_chars = (e['width'] - 12) / (e['fontSize'] * 0.6)
        longest = max(len(line) for line in e['text'].split('\n'))
        if longest > max_chars + 1:
            print(f"OVERFLOW {e['id']}: {longest} > {max_chars:.0f}")
```

#### 内容多怎么办：**优先用子框，而不是塞文字**

> 📌 **核心规则**：当某个模块文字超过 5–6 行 / 单行超过容纳上限，**不要**通过缩小字号或硬塞来解决。把它升级成「父容器 + 标题 + 多个子框」的结构，每个子框承担一类信息。这同时解决溢出问题 *和* 可视化模块内部组成。

**升级触发条件**（满足任一即升级）：
- 文字 ≥ 6 行
- 任何一行字符数 > §文字宽度估算上限
- 内容天然可拆成 2+ 个独立小组件（如 VAE + Flow Matching + FramePack + Plücker rays）
- 模块是 hero（核心组件），需要视觉权重

**子框模式构造**（含数据流箭头 — 子框间有依赖必须画）：

```
┌─Wan 2.1-14B DiT────────────────────────────┐  ← 父框（粗描边、深色 stroke）
│                                            │
│  [VAE 8x8/4x4]  ─→  [Flow Match 35/DMD 4]  │  ← 主流：实线箭头
│        ↑                   ↑                │
│        │ (dashed)          │ (dashed)       │  ← 条件注入：虚线箭头
│  [FramePack hist]   [Plücker rays inj.]    │
│                                            │
└────────────────────────────────────────────┘
```

子框生成用 `Builder.subbox(rect_id, txt_id, x, y, w, h, stroke, fill, text)`：自动绑定 + 居中 + 索引分配。

**字段规范**：

| 元素 | 规则 |
|------|------|
| 父框 | `strokeWidth: 3`，深色 stroke (`#6d28d9`)，浅色 fill (`#ede9fe`) |
| 标题 | 父框顶部 `y=parent.y+4`，`fontSize: 14`，`textAlign: center`，颜色与父框 stroke 一致 |
| 子框 | `strokeWidth: 1`，更浅的 stroke (`#7c3aed`)，更浅的 fill (`#f5f3ff`)，`roundness: {type:3}`，**必须**绑定 text（见下） |
| 子框文字 | `fontSize: 10–11`，1–3 行，**用 containerId 绑定到子框**（见下） |
| 间距 | 父框 padding 5–10px；子框间 gap 5–14px（够画内部箭头） |

**子框文字必须用 containerId 绑定**（不能用自由文本）

子框里的多行文字如果用自由文本（`containerId: null`），即便设了 `verticalAlign: "middle"` 也常常顶部对齐 — Excalidraw 对自由 text 的垂直居中支持不稳。**正确做法是 container binding**，让 Excalidraw 自动水平+垂直居中。

```python
# rect: 必须有 boundElements 反向引用 + customData
rect = {
    "id": "sub_a",
    ...,
    "boundElements": [{"type": "text", "id": "txt_sub_a"}],  # 必须
    "customData": {"legacyTextWrap": True}                   # 必须，让多行文字按 box 宽度 wrap
}

# text: 必须有 containerId 指向 rect
text = {
    "id": "txt_sub_a",
    ...,
    "containerId": "sub_a",      # 必须
    "textAlign": "center",
    "verticalAlign": "middle",
    "x": <rect.x>, "y": <rect.y>, "width": <rect.w>, "height": <rect.h>  # 与 rect 同尺寸（Excalidraw 会忽略并自动布局）
}
```

**双向引用必须一致**（§5 反复警告过）：rect 的 `boundElements` 里有 text 的 id，text 的 `containerId` 指 rect 的 id。任何一方写错整张图可能拒绝渲染。

**helper 函数模板**：

```python
def subbox(rect_id, txt_id, x, y, w, h, stroke, fill, text_content, idx_rect, idx_text, fs=11):
    add(rect(rect_id, x, y, w, h, stroke, fill, idx_rect, sw=1,
             bound=txt_id))  # 自动加 boundElements + customData
    add(text(txt_id, x, y, w, h, text_content, idx_text, fs,
             container=rect_id))  # 自动加 containerId
```

哪些场景用 container binding：
- ✅ 子框（必用）
- ✅ 简单单盒模块（Input / Output 等只有 4–5 行，希望整体居中）
- ✅ Recon 模块（DAv3 / Mesh Ext 等）
- ❌ 父框（父框只放标题在顶部 + 子框在下方，不能整体居中）
- ❌ 自由标签（侧栏、张量形状、loop 标注）— 这些就是要靠位置控制布局

**典型尺寸**：
- 2 平行子框：父 `220 × 140`，子 `95 × 100`，间隔 10px
- 2 串行子框（带箭头）：父 `220 × 140`，子 `90 × 100`，箭头 20px
- 3 串行子框：父 `240 × 140`，子 `64 × 100`，箭头 14px
- 2×2 网格：父 `360 × 140`，子 `165 × 50`，箭头穿插其间

#### 子框间数据流箭头（**必加**）

子框不是装饰 — 是模块内部的数据流分解。**只要子框之间有先后顺序或依赖关系，就必须加内部箭头**，否则读者无法判断流向。

**箭头规范**（与外部主流箭头区分）：
- `strokeWidth: 1`（外部主流是 2）
- 颜色与父框 stroke 一致（不是默认灰）— 视觉绑定到所属模块
- 实线表 forward flow，虚线表 conditioning / 注入
- 字号若加标签则 `fontSize: 10`

**常见内部拓扑**：

| 拓扑 | 何时用 | 箭头 |
|------|--------|------|
| **平行存储** | 多份独立数据共存（如 `Depth ‖ PointCloud`） | 无内部箭头 |
| **串行 A→B** | 两阶段处理（如 `Score → Select`） | 1 条横向实线 |
| **串行 A→B→C** | 三阶段（如 `FwdWarp → Build → Inject`） | 2 条横向实线 |
| **2×2 主流+条件** | 主流水平 + 下方分支垂直注入（如 DiT：`VAE→FlowMatch`，下方 `FramePack`/`Plücker` 虚线 ↑） | 1 条主线 + 2 条虚线注入 |
| **fan-in / fan-out** | 多源融合或多头分发 | 多条实线汇聚到目标点 |

**实例**（Lyra 2.0 DiT，2×2 + 主流 + 条件注入）：

```
┌─Wan 2.1-14B DiT────────────────────────────┐
│  [VAE 8x8/4x4]  →  [Flow Match 35/DMD 4]   │  ← 实线主流
│         ↑                  ↑                │
│  [FramePack hist]    [Plücker rays]        │  ← 虚线条件注入
└────────────────────────────────────────────┘
```

#### 该升级哪些模块？（不要只升级一个）

**经验法则**：当一张图里有 **任意** 模块满足升级条件，**所有同等复杂度的模块都该升**，否则视觉权重失衡。

| 模块复杂度 | 处理 |
|-----------|------|
| 1–3 行简单内容 | 单盒 + 文字（`Builder.module()`） |
| 4–5 行 | 单盒 + 文字（确保宽度足够；`Builder.module()`） |
| ≥6 行 / 含 ≥2 个独立子组件 | **必须**子框（`Builder.parent_box()` + `.subbox()`） |
| Hero 模块（核心组件）| **优先**子框，即使内容只有 4–5 行（强化视觉权重） |

**何时不该用子框**（避免过度设计）：
- ❌ Input/Output 这类只是 I/O 描述的端点 — 子框反而显得 over-engineered
- ❌ 内容是同质的列表（如"成功率 / 速度 / 数据规模"三个指标）— 子框暗示"流程关系"，但这里只是并列条目，用单盒 bullet 列即可
- ❌ 一张图整体复杂度低（≤5 个模块、各自 3–4 行）— 全用单盒更清爽
- ❌ Side panel（创新点 / 指标 / 推理流程）— 这些是叙述性内容，不是模块结构

**典型分布**（VLA/VLM 论文）：
- 简单单盒：Input / Output / 标注框 / 侧栏
- 子框升级：Vision Encoder / LLM / Diffusion DiT / Policy Head / Memory Cache / Retrieval / Fusion 等核心模块

**常见拆分模式**：
- **VLM/VLA backbone**（2×2 网格 + 主流横线）：[Vision Encoder] → [Cross-Attn] / [Text Encoder] ↑ [Decoder] ↑
- **Diffusion DiT**（2×2 + 条件注入）：[VAE enc] → [Flow Match] / [FramePack] ↑ [Plücker] ↑
- **3D Cache**（2 平行）：[Depth Map] ‖ [Point Cloud]
- **Geo Retrieval**（2 串行）：[Score φ(i)] → [Greedy select]
- **Canonical Warp**（3 串行）：[FwdWarp] → [Build map] → [Inject Q,K]
- **Policy Head**（2×2）：[Action Decoder] ‖ [Value Head] / [Loss] [Optim]

**禁止**：
- ❌ 把已经溢出的文字硬挤进原盒，靠减字号到 10 以下
- ❌ 用 `containerId` 让 Excalidraw 自动 wrap（虽然能 work，但 wrap 出来的中文/英文混排很丑）
- ❌ 子框层数 > 2（再深就成思维导图了，画不下）
- ❌ 一张图里只升级一个 hero 模块、其他同等复杂度的模块塞文字 → 视觉失衡
- ❌ 子框之间有数据依赖却不画内部箭头 → 读者必须靠位置和先验猜流向

### 3.4 张量形状与元数据标注

**形状标注**（free-floating，不带容器）：
- 格式：`(B, seq_len, dim)` 或 `[N, 256]` 或 `B × N × 256`
- 字号 14–16，颜色 `#b45309`（金棕色），`fontFamily: 5`
- 位置：贴在产生该张量的箭头中段或目标模块上方
- **示例**：`(B, 128, 512)`、`[M, 3]` 轨迹、`N×256 tokens`
- **禁止用花括号上下标** `R^{H×W×3}`、`x_{ij}` — Obsidian markdown 解析与 `^block-ref` 语法冲突，且某些字符组合会让插件压缩 JSON 后无法解码。改用平铺写法 `R³`、`(B, H, W, 3)`、`x_ij`。

**频率/延迟标注**：
- `「30 Hz」`、`耗时: ~30ms`、`Latency: 0.7s`
- 与速率相关的箭头/模块旁，用虚线小框包裹（`strokeStyle: dashed`，`backgroundColor: #fef3c7`）

**参数量标注**：模块名后小字，例 `Qwen-VL-2.5「7B」`、`U-Net「12M」`

### 3.5 子系统分组（System 1/2 风格）

将多模块用大半透明矩形框住：
- `width` 跨多个子模块，`height` 包含所有内容 + 上下 50px padding
- `backgroundColor: #f8fafc`（极浅灰）或 `transparent`
- `strokeStyle: dashed`，`strokeWidth: 2`，`roughness: 0`
- `opacity: 60`（不抢戏）
- **z 轴**：分组框用最早的索引（如 `a1`），子模块用之后的（`a2, a3, ...`）。**禁止用末字符为 `0` 的索引**（见 §7.4）
- 顶部贴标题文本：`System 2: 高层规划「Slow, 2 Hz」`

参考：`InternVLA-N1.md` 的 DualVLN 双系统框。

### 3.6 重复块与跳连

- **堆叠重复**（Transformer Encoder × N）：单个块 + 右下贴 `×N` 标签
- **残差/Skip Connection**：bypass 弧形箭头，`strokeStyle: dashed`，标 `+` 或 `residual`
- **共享权重**：两个块之间画双向虚线 + `Shared` 标签
- **数据并行/模态并行**：分叉箭头从同一锚点出发到多个目标

### 3.7 流向箭头规范

| 关系 | 箭头样式 | 颜色 | 线宽 |
|------|---------|------|------|
| **外部主前向流** | 实线 | `#374151` | `2` |
| **外部反馈/loss** | 虚线 | `#6b7280` | `2` |
| **外部残差/skip** | 弧线虚线 | `#9ca3af` | `2` |
| **外部控制信号** | 实线（双箭头可选） | `#475569` | `2` |
| **外部文本/语义流** | 实线 | `#6d28d9` | `2` |
| **子框内主流**（§3.3） | 实线 | 父框 stroke | `1`（区别于外部） |
| **子框内条件注入**（§3.3） | 虚线 | 父框 stroke | `1` |
| **autoregressive loop** | 长虚线 | `#6b7280` | `2` |

箭头中段贴张量形状或操作名（`+`、`⊙`、`concat`、`cross-attn`）。颜色绑定原则：箭头颜色应"跟随"它属于的子系统 — 子框内部箭头跟父框走，跨模块主流用中性灰。

### 3.8 侧栏元信息

右侧或下方留 200–300px 给侧栏卡片：
- 🔑 **关键创新点** — 3–5 条，`#dc2626` 标题
- 📊 **性能指标** — 成功率、速度、数据规模
- 🚀 **推理流程** — 多阶段步骤（Stage 1/2/3）
- ⚙️ **训练**（可选）— 损失函数、数据集

每张图保留 ≥1 个侧栏（参考 `NavDP架构.md`）。

### 3.9 AI 架构图常用图标库

将这些字符直接放入 text 元素：
- 📥 输入  📤 输出  🧠 LLM  👁️ Vision  🎯 Goal
- 🔁 循环  ⏱️ 时延  📊 指标  🔑 创新  🚀 推理
- 箭头：→ ↑ ↓ ↔ ⇒ ⇄
- 数学：× ÷ ± ⊙ ⊕ ⊗ ∑ ∇
- 装饰：✓ ✗ • ・ ━ ┃ ┏ ┓ ┗ ┛

### 3.10 架构家族速查

| 家族 | 视觉模式 |
|------|---------|
| **VLA**（OpenVLA, RT-2） | 横向流水线：RGB+Text → Encoder → LLM → Action Head → 7-DOF |
| **双系统**（InternVLA-N1） | 上下分层 System 2 (Slow) / System 1 (Fast) + 频率标注 |
| **Diffusion Policy** | 噪声 → U-Net 去噪 → 轨迹，DDPM/DDIM 标在路径上 |
| **Transformer 堆叠** | 单块 + `×N` 标记 + 残差弧 |
| **RL** | Actor / Critic 双头并列，环境-策略闭环箭头 |
| **导航**（NavDP, NaVid） | RGB-D → 编码 → 策略 → 轨迹 + 评估头 |

---

## 4. Universal Design Rules

### 4.1 容器纪律（避免「全是矩形」）

只在以下情况用矩形容器：
- 是某个区域的焦点元素
- 需要被箭头连接
- 与其他元素视觉分组
- 形状本身有语义（菱形=决策、椭圆=起止/输出）

**否则用自由文本** — 标签、注释、张量形状、侧栏内容都不要装在矩形里。目标：被装进容器的文本占比 < 50%。

形状语义：

| 概念 | 形状 |
|------|-----|
| 模块/过程 | 矩形（圆角） |
| 起点 / 终点 / I/O | 椭圆 |
| 决策 / 分支 | 菱形 |
| 抽象状态 / 上下文 | 重叠椭圆 |
| 时间点 / 节点 | 小圆点 (10–20px) |

### 4.2 布局与间距

- **画布**：所有元素在 `0 ≤ x ≤ 2000, 0 ≤ y ≤ 1000`。横向 6 段流水线 + 子框 + 右侧面板常达 1700–1850 宽，原 1600 上限不现实。超过 2000 应考虑分屏或重设计。
- **网格对齐**：所有 `x, y` 用 10 或 20 的倍数（视觉对齐；子框内部精度可放宽）
- **重要性 = 留白**：核心元素四周 ≥80px 空白（含子框时模块间距给小，模块组之间留白给大）
- **尺寸层级**（高度按"装得下 4–5 行 fs=13 文字 + container padding"反推）：

  | 层级 | 用途 | 宽×高 | 示例 |
  |------|------|------|------|
  | **Hero+** | 含 2×2 子框的核心模块 | `320–360 × 140–160` | DiT、双系统父框 |
  | **Hero** | 主流水线核心 | `220–240 × 140` | LLM、Vision Encoder |
  | **Primary** | 普通流水线模块 | `180–200 × 120–140` | Input、Output、Decoder |
  | **Sub-box** | 父框内部子组件 | `64–165 × 50–100` | 见 §3.3 子框尺寸表 |
  | **Tag** | 自由文本标签 | autoResize=true | 张量形状、频率标注 |

### 4.3 文字规范

- `fontFamily: 5`（Excalifont，手写感）— 所有文本默认
- `lineHeight: 1.25`
- 字号：标题 24–28、副标题 18–20、正文 14–16、张量/标注 12–14
- 颜色按 §3.1 模块类型；通用文字 `#1f2937`
- **文本替换规则**（解决 Obsidian 解析冲突）：
  - 中文自然语句中的 `(...)` → `「...」`
  - 中文自然语句中的 `"..."` → `『...』`
  - **例外**：技术注解中的张量形状 `(B, 128, 512)`、单位 `(Hz)`、英文短语保留原样

### 4.4 视觉风格

- `roughness: 1`（手绘感，与现有图一致）；如需严肃汇报用 `0`
- `strokeWidth: 2`；关键流用 `3`，标注用 `1`
- `opacity: 100`（除分组背景框可降至 60）
- `roundness: {type: 3}`（圆角矩形）

---

## 5. Element Schema (Required Fields)

### 通用字段（所有 element）

> ⚠️ `index` 字段必须是合法 fractional-indexing 字符串，**末字符不能是 `0`**（见 §7.4 — 违反会让插件静默丢弃整个 elements 数组）。安全模板：`a1..a9, aA..aZ, aa..az`。

```json
{
  "id": "module_vit",
  "type": "rectangle | text | arrow | ellipse | diamond | line",
  "x": 200, "y": 240,
  "width": 200, "height": 100,
  "angle": 0,
  "strokeColor": "#1e40af",
  "backgroundColor": "#dbeafe",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "frameId": null,
  "index": "a1",
  "roundness": {"type": 3},
  "seed": 123456789,
  "version": 1,
  "versionNonce": 987654321,
  "isDeleted": false,
  "boundElements": [{"type": "text", "id": "txt_vit"}],
  "updated": 1751928342106,
  "link": null,
  "locked": false,
  "customData": {"legacyTextWrap": true}
}
```

`boundElements` + `customData`：作为 text container 时**必填**。空数组 + 无 customData 也 OK，但 text 没法靠 container binding 居中。

### text 额外字段

**模式 A — Container-binding（推荐用于盒内文字）**：

```json
{
  "text": "[Vision Encoder]\n=====\n- DINOv2 ViT-L\n- (B, N, 1024)",
  "rawText": "...",
  "fontSize": 14,
  "fontFamily": 5,
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": "module_vit",
  "originalText": "...",
  "autoResize": false,
  "lineHeight": 1.25
}
```

容器（rect/ellipse）和 text 必须双向引用，否则整图可能拒绝渲染：
- rect: `boundElements: [{"type":"text","id":"<text-id>"}]` + `customData: {"legacyTextWrap": true}`
- text: `containerId: "<rect-id>"` + `autoResize: false`

**模式 B — 自由文本（用于标签、张量形状、侧栏内容）**：

```json
{
  "text": "(B, 128, 512)",
  "fontSize": 12,
  "fontFamily": 5,
  "textAlign": "left",
  "verticalAlign": "top",
  "containerId": null,
  "autoResize": true,
  "lineHeight": 1.25
}
```

`autoResize: true` 让文本框自动贴合内容尺寸；`containerId: null` 不绑定。**禁止**用此模式装多行盒内文字 — 垂直居中不稳。

### arrow 额外字段

**默认：不绑定的浮动箭头**（推荐，最稳定）：

```json
{
  "points": [[0, 0], [120, 0]],
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```

只设 `points` 和箭头样式，由作者手动放对位置。这样箭头是"哑"的，不依赖任何元素 ID，几乎不会触发渲染失败。

**高级（易碎）：绑定箭头**：

```json
{
  "points": [[0, 0], [120, 0]],
  "startArrowhead": null,
  "endArrowhead": "arrow",
  "startBinding": {"elementId": "module_a", "focus": 0, "gap": 5},
  "endBinding": {"elementId": "module_b", "focus": 0, "gap": 5}
}
```

绑定箭头会自动随源/目标盒子移动而吸附。但**必须保证双向引用一致**：
- 箭头的 `startBinding.elementId` 指向的盒子，其 `boundElements` 数组里也必须有 `{"id":"<arrow_id>","type":"arrow"}`
- `endBinding` 同理
- 任何一方拼错或漏写，整张图可能直接拒绝渲染

⚠️ 如果不需要吸附行为，**永远优先选浮动箭头**。本 skill 默认浮动。仅当用户明确要求"可拖动连接线"时才用绑定。

### 顶层结构

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin",
  "elements": [...],
  "appState": {"gridSize": null, "viewBackgroundColor": "#ffffff"},
  "files": {}
}
```

完整字段定义见 [`references/excalidraw-schema.md`](references/excalidraw-schema.md)。
AI 架构图复用片段（模块盒/子系统框/标注气泡/侧栏卡片）见 [`references/ai-architecture-patterns.md`](references/ai-architecture-patterns.md)。

---

## 6. Quality Checklist

### 6.1 设计层（人脑判断 — builder 查不出来）

**AI 架构图必检**：
- [ ] 每个张量变形点都标了形状
- [ ] 同类模块用了同色（按 §3.1）
- [ ] 子系统用大框框住、加标题
- [ ] 用了真实模型名（不是 "Encoder 1"）
- [ ] 重复堆叠用 `×N` 标记
- [ ] 至少一个侧栏（创新点 / 指标 / 推理流程）
- [ ] 子框间数据依赖都画了内部箭头（见 §3.3）
- [ ] 同等复杂度的模块**统一**用子框 or 单盒（不混搭，否则视觉失衡）

**通用设计必检**：
- [ ] 容器占比 < 50%（其余用自由文本）
- [ ] 中文自然语句的 `()` `""` 已转义为 `「」` `『』`
- [ ] 关键元素周围有适当留白
- [ ] 整体宽度 ≤ 2000

### 6.2 兼容性层（**用 `Builder.validate()` 自动跑** — 不用人工查）

`Builder.write()` 默认调 `validate(strict=True)`，覆盖以下 7 项。失败立即 abort，不会写出坏文件：

1. ✅ 所有 `id` 唯一
2. ✅ 所有 `index` 末字符不是 `0`（fractional-indexing 合法）
3. ✅ 所有 `index` 唯一
4. ✅ container binding 双向一致（rect.boundElements ↔ text.containerId）
5. ✅ arrow binding 双向一致（如果用了）
6. ✅ 自由文本不溢出（按 §3.3 公式估算）
7. ✅ 文本无 `^{...}` `_{...}` 花括号上下标

**如果你不用 builder（手写 JSON）**：把 `references/builder_template.py` 的 `Builder.validate()` 函数抠出来跑一遍。**禁止**没跑自检就写文件。

---

## 7. Error Prevention「常见踩坑与根因」

记录已发生过的故障 + 根因 + 永久规避方式：

### 7.1 图生成后无法显示「空白 / 转 Excalidraw 视图后报错」

**根因**：Obsidian Excalidraw 插件首次打开 `.md` 文件时会自动把 `json` 压缩为 `compressed-json` base64。压缩输入若违反任一条件，输出 base64 会损坏（出现意外换行、`===` 多余 padding、截断）：

| 触发条件 | 修复 |
|---------|------|
| JSON 跨多行缩进（pretty-print） | 改为单行紧凑（每 element 一行） |
| 文本含 `R^{H×W×3}` 等花括号上下标 | 改为 `R³` / `(B,H,W,3)` |
| 箭头有 `startBinding` 但目标盒子 `boundElements` 没有反向引用 | 删除绑定，改用浮动箭头 |
| 手写 ` ```compressed-json ` fence | 永远只写 ` ```json `，由插件自己压缩 |

### 7.2 Text Elements 段与 JSON 不同步

**根因**：`^id` 与 JSON 中 text element 的 `id` 字段不一致，插件会重生成 Text Elements 段并破坏原内容。

**规避**：每个 text element 在 Text Elements 段必须有对应 `^id` 行，且字符串完全一致。生成前自检 `^xxx` 与 JSON `"id":"xxx"` 一一对应。

### 7.3 重新打开后 Text Elements 出现重复条目

**根因**：插件 round-trip 时，原 Text Elements 段没被清理，新内容追加在后面。

**规避**：用户改动后若发现重复，让用户在命令面板执行 `Excalidraw: Decompress current Excalidraw file`，再手动清理重复段，或直接重新生成整个文件覆盖。

### 7.4「最坑」打开后画布完全空白，但 JSON 看起来没问题

**症状**：
- 文件用 Python `json.loads` 校验通过
- Obsidian 自动压缩为 `compressed-json` 没报错
- 用 `lzstring` 解压压缩内容后 → `"elements": []`（**整个数组被插件丢弃**）
- 画布空白，没有任何错误提示

**根因**：每个 element 的 `index` 字段必须是合法的 [fractional-indexing](https://github.com/rocicorp/fractional-indexing) 字符串。Excalidraw 用此字段决定 z-order，插件会在加载时**对所有 element 调用 `validateFractionalIndex`，任何一个不合法整个 elements 数组就会被静默丢弃**（不抛错，不警告）。

**合法规则**（base-62 字母表 `0-9A-Za-z`）：
- 第一字符是排序桶（通常 `a`）
- 末字符**不能是 `0`**（fractional-indexing 禁止"尾部零"，因为 `a0` 与 `a00` 在数值上等价 → 不规范）
- 中间字符可以是任何 base-62 字符
- ✅ 合法：`a1`, `a2`, `aA`, `aZ`, `aa`, `az`, `b1`, `aOg`
- ❌ **非法**：`a0`（注意 `a0` 本身也不合法因为以 0 结尾）、`a00`, `a10`, `a20`, `aB0`, `b0`

**等等 `a0` 不合法？** 严格来说 `a0` 在 fractional-indexing 规范里是「base case」可用，但很多实现（包括 Excalidraw 用的版本）拒绝末字符是 `0` 的任何字符串。安全做法：**永远不用末字符是 `0` 的索引**。

**生成规则（推荐）**：N 个元素按 z-order 顺序分配 `a1, a2, ..., a9, aA, aB, ..., aZ, aa, ab, ..., az`（共 9+26+26 = 61 个安全值，够大多数图用）。超过 61 个就用 `b1, b2, ...`。

**自检脚本**（生成前必跑）：
```python
indices = [e['index'] for e in elements]
bad = [i for i in indices if i.endswith('0')]
assert not bad, f"Trailing-zero indices: {bad}"
assert len(set(indices)) == len(indices), "Duplicate indices"
```

**调试技巧**：怀疑画布空白时，用 `lzstring` 解压 `compressed-json`，如果看到 `"elements": []` 但你明明写了几十个，99% 是 index 问题。

```python
# 一行式解压调试脚本
import re, json, lzstring
c = open('YourDiagram.md', encoding='utf-8').read()
m = re.search(r'```compressed-json\s*\n(.*?)\n```', c, re.DOTALL)
data = json.loads(lzstring.LZString().decompressFromBase64(m.group(1).replace('\n','').replace(' ','')))
print(f"elements: {len(data['elements'])}")  # 0 = index 问题；正常数 = 别处坏
```

### 7.5 子框 / 单盒里多行文字顶部对齐，没有居中

**症状**：sub-box 或 simple module 里的多行文字（如 `[Title]\n=====\n- item1\n- item2`）渲染时贴顶部，垂直方向没居中。

**根因**：自由文本（`containerId: null`）的 `verticalAlign: "middle"` 在 Excalidraw 的渲染逻辑里**只对单行可靠**，多行常被忽略。Excalidraw 内置的 container binding 才会真正"测量文本块高度并垂直居中放进容器"。

**规避**：
- 盒内多行文字必须用 container binding：rect 加 `boundElements: [{type:"text", id:"<txt>"}]` + `customData: {legacyTextWrap: true}`，text 加 `containerId: "<rect>"` + `autoResize: false`。
- `Builder.module()` 和 `Builder.subbox()` 默认就是这套。永远用它们，别手写。
- 父框的标题（顶部 `y=parent.y+4`）反而**应该**用自由文本 + `valign: "top"`（要的就是顶部对齐）。

### 7.6 用户提了小修改后，要重跑 builder 还是手改 JSON？

**永远重跑 builder**。理由：
- 文件已被 Obsidian 压缩成 `compressed-json` base64 — 手改 JSON 必须先解压（`Excalidraw: Decompress current Excalidraw file` 命令面板），改完插件可能再压缩一次，每次 round-trip 都是潜在的损坏点。
- 手改容易漏更新 `Text Elements` 段，触发 §7.2 不同步问题。
- builder 重跑保证所有自检都过、双向引用一致。

**唯一例外**：用户只改文字内容（不动结构）+ 文件还在 ` ```json ` fence（没被插件压缩过）。这种情况可以 Edit。否则一律重跑 Python builder。

---

## 8. 用户反馈消息（生成后简短报告）

```
✅ 已生成：{filename}
📍 路径：{absolute_path}
🎨 类型：{diagram_type} — {one-line rationale}
📖 在 Obsidian 中打开 → MORE OPTIONS → Switch to EXCALIDRAW VIEW
```

不要堆砌 emoji 段落。如对方需要调整（布局/配色/细节），等他提出再迭代。
