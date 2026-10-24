# 指令与 3D 轨迹的一致性契约

指令里每一个方向词、每一个楼梯词、每一个终止地标，都在对 `reference_path` 做断言。
断言错了，训练出来的就是空间幻觉。本文给出判定算法、阈值来源，以及剖面到措辞的映射。

所有算法与阈值与上游 `R2RA-RXR-VLNCE-Refined` 的
`scripts/r2r/trajectory_aligner.py` / `spatial_validator.py` / `visual_artifact_filter.py`
逐行一致，`scripts/check_instruction.py` 是它们的独立移植。

## 1. Habitat 坐标系与转角判定

Habitat / MP3D 用 **Y-up** 右手系：水平面是 **(X, Z)**，**Y 是高度**。
判定转向只看水平投影。

```
     +Z                    连续两段位移向量 s1 → s2：
      │                      cross = s1.dx * s2.dz - s1.dz * s2.dx
      │    s2                dot   = s1.dx * s2.dx + s1.dz * s2.dz
      │   ↗                   θ    = acos(dot / (|s1||s2|))
      │  /
      │ /  θ                cross > 0  →  RIGHT   （注意：正号是右转）
      └────────── +X        cross < 0  →  LEFT
           s1               θ > 135°   →  U_TURN（不分左右）
```

判定流程：

```
reference_path (N 个 waypoint)
   │
   ├─ 相邻点求位移，水平位移 dist_2d ≤ 0.05 m 的段丢弃   ← 去 waypoint 抖动
   │
   ├─ 相邻两段求夹角 θ
   │     θ ≤ 25°   → 不算转向（直行中的漂移）
   │     θ > 135°  → u_turn
   │     否则       → cross > 0 ? right : left
   │
   └─ 输出 turn_sequence + net_turns{left, right, u_turn}
```

## 2. 阈值表

| 常量 | 值 | 含义 | 来源 |
| :--- | :--- | :--- | :--- |
| `SEGMENT_MIN_DIST` | 0.05 m | 低于此水平位移的段视为抖动，丢弃 | `trajectory_aligner.py` |
| `TURN_MIN_DEG` | 25° | 超过才算一次转向 | `trajectory_aligner.py` |
| `U_TURN_MIN_DEG` | 135° | 超过算掉头 | `trajectory_aligner.py` |
| `STAIRS_MIN_DY` | 0.25 m | 低于此高程差不得提楼梯 | `spatial_validator.py` |
| `STAIRS_MUST_MENTION_DY` | 1.8 m | 高于此高程差必须描述上下楼 | `trajectory_aligner.py` |
| `TELEPORT_MAX_STEP` | 5.0 m | 单步超过即判轨迹损坏 | `spatial_validator.py` |
| `goal.radius` | 3.0 m | R2R-CE 全部 episode 恒定 | 数据集 schema |

> RxR 的 `rxr_spatial_validator.py` 统计物理转向时用的是 **≥35°**，比 R2R 严。
> 本技能按 R2R 的 25° 判定，遇到 25–35° 的边缘转角时人工确认一下再落笔。

## 3. 剖面 → 措辞：允许与禁止

| 运动剖面 | 允许 | 禁止 |
| :--- | :--- | :--- |
| `net_turns = {left:0, right:2}` | turn right ×2；也可只写其中一个显著转角 | 任何 left（触发 `direction_contradiction`） |
| `net_turns = {left:1, right:1}` | 左右各一次，按 `waypoint_index` 顺序写 | 顺序颠倒 |
| `turn_sequence = []` | continue / walk straight / walk down the hall | turn left / turn right |
| `u_turn ≥ 1` | `Turn around and ...` | 把掉头写成 turn left |
| `Δy < 0.25 m` | 平面移动词 | stairs · steps · upstairs · downstairs · staircase · stairway |
| `0.25 ≤ Δy ≤ 1.8 m` | 楼梯词可写可不写（半层、台阶、坡道） | 写了但画面里没有台阶 |
| `Δy > 1.8 m` | **必须**写 `go up/down the stairs` 之类 | 完全不提高程（触发 `elevation_unmentioned`） |
| `max_step_dist > 5 m` | —— | 这条 episode 本身坏了，别给它写指令 |

### 方向矛盾的精确判定

只有在**语言完全单向**且**轨迹完全反向**时才判 ERROR，避免误伤：

```
说 left 不说 right  AND  net_turns.left == 0  AND  net_turns.right >= 2   → 矛盾
说 right 不说 left  AND  net_turns.right == 0 AND  net_turns.left  >= 2   → 矛盾
```

`>= 2` 这个门槛是故意的：单个转角可能落在 25° 阈值附近抖动，两个同向转角才足以
证明轨迹的整体走向。R2R `train` 里有 88 条、`joint_train_envdrop` 里有 12,482 条
命中这条规则。

### 转角存在但轨迹没有

`turn_without_path_turn` 是 WARN 不是 ERROR。`reference_path` 只有 5–10 个稀疏
waypoint，智能体实际执行的小幅转身不会体现在里面。看到这条时：

- 剖面里有接近 25° 的夹角 → 方向词大概率是对的，保留
- 整条路径近乎直线 → 删掉方向词，改成 `continue straight`

## 4. episode 自身的几何健康

写指令之前先确认这条 episode 没坏，否则写得再好也是给脏数据配文案：

| 检查 | 判据 |
| :--- | :--- |
| `start_position` == `reference_path[0]` | 距离 > 1e-3 m 即不合法 |
| `start_rotation` 四元数归一 | \|norm − 1\| > 1e-3 即不合法 |
| 无瞬移 | 任意相邻 waypoint 距离 ≤ 5.0 m |
| 终点落在目标内 | `dist(reference_path[-1], goals[0].position) ≤ radius + 1.0 m` |

`check_instruction.py --episode` 会一并报这四项。

## 5. 视觉可见性：别描述被黑洞吞掉的地标

MP3D 网格有扫描盲区、玻璃反射和外部空洞，渲染出来是纯黑区域（$RGB \le 10$）。
被黑洞覆盖的地标，智能体根本看不见，写进指令就是无法 grounding 的噪声。

| 阈值 | 含义 |
| :--- | :--- |
| `max_void_ratio ≥ 0.40` | 单帧严重空洞 → `BLACK_SHADOW_VOID_SEVERE` |
| `max_void_ratio ≥ 0.25` | 单帧中度空洞 |
| `max_consecutive_corrupted ≥ 3` | 连续 3 帧损坏 → `CONSECUTIVE_BLINDSPOT_STAGNATION` |
| 损坏帧 / 总帧 ≥ 0.15 | 整条轨迹判无效 |

episode 里若已有 `visual_quality.is_valid = false`，脚本报 `visual_void` (WARN)。
处理方式：换一个位于干净帧里的地标，或者干脆放弃这条 episode
（上游 `_clean.json.gz` 子集就是这么筛掉 828 条 R2R `train` episode 的）。

## 6. 写回数据集的字段格式

指令文本落在 `instruction.instruction_text`；若同时要补一致性 metadata，
沿用上游 schema（与 `{split}.json.gz` 的 refined 版本一致）：

```json
{
  "instruction": {
    "instruction_text": "Exit the room, turn right into the corridor, and wait near the mirror.",
    "instruction_tokens": [ ... ]
  },
  "spatial_alignment": {
    "is_consistent": true,
    "alignment_score": 1.0,
    "flags": [],
    "turn_sequence": [{"waypoint_index": 2, "direction": "right", "angle_deg": 88.4}]
  },
  "visual_quality": {
    "is_valid": true,
    "max_void_ratio": 0.031,
    "mean_void_ratio": 0.004,
    "corrupted_frames_count": 0,
    "max_consecutive_corrupted": 0,
    "flags": []
  }
}
```

`alignment_score` 的取值：完全一致 `1.0`，一致但有非致命 flag（如
`elevation_unmentioned`）`0.5`，方向矛盾 `0.0`。

**改了 `instruction_text` 就必须重算 `instruction_tokens`。** 词表与 tokenizer 在上游
`scripts/r2r/tokenizer.py`；只改文本不改 token 会让经典 GloVe 模型读到与文本对不上的
序列。整批改写走上游 `scripts/r2r/run_pipeline.py`，不要手工拼 JSON。
