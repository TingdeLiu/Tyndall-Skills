---
name: vln-paper-insert
description: >
  Insert a completed paper summary into one of the two VLN Papers blog posts —
  主篇 /VLN-Papers/ (capped at 60 papers) or 扩展篇 /VLN-Papers-Extended/ (uncapped).
  Use after the paper-summary skill completes, when the user says things like
  "把总结添加到VLN博客", "补充进去", "加到VLN论文列表", or "insert into blog post".
  Always ask which page first; inserting into a full 主篇 requires demoting one existing
  paper to 扩展篇 to stay at 60. Handles five insertion points automatically: main
  content section (with {#anchor}), TAG_MAP entry, numbered reference entry, the
  已发表论文（会议 / 期刊）venue table (published papers only), and (optional)
  leaderboard rows — 指令跟随 ①②③ on 主篇, 目标导航 ④–⑧ on 扩展篇, each row needing a
  训练 / 免训练 paradigm. Always re-sync the cross-page filter afterwards, and refresh the
  前列模型要素打勾矩阵 whenever a R2R-CE (表①) row with SR ≥ 60 is added, changed or moved.
---

# VLN Paper Insert

这个 skill 是为 [tingdeliu.github.io](https://github.com/TingdeLiu/tingdeliu.github.io) 的两篇 VLN 论文列表写的，章节标题、排行榜表头、筛选脚本都按那两篇文章的结构定位。用在自己的博客上时，照这套结构改脚本里的标题和路径即可。

脚本从环境变量 `BLOG_ROOT` 找博客仓库根目录，没设置时用当前目录。下面命令里的 `$BLOG_ROOT` 换成本机博客仓库的路径；不知道在哪时先问用户，不要猜：

```bash
export BLOG_ROOT=/path/to/your/blog
```

不带 `--blog` 时默认写 `$BLOG_ROOT` 下的主篇。

## 两篇文章

论文列表分为两篇，**插入前必须先问用户放哪一篇**：

| | 路径 | 定位 | 容量 |
|---|---|---|---|
| **主篇** | `_posts/research/2026-01-05-VLN-Papers.md` → `/VLN-Papers/` | 已发表于会议期刊，或已进入指令跟随排行榜（①②③）；另有 `# 性能排行榜`（①②③）与前列模型要素矩阵 | **上限 60 篇**（2026-09-27 为 55 篇） |
| **扩展篇** | `_posts/research/2026-01-06-VLN-Papers-Extended.md` → `/VLN-Papers-Extended/` | 其余论文，多为近期预印本与扩展增补；另有 `# 目标导航性能排行榜`（④–⑧） | 不限 |

- 选**扩展篇** → 直接插入，没有额外步骤。
- 选**主篇** → 主篇未满 60 篇时直接插；满 60 篇时必须先用 `move_paper.py` 调一篇旧的到扩展篇，
  腾出位置再插。由用户指定调哪一篇；不要自行决定。
- 只出现在目标导航榜（④–⑧）上的预印本不满足主篇收录条件：目标导航不是指令跟随 VLN，这些榜单放在扩展篇。

两篇的筛选器会合并展示彼此的命中项，靠各自内嵌的 `REMOTE_PAPERS` 清单实现。
**任何增删之后都要跑 `sync_remote.py`**，否则跨页筛选漏论文、总数对不上。

Inserts a `paper_summary/paper-summary-XXX.md` into the chosen blog post at up to five locations:
1. New `## N. PaperName (year) {#anchor}` section before `# 相关基础工作`
2. TAG_MAP entry in the JavaScript filter
3. Numbered reference entry in the `## 论文引用` list under `# 参考资料`
4. A deep-link entry in the `## 已发表论文（会议 / 期刊）` venue table — **published papers only**.
   The venue is parsed from the summary's `📄 **Paper**` line (`· 🏛️ **VENUE YEAR**`, emitted by the
   paper-summary skill) or supplied via `--venue`; preprints (no venue) are skipped here.
5. (Optional) One or more leaderboard rows — ①②③ under 主篇 `# 性能排行榜`, ④–⑧ under 扩展篇
   `# 目标导航性能排行榜` — with the model name deep-linked to the section anchor (cross-page when the
   table lives on the other page), the row inserted at its SR-sorted position within its benchmark group,
   and the table's bold re-applied by rule

## Available Tags

Choose from this fixed set (comma-separated for `--tags`):

| 标签 | 适用场景 |
|------|---------|
| `双系统` | System 1 + System 2 双过程架构 |
| `端到端` | 端到端训练/推理 |
| `Agentic` | VLM/LLM Agent 框架，主动探索 |
| `CoT` | 链式思考，显式逻辑推理能力 |
| `扩散模型` | 扩散模型驱动的动作或策略 |
| `拓扑图` | 拓扑/语义图辅助导航 |
| `SLAM` | 地图构建、前端感知 |
| `高斯表示` | 3D Gaussian Splatting 场景表示 |
| `强化学习` | RL/RLHF/GRPO 训练 |
| `零样本` | Zero-shot 泛化，无任务特定训练 |
| `世界模型` | 世界模型/视频生成辅助 |
| `数据增强` | 数据生成/合成/扩增 |
| `连续环境` | VLN-CE 等连续动作空间 |
| `离散环境` | R2R/REVERIE 等离散视点图 |
| `实机部署` | 有真实机器人实验 |
| `加速优化` | 推理加速/训练效率 |
| `数据集` | 提出新数据集/基准 |
| `基础工作` | 非 VLN 主方向的依赖基础工作 |

## Workflow

**Step 0 — 选择目标页面（必做，先问用户）**

问用户这篇放主篇还是扩展篇。不要替用户决定——判断依据是这篇论文的分量，只有用户清楚。

选**扩展篇**：无额外动作，Step 5 加 `--blog` 指向扩展篇即可。

选**主篇**：先数主篇现有篇数；未满 60 篇直接进 Step 1。满 60 篇时先请用户指定要调哪一篇去扩展篇，然后：

```bash
python \
  "$HOME/.claude/skills/vln-paper-insert/scripts/move_paper.py" \
  --anchor <要调走的论文锚点> --dry-run
```

先 `--dry-run` 看清影响（尤其「原页 N 处链接改为跨页」那行——被调走的论文若在排行榜里有行，
链接会自动改成 `/VLN-Papers-Extended/#anchor`，排行榜行本身保留，因为它是对比表不是目录）。
确认无误后去掉 `--dry-run` 执行。方向自动判断，无需指定；插入位置遵循两篇统一的排序约定（按年份升序）。

**Step 1 — Locate summary file**

Typically at `$BLOG_ROOT/paper_summary/paper-summary-{Name}.md`.

**Step 2 — Determine tags**

Read the summary briefly and pick 2–4 tags. Common combinations:
- 3DGS + zero-shot navigation → `Agentic,高斯表示,零样本`
- End-to-end + RL + continuous env → `端到端,强化学习,连续环境`
- Traditional SLAM (no LLM) → `SLAM,连续环境`

Ask the user if unsure.

**Step 3 — Extract leaderboard metrics (`--rank`)**

Read the summary's 核心结果 / main results and pull out reported SR/SPL (and NE/OSR where
given). For **each** (benchmark, task) the paper reports, add one `--rank` entry. A paper that
reports two settings (e.g. Image-Goal and Point-Goal) gets two `--rank` flags — same model name,
different benchmark/numbers.

Pick the sub-table by task type (the circled number is the `table=` value). 目标导航表按
「目标形式 · 代表基准」命名；①②③ 在主篇，④–⑧ 在扩展篇，脚本按表号自动写到对应页面。
只有一篇论文报告的自建基准（不论目标形式）一律写进 ⑧，不进 ④–⑦：

| `table` | 排行榜子表（页面） | 适用 | 基准列 | 指标列 |
|:-:|------|------|:-:|----|
| `1` | ① R2R-CE（主篇） | R2R-CE val-unseen 全量；Open-Nav 的 100 条子集加 `flag=100 条子集` | 无 | SR/SPL/NE/OSR |
| `2` | ② RxR-CE（主篇） | RxR-CE val-unseen | 无 | SR/SPL/NE/OSR |
| `3` | ③ R2R · REVERIE（主篇） | 离散 R2R / GSA-R2R / REVERIE | 有 | SR/SPL/NE/OSR |
| `4` | ④ 封闭类别物体目标 · ObjectNav（扩展篇） | HM3D-v1 / HM3D-v2 / MP3D / Gibson 封闭类别物体导航 | 有 | SR/SPL |
| `5` | ⑤ 开放词汇物体目标 · HM3D-OVON（扩展篇） | 开放词汇物体导航，默认 val-unseen；未写明划分的在模型名后加 `<sup>†</sup>` | 无 | SR/SPL |
| `6` | ⑥ 图像目标 · HM3D-IIN / Image-Goal（扩展篇） | HM3D-IIN、Image-Goal | 有 | SR/SPL |
| `7` | ⑦ 点目标 · Point-Goal（扩展篇） | 多篇可比的 Point-Goal 基准（如 Clutter/Intern） | 有 | SR/SPL |
| `8` | ⑧ 多模态目标与自建基准（扩展篇） | GOAT-Bench 与只有一篇论文报告的自建基准 | 有 | SR/SPL |

HM3D ObjectNav 原文没写 v1 / v2 时，先按场景 / 条数（v1 = 2000 条 / 20 场景，v2 = 1000 条 / 36 场景）
或原文基线的数字（与基线原文哪个版本的成绩一致）推断；推断不出来才写 `HM3D（未注明版本）`，并在表下注释说明依据。

`--rank` spec is semicolon-separated `key=value`. Keys:
- `table`（必填，1–8）、`paradigm`（必填，`训练` 或 `免训练`，口径见下）
- `benchmark`：③④⑥⑦⑧ 必填，照抄表里已有的基准写法（如 `HM3D-v2`、`Clutter/Intern (Point-Goal)`），
  写成新名字会新开一组并打印 ⚠；①②⑤ 标题已限定基准，不写入
- `SR`、`SPL`、`NE`、`OSR`、`base`（基模）、`code`，以及 `model` / `year` 覆盖（默认取论文名与年份）；缺的指标写成 `–`
- `flag`：非标准口径时填，如 `flag=100 条子集`、`flag=200 条子集`。该行会带 `.lb-flag` 角标、灰显、不参与加粗

**范式判定口径**（页面「读表」里写的同一条）：**训练** = 在导航数据上训练或微调过模型（含跨任务零样本迁移的
导航基础模型，如 NavFoM）；**免训练** = 不训练任何导航模型，由现成大模型、检测分割模型与规则 / 规划模块组合而成，
调用现成的点目标低层控制器（如 VLFM 的 PointNav、HarnessVLN 的 NavDP）不影响归类。只微调了一个任务相关的
分类器也算训练（如 GaussNav 用 IIN 训练集微调 ResNet）。**不要照 TAG_MAP 的「零样本」标签判断**——那个标签
也打在 NaVid、Image2Sim 等零样本 sim-to-real 的训练式模型上。拿不准时查原文实验表里的 Training / Zero-shot 列。

**加粗由脚本自动管理**：插入后按「同一基准内、非灰色行、至少两个数值时取最优（NE 取最小），并列都加粗」重算
整张表，与页面上 `js/leaderboard.js` 筛选后的重算规则一致，不要手工改加粗。

If the paper reports no comparable SR (real-world-only / non-navigation / 基础工作), **skip `--rank`**
— those papers are intentionally excluded from the tables (see the 说明 note above the tables).

**Step 4 — Determine venue (会议 / 期刊)**

Check the summary's `📄 **Paper**` line for a `· 🏛️ **VENUE YEAR**` tag (the paper-summary skill
emits this for published papers; preprints have none). The script auto-parses it, so you usually
do nothing. Pass `--venue "ICRA 2024"` only to override or to add a venue the summary omitted.

- **Conferences** (CVPR, ICCV, ECCV, ICLR, AAAI, ICRA, ACL, NeurIPS, CoRL, …) get their own row,
  entry rendered as `[Name](#anchor) (year[, Poster])`.
- **Everything else** (IEEE TPAMI / RA-L, Sensors, Springer journals, …) falls into the `期刊`
  row with the full venue kept inline: `[Name](#anchor) (IEEE TPAMI 2025)`.
- **Preprints**: no `--venue`, no 🏛️ tag → the table is left untouched (correct — don't force one).

**Step 5 — Run the script**

```bash
python \
  "$HOME/.claude/skills/vln-paper-insert/scripts/insert_paper.py" \
  "$BLOG_ROOT/paper_summary/paper-summary-{Name}.md" \
  --tags "Tag1,Tag2,Tag3" \
  --venue "ICRA 2024" \
  --rank "table=1;paradigm=训练;SR=66.2;SPL=58.8;NE=3.85;OSR=74.5;base=Qwen2.5-VL-7B" \
  --rank "table=6;paradigm=训练;benchmark=Clutter/Intern (Point-Goal);SR=80.4;SPL=78.0" \
  --rank "table=6;paradigm=训练;benchmark=Clutter/Intern (Image-Goal);SR=50.2;SPL=48.2"
```

Add `--anchor <slug>` only to override the auto slug (default: paper name lowercased,
e.g. `WAM-Nav` → `wam-nav`); match the existing curated convention if one exists.
Drop `--venue` when the summary already carries the 🏛️ tag, or for preprints.

**插入扩展篇时**追加 `--blog "$BLOG_ROOT/_posts/research/2026-01-06-VLN-Papers-Extended.md"`
（不加则默认写主篇）。`--rank` 照常传：①②③ 的行写进主篇、④–⑧ 的行写进扩展篇，表不在论文所在页时
模型链接自动写成跨页形式（`/VLN-Papers/#anchor` 或 `/VLN-Papers-Extended/#anchor`）。
扩展篇没有会议表；若论文有会议出处，或有 ①②③ 的成绩，说明它满足主篇收录条件，回 Step 0 与用户确认。

**Step 5b — 同步跨页筛选清单（必做）**

```bash
python \
  "$HOME/.claude/skills/vln-paper-insert/scripts/sync_remote.py"
```

重新生成两篇内嵌的 `REMOTE_PAPERS`。跳过这步的后果：新论文不会出现在另一篇的筛选结果里，
且筛选栏的总数（如「共 68 篇」）会少算。脚本幂等，可反复跑；`--check` 只报告不写入。

**Step 5c — 刷新前列模型要素打勾矩阵（主篇，表① 有变动时必做）**

主篇排行榜下面的「# 前列模型技术方案分析」里有两节派生内容：「## 要素打勾矩阵」和「## 统计研判」。矩阵收录的正是**排行榜 ① 里 SR ≥ 60 且非灰显的每一行**——带 `flag=`（如 100 条子集）的灰显行样本太少、口径不同，不进矩阵（2026-09-29 用户决定；GPT-6-Astra、Talk2Escape 因此只在矩阵下方的说明里提及）。所以只要下面任一情况发生，矩阵就过期了：

- 这次 `--rank table=1` 插入了 SR ≥ 60 的非灰显行（`insert_paper.py` 的 `⚠ 前列矩阵` 提醒可能也会因灰显行触发，以 `refresh_matrix.py --check` 为准）
- 手工改了表① 里某个 ≥ 60 条目的数字，或数字从 60 以上掉到 60 以下
- 用 `move_paper.py` 调走 / 调回了一篇在矩阵里的论文（链接要变成跨页形式）

拿不准时直接跑 `--check`，它只读不写：

```bash
python \
  "$HOME/.claude/skills/vln-paper-insert/scripts/refresh_matrix.py" --check
```

脚本负责机械部分：对账（表① ≥ 60 的行 ⇄ 矩阵行）、同步 SR / 链接 / 开源列、删掉已不达标的行、按 SR 重排编号、
重算底部「统计」行和研判里的两档对比表、改正文里的条目计数。**打勾本身需要判断，脚本不猜**——表① 有新行而矩阵
没有时，`--check` 会列出缺哪几行并给出 `--add` 模板，然后按以下步骤补：

1. **逐列判定**：打开主篇矩阵上方的「打勾口径」表，拿新论文在主篇里的章节正文逐列对照；正文没写清的
   （数据量、是否用 DAgger / RL、输入几路相机、动作输出形式），去 arXiv 原文查。查不到的记 `–`。
2. **按取得该 R2R-CE 成绩的那套配置判定**，不是按模型的全部能力：例如 OmniNav 的 R2R 评测只走快系统，
   所以双系统记 `–`；Qwen-RobotNav 的上层 Agent 只用于 EQA，所以 Agentic 记 `–`；套在别的模型上的
   加速 / 包装方法（如 VLN-Cache 之于 DualVLN）继承底座的要素。
3. **不要照名字或 TAG_MAP 标签打勾**。标签是给筛选器用的，口径更宽：名字里带 Agent 不等于 Agentic，
   TAG_MAP 里的「双系统」也可能指双记忆 / 双编码器。过去的矩阵就因为照名字给端到端 VLA 打了 Agentic 而失真。
4. 用 `--add` 写入（列名写前缀即可；开源列自动跟随排行榜，同一锚点在表① 有多行时加 `sr=` 区分）：

   ```bash
   python \
     "$HOME/.claude/skills/vln-paper-insert/scripts/refresh_matrix.py" \
     --add "anchor=groundingvln;cfg=三相机;yes=堆相机,双系统,像素,强化学习"
   ```

5. **人工收尾**（脚本改不了正文）：
   - 脚本打印「两档对比表有变化」时，逐条核对「统计研判」正文里引用的比例（如「57% vs 6%」「6/7」）和举例，
     新论文若构成新证据或反例（如 188K 样本进前列、训练无关方法跨过 60%），写进对应条目。
   - 新行里有需要解释的判定（继承底座、评测配置与完整模型不同、依据 arXiv 补充的信息），追加到矩阵下方的「注：」。
   - 新行若挤进第一梯队或改变了某个要素在两档中的高低关系，重读研判的每一条结论和结尾「小结」，确认仍然成立。

**Step 6 — Report result**

Show the confirmation lines from the script output (the 已发表表 line appears only for published
papers; the 排行榜 lines only when `--rank` is passed):
```
✓ Inserted   ## N. PaperName (year) {#anchor}
✓ TAG_MAP    { m: 'Name', t: [...] }
✓ Reference  N. **Name** (year). ...
✓ 已发表表   | **ICRA** | …、[Name](#anchor) (year) |
✓ 排行榜 表⑥  | [Name](#anchor) | year | benchmark | 训练 | base | SR | SPL | 开源 |
```

If Step 5c ran, also report the matrix changes it printed (added / dropped rows, the tier-table deltas)
and which 研判 bullets you rewrote.

If `⚠ 表X 新增基准组` appears, check whether the benchmark is really new or just a different spelling of an
existing group (e.g. `HM3Dv2` vs `HM3D-v2`); fix the row's 基准 cell by hand if it is the latter.
If `⚠ new venue row「X」created` appears, glance at the venue table to confirm the new conference
row landed sensibly (it is inserted just above the `期刊` row).

## Notes

- Section number is auto-detected from existing `## N.` headings in the 具身导航经典论文 section.
- TAG_MAP match string is the paper name extracted from the `## PaperName (year)` heading — verify it's unique enough to not accidentally match other entries.
- Reference number = last existing reference number + 1 (counted from the `## 论文引用` numbered list;
  the venue table's `| **ECCV** |`-style rows are not numbered references and don't affect this).
- Venue table: the entry is appended to the end of the matching row. Journal venues keep their raw
  text verbatim — occasionally a curated entry uses a hand-normalized form (e.g. existing
  `Vicinagearth / Springer 2025` vs. the parsed `Vicinagearth (Springer) 2025`); polish by hand if
  it bothers you. New conference rows land just above `期刊`; reorder by hand only if you care about
  a particular ordering (the table is not strictly sorted).
- Leaderboard rows are inserted in SR-descending order — within the row's benchmark group for tables
  with a 基准 column (③④⑥⑦⑧), across the whole table otherwise; rows with no numeric SR fall to the
  bottom of their group. The script re-applies `**bold**` to the whole table by rule after each insert.
- 页面上的筛选（`js/leaderboard.js`，两篇末尾 `<script src="/js/leaderboard.js">` 引入）按表头名读列：
  模型 / 基准 / 范式 / SR / SPL / NE / OSR / 开源，灰显靠模型格里的 `<span class="lb-flag">`，输入配置靠模型名括号里的
  单目 / 多目 / 全景 / 三相机 / 四视角 / 180°。**改列名、加列或改括号写法时，同步改 `insert_paper.py` 的
  `build_rank_row` 与 `js/leaderboard.js`。** 两篇内嵌的论文筛选只把「N. 名称」形式的二级标题当论文章节，
  排行榜标题（如「① R2R-CE」）不会被误包。
- The section heading gets a `{#anchor}` so leaderboard rows can deep-link to it; reuse the same
  anchor for every `--rank` row of this paper (the script does this automatically).
- Use `--blog <path>` to override the default blog post path if needed（增补篇必须传）。
- **主篇 60 篇是硬上限**，`move_paper.py` 会在超出时直接报错拒绝。收录条件是「已发表于会议期刊 **或**
  已进入指令跟随排行榜（①②③）」；2026-09-27 把目标导航榜移到扩展篇时，只靠目标导航榜入选的 7 篇预印本
  （VLingNav、Hydra-Nav、3DGSNav、SysNav、WAM-Nav、EvoMemNav、LocalNav）调去了扩展篇，按用户选择只调回在榜的
  BudVLN 与 NavGPT-2，主篇变为 55 篇；扩展篇里仍有已发表但未调回的论文（LoGoPlanner、VL-Nav、Route2Step 等），
  以后有空位时可以问用户是否调回。若哪天想改判据，注意别把 VLN-CE(ECCV)、NoMaD(ICRA) 这类奠基工作挤出主篇。
- `move_paper.py` 一次搬运会同时处理四处：章节正文、参考条目、TAG_MAP 条目，以及原页残留的
  锚点链接（改成跨页形式）。搬运后两篇都会重新编号。搬回来时链接会自动还原为页内锚点，
  但章节位置按目标页的年份排序重新落位，未必回到原来的序号——内容不丢，只是顺序变了。
- 四个脚本的关系：`insert_paper.py` 加论文 → `move_paper.py` 在两篇间调换 →
  `sync_remote.py` 同步跨页筛选清单；`refresh_matrix.py` 刷新主篇的前列模型要素矩阵。
  **前两个跑完都要跑 `sync_remote.py`，只要动到表① 的 ≥ 60 行（含调篇）就再跑 `refresh_matrix.py`。**
- `refresh_matrix.py` 靠三个标题定位：`## ① R2R-CE`、`## 要素打勾矩阵`、`## 统计研判`；矩阵表头以 `| 排名 |` 开头，两档对比表表头以 `| 要素 |` 开头且含
  `SR ≥ X%`（X 即分档阈值）。改这些标题或表头时同步改脚本。
