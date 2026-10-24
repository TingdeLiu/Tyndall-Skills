---
name: vln-instruction
description: 撰写、改写或体检英文导航指令，覆盖两种体裁——(a) VLN-CE（R2R-CE / RxR-CE）轨迹的长程路线指令 instruction_text，可直接写回 {split}.json.gz；(b) 机器人单目标指令（Go to the front-left TV 那种）。规范包括零错字与零粘连标点、方向词与 3D 轨迹转角一致、Δy≥0.25m 才能提楼梯、地标锚定与物体消歧策略排序、终止动作明确。触发词示例：「写一条 R2R 指令」「给这条轨迹配导航指令」「改写这批 VLN 指令」「检查这条导航指令有没有问题」「写机器人导航指令」「物体导航指令怎么写」「VLN 提示词」。
---

# vln-instruction — 写 VLN-CE 英文导航指令

**先看轨迹，再写句子。** 指令不是凭空的英文写作，它是对一条 3D 轨迹的语言编码：
方向词必须与 `reference_path` 的实际转角同号，楼梯词必须有高程差撑着，终止地标必须
落在目标半径里。R2R 原始数据里 1,440+ 条指令就是栽在这三件事上。

```
episode(reference_path, goals, scene)
        │
        ├─ 1. 读运动剖面 ──► check_instruction.py --profile
        │      turn sequence / Δy / goal radius  ← 这是硬事实，不可改
        │
        ├─ 2. 按骨架落笔 ──► references/style-guide.md
        │      起手动作 → 沿途地标推进 → stop/wait near <地标>
        │
        └─ 3. 自检 ───────► check_instruction.py --episode ep.json --text "..."
               ERROR = 必改（写回数据集前必须 exit 0）
               WARN  = 看一眼，多数该改
```

只处理**英文**指令（`en-US` / `en-IN`）。

## 先分体裁

两种指令长得完全不一样，尺子也不一样。判断标准是**目标是一条路径还是一个物体**：

| | `--mode route`（默认） | `--mode object-goal` |
| :--- | :--- | :--- |
| 长什么样 | `Go down the stairs. Turn right. Go past the glass display case and wait in front of the bench on the right.` | `Go to the desk on your right and stop.` |
| 目标 | 一条多段路径 | 一个物体 |
| 长度 | 20–35 词，2–3 句 | 3–16 词，单句 |
| 成败关键 | 方向词与 3D 轨迹对齐 | 物体消歧说没说清 |
| 有 `reference_path` | 有，必须跑 `--profile` | 通常没有，跳过第 1 步 |
| 风格文档 | `references/style-guide.md` | `references/object-goal-style.md` |

写到一半发现 object-goal 超过 16 词、冒出第二个转角 —— 那它其实是 route，换骨架重写。

## 环境

- Python 3：任意解释器均可（Windows 上若 `python` 指向 WindowsApps 占位符，改用 conda 或官方安装的 `python.exe` 完整路径）
- 依赖：无，纯标准库
- 脚本：`scripts/check_instruction.py`，词表 `scripts/lexicon.py`（303 条错字 / 9 条拉长拼写 / 17 条粘连词，
  从 [`R2RA-RXR-VLNCE-Refined`](https://github.com/TingdeLiu/R2RA-RXR-VLNCE-Refined) 的 `scripts/r2r/typo_dict.py` + `scripts/rxr/rxr_typo_dict.py` 生成）

## 三步流程

### 1. 先拿运动剖面

```bash
python scripts/check_instruction.py --profile --episode ep.json
```

`ep.json` 可以是单个 episode 对象，也可以是 `{"episodes": [...]}` 或 `.json.gz` 整个 split
（配 `--episode-id` 挑一条）。输出：

```
motion profile  (6 waypoints)
  path length      11.52 m
  max step         4.32 m
  elevation dy     1.54 m   (mild slope -> stairs optional)
  net turns        left=0  right=2  u_turn=0
  turn sequence:
    wp2    right   104.9 deg
    wp3    right    73.8 deg
  goal             radius 3.0 m, final waypoint 0.00 m away
  skeleton         <start action> -> turn right -> turn right -> stop near <landmark ...>
```

**这一步不能跳过。** 没有剖面就写方向词，等于在赌左右——原始 R2R 的方向矛盾就是这么来的。

### 2. 按骨架落笔

三拍结构，真实 R2R 的中位数是 **25 词 / 2 句**（p10–p90 = 14–42 词）：

```
[起手] Walk / Go / Turn / Exit / Leave  + 从出生位姿能立刻执行的动作
[推进] 每个 >25° 的转角写成一句，挂一个可见地标
[终止] Stop / Wait + near|in|in front of + 目标半径内的地标
```

写完对照 `references/style-guide.md` 的动词表与禁用短语表；方向 / 楼梯 / 终止地标的
硬约束在 `references/consistency.md`。

### 3. 自检到 exit 0

```bash
# 单条 + 3D 校验
python scripts/check_instruction.py --episode ep.json --text "Walk down the stairs, turn right, ..."

# 一批草稿（每行一条，无 3D 校验）
python scripts/check_instruction.py --file drafts.txt

# 体检现成的 split（只打印有问题的 episode）
python scripts/check_instruction.py --episodes val_seen/val_seen.json.gz --limit 200

# 单目标指令
python scripts/check_instruction.py --mode object-goal --text "Go to the front-left TV"
```

输出末行会报出识别到的消歧策略，`disambiguation: none` 意味着物体没说清：

```
    ----   7 words / 1 sentences / 1 landmarks / disambiguation: direction+extreme
```

`ERROR` 一条都不能留；`WARN` 逐条判断（`too_short` 在短轨迹上可以接受，
`no_terminal_action` / `no_landmark` 基本都该改）。加 `--json` 拿机器可读结果。

## 硬约束速查（细节见 references/consistency.md）

| 事实 | 措辞约束 |
| :--- | :--- |
| `net_turns.left=0, right≥2` | 只写 right；写 left 直接判 `direction_contradiction` |
| `Δy < 0.25 m` | **禁用** stairs / steps / upstairs / downstairs / staircase / stairway |
| `Δy > 1.8 m` | **必须**描述上下楼 |
| 无 >25° 转角 | 不要写 turn；用 continue / walk straight |
| `goal.radius`（R2R 恒为 3.0 m） | 终止地标必须在这个半径内看得见 |
| `visual_quality.is_valid = false` | 该 episode 有 mesh 空洞，别去描述可能被黑洞吞掉的地标 |

## 何时读哪个 reference

- **`references/style-guide.md`** — 写 route 前必读：三拍骨架、动词与介词搭配、
  禁用短语表（`enter into` → `enter`、`make a left` → `turn left`…）、地标锚定与
  消歧排序、真实数据里的好/坏对照。
- **`references/object-goal-style.md`** — 写 object-goal 前必读：模板公式、
  四种消歧策略的可靠性排序与适用场景、反例、体裁分界表。
- **`references/consistency.md`** — 需要判断「这条轨迹到底转没转」「能不能提楼梯」
  「metadata 怎么写」时读：转角判定算法、阈值来源、`spatial_alignment` /
  `visual_quality` 字段格式。

## 几个已知坑

- **别信原始指令的方向词**。改写现成指令时，先跑 `--profile`；R2R 里
  `Make a left ... Make another left ... Make another left` 配的是一条纯右转轨迹。
- **`turn_without_path_turn` 不一定是错**。轨迹只有 5 个稀疏 waypoint 时，
  智能体实际执行的小角度调整不会体现在 `reference_path` 上。看到这条 WARN 时
  确认 Δθ 是否接近 25° 阈值，别机械删掉方向词。
- **Δy 在 0.25–1.8 m 之间是灰区**。半层楼梯、台阶、坡道都落在这里，写不写都不算错，
  但写了就要和画面对得上。
- **`larg` / `som` / `dor` 这类词典项会命中正常缩写**。看到反直觉的 `typo` ERROR，
  先确认原文不是专有名词，再决定是否忽略。
- **方向永远是智能体视角，不是房间视角**。`the door on the right` 指的是机器人当前
  朝向的右边，写的时候要跟着轨迹的朝向走，不是跟着俯视图。
- **`depth_dependent_extreme` 是排序建议不是错误**。`the nearest bollard` 能用，
  只是不如 `the leftmost bollard` 稳；场景里确实没有左右可分时保留即可。
- 词表是从上游仓库生成的快照。上游 `typo_dict.py` 更新后，重新生成 `scripts/lexicon.py`。
