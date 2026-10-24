---
name: paper-insert
description: >
  Insert a completed paper summary (from paper_summary/) into one of the four survey posts
  (VLA, VLM, World Models, or Spatial Intelligence) based on its theme.
  Use when the user requests to insert a summary into a survey post, e.g.,
  "把文章插入到 VLA 综述", "add summary to world models survey", "insert paper into survey".
  Automatically updates heading numbers, anchors, and post date.
---

# Paper Insert Skill

将生成的中文论文总结插入到对应的综述博客文章中（VLN, VLA, VLM, World Models, Spatial Intelligence），自动完成序号调整、锚点设置、基准排行榜插入及博客更新时间修改。

这个 skill 是为 [tingdeliu.github.io](https://github.com/TingdeLiu/tingdeliu.github.io) 的几篇综述写的，下表的文件名和章节标题都对应那几篇文章。用在自己的博客上时，改 `scripts/insert_paper.py` 里的 `MAP` 即可。

## 支持的主题与目标博客

| 主题 (`--topic`) | 目标博客文件 | 章节标题 | 序号前缀 |
|------------------|--------------|----------|----------|
| `vln` | `_posts/research/2026-01-05-VLN-Papers.md` | `# 具身导航经典论文` | 自动递增 (如 `62`) |
| `vla` | `_posts/research/2026-01-24-VLA-Survey.md` | `# 5. 经典论文深度解析` | `5` |
| `vlm` | `_posts/research/2026-03-05-VLM-Survey.md` | `# 8. 经典方法与代表性工作` | `8` |
| `wm` / `world-models` | `_posts/research/2026-04-16-World-Models-Survey.md` | `# 5. 经典代表性工作` | `5` |
| `si` / `spatial-intelligence` | `_posts/research/2026-04-29-Spatial-Intelligence-Survey.md` | `# 6. 经典论文深度解析` | `6` |

---

## 综述主题归属极简判定法 (Decision Tree)

在执行插入前，按以下决策树确定 `--topic`，杜绝分类混淆：

### 1. 五大主题核心边界速查

- **`vla` (视觉-语言-动作 / 具身操控)**：
  - **核心特征**：机器人策略网络、机械臂/灵巧手操控、动作 Token (Action Tokens)、Diffusion Policy、端到端具身执行。
  - **代表模型**：OpenVLA, Octo, RT-2, π0, GROOT, 3D-VLA 等。
- **`vln` (具身导航)**：
  - **核心特征**：室内外主动导航、路径规划、拓扑图导航、Continuous VLN、Object-goal Navigation。
  - **代表模型**：VLN-BERT, DUET, NaviLLM, MapGPT 等。
- **`wm` / `world-models` (世界模型 / 物理环境模拟)**：
  - **核心特征**：视频生成作为物理世界模拟器、环境动力学建模、未来帧/动作条件预测 (Action-conditioned Video Gen)。
  - **代表模型**：GAIA-1, UniSim, WorldDreamer, Sora-like Embodied WM 等。
- **`si` / `spatial-intelligence` (空间智能 / 3D 几何与推理)**：
  - **核心特征**：点云/3DGS/NeRF、单目/多目深度估计、3D 目标检测与重建、相机位姿/6D Pose、3D-LLM、度量空间推理。
  - **代表模型**：Depth Anything, VGGT, MapAnything, 3D-LLM, LLaVA-3D, HiSpatial, VLM³, DepthLM, LangSplat, GaussianVLM 等。
- **`vlm` (通用视觉-语言基座)**：
  - **核心特征**：2D 图像/视频通用理解、OCR/文档解析、通用多模态对齐架构（ViT/CLIP/SigLIP/Q-Former/MLP Projector）、多模态大模型预训练与后训练技术栈（SFT/RLHF/DPO/PPO）。
  - **代表模型**：CLIP, Flamingo, BLIP-2, LLaVA, InternVL 系列, Qwen-VL 系列, Mage-VL, DINOv3 等。

### 2. 重点辨析：VLM vs 空间智能 (SI) 判定准则

由于现代 VLM 正在空间化，而空间智能正在大模型化，二者常有交叉。判定时请遵循以下规则：

```
                    ┌────────────────────────┐
                    │     判断输入与输出      │
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
【强 3D / 物理空间几何】                         【通用 2D 图像 / 视频 / 图文】
- 点云 / 3DGS / NeRF / 深度图                   - 2D 图片 / 网页截图 / 普通视频
- 3D Bounding Box (7/9自由度)                   - 文本 / 2D Bbox (Grounding)
- 相机位姿 / 6D 抓取位姿 / 绝对坐标             - OCR / 图表 / 代码 / 通用对话
- 单目/多目 3D 几何重建任务                      - 模态对齐架构 / 训练范式
        │                                               │
        ▼                                               ▼
归入【空间智能综述】(`--topic si`)                归入【VLM 综述】(`--topic vlm`)
```

- **跨界复合模型分流规则**：
  1. **通用多模态基座**（以通用图文/视频理解、多模态预训练后训练为主要贡献，如 Qwen2.5-VL / Qwen3-VL / InternVL2） $\rightarrow$ 归入 `--topic vlm`。
  2. **针对 3D/空间任务特化或核心贡献为 3D 空间推理**（如 3D-LLM, LLaVA-3D, VGGT, MapAnything, VLM³, DepthLM） $\rightarrow$ 归入 `--topic si`；并在其解析中提及 2D 底座时，添加跳转链接回引至 VLM 综述（如 `[LLaVA](/VLM-Survey/#85-llava2023)`）。

---

## 工作流

**Step 1 — 确定总结文件路径与目标主题**

- 总结文件通常位于: `$BLOG_ROOT/paper_summary/paper-summary-{PaperName}.md`。脚本从环境变量 `BLOG_ROOT` 找博客仓库根目录，没设置时用当前目录。
- 参考上述【综述主题归属极简判定法】选择对应的 `--topic`（`vln`、`vla`、`vlm`、`wm` 或 `si`）。

**Step 2 — 确定插入位置（可选）**

- **默认追加**: 如果不指定 `--after` 参数，脚本会将论文自动追加到对应章节的末尾。
- **指定论文后**: 如果该论文是另一篇论文的直接演进（如 InternVLA-A1.5 之于 InternVLA-A1），可通过 `--after "InternVLA-A1"` 指定在其后插入。脚本会自动计算正确的插入行，插入新章节，并将后面所有论文的二级标题序号全部顺延，同时**保持被顺延论文原有的 HTML 锚点 ID 不变**以避免破坏已有的内联链接。

**Step 3 — 运行脚本执行插入**

```bash
export BLOG_ROOT=/path/to/your/blog

# 默认追加到末尾
python "$HOME/.claude/skills/paper-insert/scripts/insert_paper.py" \
  "$BLOG_ROOT/paper_summary/paper-summary-InternVLA-A1.5.md" \
  --topic vla

# 插入到指定论文后，并顺延后续序号
python "$HOME/.claude/skills/paper-insert/scripts/insert_paper.py" \
  "$BLOG_ROOT/paper_summary/paper-summary-InternVLA-A1.5.md" \
  --topic vla \
  --after "InternVLA-A1"
```

`--topic vln` 会转交给同一 skills 目录下的 `vln-paper-insert`，两个 skill 需要装在一起。

**Step 4 — 更新校验**

- 运行完成后，检查目标博客的 Front Matter 的 `date` 字段是否已被自动修改为今天的日期。
- 用 `git diff` 确认内容和序号递增行为符合预期。

## 注意事项

1. **Jekyll 公式安全**: 插入前请确保公式已遵守 MathJax 安全规则（行内公式中含有 `}_` 等组合时用 `$$...$$` 包含）。
2. **直引号规则**: 插入前确保所有的图片标签属性使用的是直引号 `"`。
