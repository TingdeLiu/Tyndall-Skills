# 单目标指令风格指南（object-goal）

与 R2R-CE 的长程路线描述不同，这类指令只做一件事：**让机器人走到某一个物体前**。
没有多段转角、没有地标链，成败几乎全押在「这句话有没有说清是哪个物体」上。

```
[action verb] + [direction (可选)] + [消歧后的物体短语] + [and stop (可选)]
```

动词随便挑，不影响成功率：`Go to` / `Walk to` / `Head to` / `Walk towards` / `Approach`。
长度落在 **3–16 词、单句**；`--mode object-goal` 按这个尺子量。

## 消歧的四种策略：按可靠性排序，一条指令只用一种

「消歧」= 读完这句话，不存在第二个候选物体。四种做法效果差得很远，**从上往下挑第一个能用的**。

### ① 方向 + 物体 —— 最可靠，优先用

```
Turn left and walk to the red lamppost
Go to the front-left TV
Go to the desk on your right and stop.
Turn right, then walk to the chair and stop.
```

- 方向可以放在动作前（`Turn left and go to X`），也可以挂在物体后（`the desk on your right`），两种都成立。
- **室内**优先 `front-left` / `front-right` / `in front`；**室外**优先 `turn left` / `turn right`。
- **方向永远相对机器人，不是相对房间。** 写指令的人站在机器人视角，不是俯视图视角。

### ② 关系锚点（next to / on / behind）—— 次选

```
Walk towards the trash can next to the green lawn
Walk to the vase on the dining table ahead.
Go to the table behind you
Head to the plant behind you on the right.
```

- `A next to B` / `A on B` / `A behind you` 都有效。
- **`behind you` 特别好用**：一句话同时给了方向（转身）和消歧，等于免费拿到策略 ①。
- 锚点 B 要**大且显著**——lawn / trees / dining table / walkway，不要拿另一个小物体当锚点。

### ③ 极值（leftmost / nearest）—— 可用

```
Go to the leftmost TV in front
Walk to the rightmost curtain.
Turn left and walk to the nearest grey pointed stone bollard on the park lawn
```

- **`leftmost` / `rightmost` 明显优于 `nearest` / `farthest`**：前者在画面里直接可见，
  后者要求模型做深度估计。checker 命中 nearest/farthest 时会给 `depth_dependent_extreme`。

### ④ 序数（first / second / third）—— 最弱，少用

```
Walk to the first wooden park bench on the right
Turn left and walk to the second stone bench from the left.
Go to the first chair on the right side of the dining table
```

- **序数必须配数数方向**（`from the left` / `on the right`），否则从哪头开始数是不确定的
  → `ordinal_without_anchor`。
- **不要超过 third** → `ordinal_beyond_third`。
- 要单独点出一个物体时，优先用极值（`leftmost`）或关系（`next to the door`），别用序数。

## 不要叠加策略

一条指令挑一种就够。`Walk to the leftmost first chair next to the table on your right`
同时用了四种，反而增加解析歧义 → `stacked_disambiguation`（≥3 种时告警）。

例外：**序数 + 数数方向**不算叠加，那是策略 ④ 的完整形态；
**方向 + 关系锚点**（`the vase on the dining table ahead`）也常见且稳定。

## 反例

```
✗ Go to the chair                       → 有几把椅子就有几个候选，无消歧
✓ Go to the chair on your right

✗ Go to the second chair                → 从哪头数？
✓ Go to the second chair from the left

✗ Walk to the fifth bench from the left → 超过 third，数不准
✓ Walk to the leftmost bench

✗ Walk to the nearest chair             → 要深度估计
✓ Walk to the chair on your left

✗ The robot should probably move over to the area near the desk if possible and then halt
                                        → 无动词开头、17 词、无消歧、"area" 不是物体
✓ Go to the desk on your right and stop.

✗ Go to the cup next to the pen         → 锚点太小
✓ Go to the cup on the dining table
```

## 自检

```bash
python scripts/check_instruction.py --mode object-goal --text "Go to the front-left TV"
python scripts/check_instruction.py --mode object-goal --file drafts.txt
```

输出末行会报出识别到的策略：

```
[1] "Go to the leftmost TV in front"
    OK     clean
    ----   7 words / 1 sentences / 1 landmarks / disambiguation: direction+extreme
```

`disambiguation: none` 说明这句话没有任何消歧手段，必须补。

## 落笔前的 checklist

- [ ] 以 Go to / Walk to / Head to / Walk towards / Approach 开头
- [ ] 3–16 词、单句
- [ ] 恰好用了**一种**消歧策略，且是当前场景能用的最高一档
- [ ] 方向词是机器人视角，不是房间视角
- [ ] 用了序数就配了数数方向，且不超过 third
- [ ] 关系锚点足够大、足够显著
- [ ] `check_instruction.py --mode object-goal` 无 WARN（或每条 WARN 都能说清为什么保留）

## 与 route 体裁的分界

| | object-goal | route（R2R-CE） |
| :--- | :--- | :--- |
| 目标 | 一个物体 | 一条多段路径 |
| 长度 | 3–16 词，单句 | 20–35 词，2–3 句 |
| 转角 | 至多一个，用于消歧 | 每个 >25° 转角一句 |
| 地标 | 1 个目标 + 至多 1 个锚点 | ≥2 个，串成链 |
| 结尾 | `and stop` 可选 | Stop/Wait 收尾（85.6%） |
| 3D 校验 | 通常无 `reference_path` 可比 | 必须跑 `--profile` 对齐 |
| 句尾句号 | 可省 | 必须有 |

写着写着超过 16 词、出现第二个转角，说明这其实是一条 route
—— 换 `references/style-guide.md` 的三拍骨架重写。
