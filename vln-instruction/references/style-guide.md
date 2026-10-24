# R2R-CE 英文指令风格指南

所有统计取自 R2R-VLNCE `val_seen` + `val_unseen`（n = 2,617 条真实人工指令）。
写出来的句子要能混进这批数据里看不出来，同时不带原始数据的脏毛病。

## 1. 数据画像：一条正常指令长什么样

| 维度 | 实测 |
| :--- | :--- |
| 词数 | 均值 26.7，p10 **14**，中位 **25**，p75 32，p90 **42**（最长 119） |
| 句数 | 中位 **2**，p75 3，p90 4 |
| 含 stop / wait / stand | **85.6%** |
| 含 left / right | **77.9%** |
| 起手词 | walk 36% · go 18% · turn 15% · exit 13% · leave 4% · head/enter/take/move/continue/pass 各 1–2% |

**目标区间：20–35 词、2–3 句、一定要有终止动作。** 低于 14 词通常是漏了地标，
高于 42 词说明这条轨迹该拆或者你在写小说。

## 2. 三拍骨架

```
[起手]  从出生位姿能立刻执行的第一个动作
   ↓    Walk out of / Exit / Turn around / Go down / Walk past
[推进]  每个 >25° 的转角一句，每句挂一个可见地标
   ↓    turn left|right + into|towards|through + <地标>
[终止]  Stop / Wait + near|in|in front of|beside + <目标半径内的地标>
```

真实样本（`val_seen` 原文，未经改写）：

```
Go down the stairs. Turn right. Go past the glass display case and wait in front
of the bench on the right.
        ↑起手              ↑推进            ↑地标            ↑终止 + 地标 + 侧向

Exit the room through the only door with an arched, round design above it.
Continue straight through the small hall and enter the next room. Stop once you
reach the blue mat.

Walk past the water fountain and turn left. Walk to the doorway directly across
from the stairs. Stop in the doorway.
```

## 3. 起手动作：由出生位姿决定

| 出生状态 | 起手写法 |
| :--- | :--- |
| 面朝出口 / 走廊 | `Walk out of the bedroom` · `Exit the room` · `Go through the doorway` |
| 面朝墙 / 背对路径 | `Turn around and ...`（对应剖面里的 u_turn） |
| 第一段就是转角 | `Turn left and walk down the hallway` |
| 面朝楼梯（Δy 够） | `Walk down the stairs` · `Go up the stairs` |
| 第一段直行 | `Walk forward past the ...` · `Walk towards the ...` |

`Leave the ...` 与 `Exit the ...` 等价，交替使用可以避免整批数据句式雷同。

## 4. 推进句：动词 + 介词的固定搭配

| 意图 | 写法 | 反例 |
| :--- | :--- | :--- |
| 经过某物 | `walk past the table` | ~~walk passed the table~~ · ~~passed by the table~~ |
| 穿过开口 | `walk through the doorway` · `go through the double doors` | ~~enter into the doorway~~ |
| 进入房间 | `enter the kitchen` · `walk into the bedroom` | ~~enter into the kitchen~~ |
| 沿走廊 | `walk down the hallway` · `continue down the hall` | ~~walk down to hallway~~ |
| 朝目标 | `walk towards the fireplace` | ~~walk forward towards the fireplace~~（冗余） |
| 转向 | `turn left` · `turn right` · `turn around` | ~~make a left~~ · ~~take a right~~ · ~~taking a left~~ |
| 轻微偏转 | `veer left` · `bear right` · `head slightly right` | — |
| 上下楼 | `go up the stairs` · `walk down the steps` | — |
| 直行 | `continue straight` · `go straight ahead` | ~~go straightly~~ |
| 侧向定位 | `on your right` · `on the left side of the room` | ~~on right~~ · ~~rightside~~ |
| 相对定位 | `in front of the sofa` · `next to the piano` · `between the bench and the carpet` · `at the end of the hallway` · `directly across from the stairs` | ~~infront of~~ |

## 5. 终止句：85.6% 的指令靠它收尾

```
Stop near the bench and piano along the right side of the wall.
Wait in front of the bench on the right.
Stop once you reach the blue mat.
Stand on the wood between the bench and the carpet.     ← stand 也在数据里，但 stop 更清晰
```

规则：

- 动词用 `Stop` 或 `Wait`（`Stop and wait there` 也可），**不要**用 `stand in the` / `stand near`
- 后面必须跟一个**目标半径（3.0 m）内看得见**的地标，不能是 `stop there` / `stop at the end`
- 地标最好带一个区分性修饰：颜色、材质、或与另一个物体的相对关系
- 终止地标出现过一次就够，不要在最后一句堆三个地标

## 6. 地标锚定

技能自带的地标名词表（`scripts/lexicon.py :: LANDMARK_NOUNS`，40 个）覆盖了 MP3D 里
高频、可分辨的物体与房间：

```
房间   bedroom bathroom kitchen living room dining room hallway corridor balcony patio
结构   stairs staircase stairway door doorway window fireplace
家具   table chair couch sofa bed closet bench desk piano shelf bookshelf cabinet counter
电器   refrigerator fridge oven sink tv television lamp fan
软装   mirror rug carpet
```

- **每条指令至少 2 个地标锚点**，其中一个在终止句里；`no_landmark` 这条 WARN 意味着
  智能体没有任何可 grounding 的对象。
- **优先挑独特的**：`the glass display case` / `the water fountain` / `the piano` 强于
  `the room` / `the area`。
- **不要写数值距离**：R2R 几乎不用 `walk 5 meters`，全部是地标相对定位。

### 同类物体多时怎么消歧：按可靠性排序

场景里有三把椅子时，说 `the chair` 等于没说。四种消歧手段效果差很远，
**从上往下挑第一个能用的，一个地标只用一种**：

| 排序 | 手段 | R2R 里的写法 |
| :---: | :--- | :--- |
| ① | **方向 + 物体**（最可靠） | `the desk on your right` · `the bench on the right` · `the front-left door` |
| ② | **关系锚点** | `the leather chairs next to the table` · `the vase on the dining table` · `the bedroom with the blue floral blanket` |
| ③ | **极值** | `the leftmost curtain` · `the rightmost door`（`leftmost`/`rightmost` 优于 `nearest`/`farthest`，后者要求深度估计） |
| ④ | **序数**（最弱，少用） | `the first door on the right` —— 必须配数数方向，且不超过 `third` |

- 方向永远相对**智能体**，不是相对房间。
- `the third door on the left` 只有在那三扇门同框可见时才成立；数不清就换成 ① 或 ②。
- 别叠加：`the leftmost first chair next to the table on your right` 反而更难解析。

> 这套排序同样是**单目标指令**（`Go to the front-left TV` 那种体裁）的核心，
> 完整版见 [`object-goal-style.md`](object-goal-style.md)。`check_instruction.py` 在两种模式下
> 都会检查序数与深度极值。

## 7. 禁用短语表（AMT 顽疾 → 规范写法）

`check_instruction.py` 会以 `awkward_phrase` (WARN) 命中这些，全部来自上游
`scripts/r2r/llm_refiner.py`：

| 原始 | 改写 |
| :--- | :--- |
| `To turn ...` | `Turn ...` |
| `Then take left enter into` | `Then turn left and enter` |
| `enter into` | `enter` |
| `passed by` / `passed the` | `past` / `past the` |
| `taking a left` / `make a left` / `make left` | `turn left` |
| `taking a right` / `make a right` / `make right` | `turn right` |
| `proceed to your left` | `proceed to the left` |
| `door way` | `doorway` |
| `stand in the` / `stand near` / `stand by` | `stop in the` / `stop near` / `stop by` |
| `wait right there` | `stop and wait there` |
| `walk forward towards` | `walk towards` |

另有 303 条拼写纠正与 17 条粘连词（`turnleft` → `turn left`、`infront` → `in front`、
`walkdown` → `walk down`），由脚本以 `typo` / `fused_word` (ERROR) 命中，不必背。

## 8. 语域与机械规范

- **句首大写、句尾句号**；句号后首字母大写。
- **禁止 ALL CAPS**。原始数据里真有整条大写的（`TURN LEFT YOU FACE A CHANDELIER ...`），
  它会把 GloVe 与现代 tokenizer 的词表命中率打穿。
- **第二人称祈使句**。不写 `You should walk`、不写 `The agent walks`、不写 `I want you to`。
- **不写元信息**：`in this task`、`the episode ends`、`navigate to the goal` 都不该出现。
- **逗号后必须有空格**，句号后必须有空格 —— 原始数据里 22,900+ 处缺空格，
  直接把 `word,word` 整体打成 `<unk>`。
- **单空格**，不要双空格；不要 `..` / `,,`；引号用 ASCII `'` `"`。
- 一句一个动作意图；用逗号串联的并列动作（`Walk down the stairs, turn right, and walk
  towards the rug.`）是数据里的常见写法，可以用。

## 9. 好 / 坏对照

```
✗ walk froward past the dinning table,then go striaght into the kithchen and turnleft
  → 5 个 ERROR：4 处拼写 + 1 处粘连逗号，外加缺终止动作
✓ Walk forward past the dining table and go straight into the kitchen. Turn left and
  stop near the sink.

✗ TURN LEFT YOU FACE A CHANDELIER ABOVE A GREEN TABLE WITH A DOOR WAY TO THE LEFT ...
  → all_caps + door way
✓ Turn left to face the chandelier above the green table. Walk towards the open door
  on the far wall and go through it. Stop in the room with the blue patterned carpet.

✗ Walk down the hallway and stop.
  → 8 词、无地标、终止位置不可定位
✓ Walk down the hallway past the mirror and stop in the doorway of the bedroom on
  the right.

✗ Exit the room, turn left into the corridor, and wait near the mirror.
  （配一条纯右转轨迹 → direction_contradiction）
✓ Exit the room, turn right into the corridor, and wait near the mirror.

✗ Walk up the stairs and turn right.
  （配一条 Δy = 0.10 m 的平地轨迹 → stairs_hallucination）
✓ Walk down the hall and turn right.
```

## 10. 落笔前的 checklist

- [ ] 跑过 `--profile`，方向词与 `net_turns` 同号
- [ ] Δy 与楼梯词的存在与否一致（<0.25 禁提，>1.8 必提）
- [ ] 20–35 词 / 2–3 句
- [ ] ≥2 个地标，终止句里有一个且在 3.0 m 目标半径内
- [ ] 以 Stop / Wait 收尾
- [ ] 句首大写、句尾句号、标点后有空格、无 ALL CAPS
- [ ] `check_instruction.py` exit 0
