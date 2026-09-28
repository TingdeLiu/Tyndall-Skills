---
name: statusline-buddy
description: Set up a Claude Code custom status line with an animated living ASCII golden capybara buddy/companion easter egg, real-time stats, and completion notification sound on Windows or macOS. Use when configuring statusLine in settings.json, when bash/jq/Unicode errors occur, when the user wants a sound alert, or when adding a status-bar pet/companion. Auto-detects OS and Python vs Node.js runtime.
---

# Status Line & Notification Setup (Windows / macOS)

## Claude: Follow these steps in order

---

### Step 1 — Detect OS and runtime

**Detect OS** — run the appropriate command based on what shell is available:

```bash
# Mac / Linux
uname -s        # returns "Darwin" on Mac
```
```powershell
# Windows
$env:OS         # returns "Windows_NT"
```

Set `OS` to `windows` or `mac` for use in later steps.

**Detect runtime** — check in order of preference:

| Command | Check |
|---|---|
| `python3 --version` | Mac preferred |
| `python --version` | Windows preferred |
| `node --version` | Fallback for both |

- Python available → use `scripts/statusline.py`, command = `python3` (Mac) or `python` (Windows)
- Node.js only → use `scripts/statusline.js`, command = `node`
- Neither → tell user to install Node.js and re-run

**Get home directory:**
- Mac: `echo $HOME` → e.g. `/Users/alice`
- Windows: `$env:USERPROFILE` → e.g. `C:\Users\alice`

---

### Step 2 — Ask user preferences with AskUserQuestion

Call `AskUserQuestion` with these two questions:

**Q1:** "Claude 完成响应后播放提示音？" (header: "提示音")
- 叮咚 Ding — 清脆短促（Mac: Glass / Windows: ding.wav）(Recommended)
- 铃声 Chime — 较悠长（Mac: Tink / Windows: chimes.wav）
- 蜂鸣 Beep — 系统蜂鸣，无需声卡
- 不播放 — 仅配置状态栏

**Q2:** "上下文用量警告阈值？" (header: "警告阈值")
- 70% 警告 / 85% 危险 (Recommended)
- 80% 警告 / 95% 危险
- 60% 警告 / 80% 危险

---

### Step 3 — Copy script to ~/.claude/

Copy the chosen script:
- Python: `scripts/statusline.py` → `~/.claude/statusline.py`
- Node.js: `scripts/statusline.js` → `~/.claude/statusline.js`

---

### Step 4 — Build the sound command

**Mac** (`afplay` is built-in, no dependencies):

| Choice | Command |
|---|---|
| 叮咚 Ding | `afplay /System/Library/Sounds/Glass.aiff` |
| 铃声 Chime | `afplay /System/Library/Sounds/Tink.aiff` |
| 蜂鸣 Beep | `osascript -e 'beep'` |

**Windows** (`powershell` is always available):

| Choice | Command |
|---|---|
| 叮咚 Ding | `powershell -WindowStyle Hidden -NonInteractive -c "[System.Media.SoundPlayer]::new('C:\\Windows\\Media\\ding.wav').PlaySync()"` |
| 铃声 Chime | `powershell -WindowStyle Hidden -NonInteractive -c "[System.Media.SoundPlayer]::new('C:\\Windows\\Media\\chimes.wav').PlaySync()"` |
| 蜂鸣 Beep | `powershell -WindowStyle Hidden -NonInteractive -c "[Console]::Beep(880,200)"` |

---

### Step 5 — Update ~/.claude/settings.json

Read the existing file, then **merge** these fields (preserve any existing keys):

```json
"statusLine": {
  "type": "command",
  "command": "<runtime> <home>/.claude/statusline.<ext>"
},
"hooks": {
  "Stop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "<sound-command-from-step-4>"
        }
      ]
    }
  ]
}
```

- If user chose 不播放: omit the `hooks` block (preserve any pre-existing hooks)
- If `hooks.Stop` already exists: append to the array, do not replace
- Windows paths in `command`: use forward slashes (`C:/Users/...`) — Claude Code handles both

---

### Step 6 — Verify

Test the script:

```bash
# Mac / Linux
echo '{"model":{"display_name":"Sonnet 4.6"},"context_window":{"used_percentage":25},"cost":{"total_cost_usd":0.05},"rate_limits":{"five_hour":{"used_percentage":10},"seven_day":{"used_percentage":30}}}' | python3 ~/.claude/statusline.py
```
```powershell
# Windows (Node.js)
echo '{"model":{"display_name":"Sonnet 4.6"},"context_window":{"used_percentage":25},"cost":{"total_cost_usd":0.05},"rate_limits":{"five_hour":{"used_percentage":10},"seven_day":{"used_percentage":30}}}' | node "$env:USERPROFILE/.claude/statusline.js"
```

Tell the user setup is complete and what the status bar will look like.

---

## Status Bar Output Format

```
Sonnet 4.6  ctx [████░░░░░░░░░░░░] 25%  $0.050  5h:10%  7d:30%  (·oo·) ♥♥♥ you got this
```

Color coding (using chosen thresholds):
- Green — below warn threshold
- Yellow — warn to danger
- Red — at or above danger threshold

---

## Buddy 宠物 (彩蛋)

状态栏行尾住着一只**金色的传说级卡皮巴拉** —— Claude Code 内置 companion 彩蛋的移植版。单行，但它**活着**：每次状态栏刷新都会换一个姿态，靠「当前时间」驱动待机动画、靠「会话状态」决定心情、心情再决定它摆什么姿势、冒什么符号、说什么话。固定一只，已内建在两个脚本里，无需任何配置。

**它长这样**（四层拼出来，从不只剩一张干巴巴的脸）：

```
\(^ww^)/  ♥♥♥  proud of you
│         │    └─ 话 —— 暗色，四帧里说三帧
│         └────── 符号 —— 每一帧都有，所以绝不会只剩一张脸
└──────────────── 姿势 + 脸 —— 举爪、泡水、咀嚼、眨眼、单眼眨
```

- **姿势** `pose` —— `\ /` 举爪、`/` 挥手、`~ ~` 泡在水里、`?` 歪头
- **脸** —— 眼睛看 ctx 用量，嘴在 `oo → Oo → oO → ww → vv` 之间咀嚼，偶尔眨眼 `(-oo-)`、偶尔单眼眨 `(^oo-)`
- **符号** `sym` —— **每一帧都有**，所以永远不会只剩一张脸杵在那
- **话** `says` —— 四帧里说三帧，从当前心情的短语池按时间轮换

**眼睛**（随 `ctx` 上下文用量平滑变化）：

| ctx | 眼睛 | 状态 |
|---|---|---|
| < 35% | `^` | 充裕开心 `(^oo^)` / `(^ww^)` |
| 35%–WARN (70%) | `·` | 稳步专注 `(·oo·)` / `(·ww·)` |
| WARN–DANGER (70%–85%) | `-` | 渐感充盈 `(-oo-)` / `(-ww-)` |
| ≥ DANGER (85%) | `×` | 脑容量满载 `(×oo×)` / `(×ww×)` |

**心情**共 9 种，会话状态优先，剩下的节拍由「日常心情」轮换填满：

| 心情 | 触发 | 符号 | 短语池示例 |
|---|---|---|---|
| `alert` | 速率限额 ≥ 75% | `!!!` `! !` `!?!` | breathe, you ok? / go outside, i'll wait / hydrate maybe? |
| `fried` | ctx ≥ DANGER (85%) | `×××` `!?!` `@@@` | brain full, send help / /compact. please. / everything is soup |
| `sleepy` | ctx ≥ WARN (70%) | `zzz` `zZz` `- - -` | eyelids: heavy / /compact soon? / maybe wrap this one up |
| `rich` | 单会话花费 ≥ $1.50 | `$$$` `★★★` `$★$` | simply built different / capy has a corp card / wow. ok. luxury. |
| `cash` | 单会话花费 ≥ $0.30 | `$$$` `¢¢¢` | worth every cent / investing in ourselves / the tokens flow |
| `happy` | ctx < 35%（日常） | `♥♥♥` `✧✧✧` `♪♥♪` | you got this / chef's kiss / ship it, friend / big brain hours |
| `chill` | 日常轮换 | `♪♪♪` `. . .` `♪ ♪` | no thoughts, just grass / unbothered. moisturized. / floating along |
| `snack` | 日常轮换 | `*nom*` `*munch*` `°°°` | is that a tangerine? / one (1) melon please / grass o'clock |
| `silly` | 日常轮换 | `^_^` `:3` `owo` `>_<` | capybara.exe running / pro sitting expert / will work for melon |

- 普通状态心情（`sleepy` / `cash` / `rich`）占 3 帧里的 2 帧，剩 1 帧留给日常心情，免得看腻。
- **真·告警状态（`alert` / `fried`）独占每一帧** —— 该急的时候不会插科打诨说 "la la la~"。

例：`\(^ww^)/ ♥♥♥ proud of you`、`~(-oo-)~ zZz so sleepy`、`\(×oo×)/ !?! /compact pls`

> 想改/想加，直接编辑脚本里的 `MOODS` 表 —— 每种心情的 `pose` / `sym` / `says` 三个列表都可以随便加。
>
> 两条约定：短语控制在 **24 字符**以内 —— 话在整行最右边，是窄终端第一个截掉的东西；`pose` 和 `sym` 别用同一批字符，否则会糊成 `zZ z Z z` 这种。

### 进度条字符与宽度

上下文用量画成 `[████░░░░░░░░░░░░] 25%`，默认 16 格，后面跟一个暗色百分比；格数用 `BAR_WIDTH` 调（最小 4）。

一个得知道的坑：`█`（U+2588）的 East Asian Width 是 **Ambiguous**，而 `░`（U+2591）是 **Narrow**。把歧义字符按双宽渲染的终端上，这两个混用会让**进度条随着填满而变宽**（0% 时 18 列、100% 时 34 列），整行跟着抽，最右边的 buddy 会被挤出屏幕。

实际上 Windows Terminal、iTerm2 以及绝大多数终端默认都把歧义字符当单宽画，所以默认用回了好看的 `█` / `░`。**如果你的终端确实会抖**（常见于开了 CJK ambiguous-width 选项的终端），设一下：

```bash
BAR_CELLS="▮▯"    # U+25AE / U+25AF 都是 Narrow，任何语言环境下恒为 BAR_WIDTH 列
```

想换其它字符的话：所有实心方块（U+2588–258F、U+2592、U+2593）和框线字符（U+2500、U+2501、U+2502…）**全部**是 Ambiguous。非歧义的只剩 `░ ▪ ▫ ▬ ▮ ▯` 和 ASCII `= - #`，其中 `▮` / `▯` 是唯一同族、能拼成正经条的一对。**两个格必须是同一个宽度类别**，否则就是上面那个抖动问题。换前先验一下：

```python
import unicodedata; unicodedata.east_asian_width('▮')   # 'N' 或 'Na' 才恒宽，'A' 看终端脸色
```

同理，buddy 的符号里 `★ ♥ ♪ ° · ×` 也都是歧义宽度 —— 它们只占行尾，抖动不影响布局，所以保留了。

### 颜色档位（今日用得越多越花哨）

默认全金色。**当天累计 API 工作时长**越长，卡皮巴拉解锁的颜色层数越多 —— 干活干得多，它就越精神：

| 今日 API 时长 | 档位 | 效果 | 对应实际工作量 |
|---|:--:|---|---|
| < 5 min | 1 | 全金色 `(^oo^) ♥♥♥` | 刚开工 / 轻量调试 |
| 5 – 15 min | 2 | **符号**按心情上色（开心粉、发呆蓝、零食橙…） | 约 30m~1h 深度结对，渐入佳境 |
| 15 – 35 min | 3 | **脸和符号**各自上色（脸用淡色，符号用亮色） | 约 1.5h~3h 沉浸式编码，全情投入 |
| ≥ 35 min | 4 | **整只逐字符彩虹**，色相随秒数流动 | 全天重度 Coding / 多 Agent 狂暴输出成就 |

- 统计的是 `cost.total_api_duration_ms`，也就是**真正在跑 API 的时间**，挂着发呆不算数。
- 普通串行编码单次交互 API 耗时约 3~10 秒，因此 35 分钟 API 时长已相当于高强度工作大半天。
- 每个会话只知道自己的时长，所以要跨会话累加：状态存在 `~/.claude/statusline-buddy.json`，形如 `{"date":"2026-08-26","sessions":{"<session_id>":<ms>}}`，**每天 0 点自动重置**。
- 状态栏每次更新时若 API 时长有增长即增量同步写盘，保证换会话/退出时累计进度不丢失。
- 需要 256 色终端（Windows Terminal / iTerm2 / 绝大多数现代终端都支持）。

**可调环境变量：**

| 变量 | 作用 |
|---|---|
| `BAR_WIDTH=16` | 上下文进度条格数（默认 16，最小 4，窄终端可调小） |
| `BAR_CELLS="█░"` | 进度条的填充 / 空白字符（两个字符；终端会抖就改成 `"▮▯"`） |
| `BUDDY_TIERS="5,15,35"` | 自定义解锁档 2/3/4 的分钟阈值（默认 5m, 15m, 35m） |
| `BUDDY_TIER=4` | 强制锁定某档，用来预览效果（不写状态文件） |
| `BUDDY_NOW=<整数>` | 固定动画相位，方便逐帧调试 |

预览四个档位：

```bash
J='{"session_id":"x","model":{"display_name":"Opus 5"},"context_window":{"used_percentage":12},"cost":{"total_cost_usd":0.5}}'
for t in 1 2 3 4; do echo "$J" | BUDDY_TIER=$t node ~/.claude/statusline.js; done
```

容错设计：宠物逻辑出错时静默隐藏，绝不影响状态栏其余部分；状态文件读不到或写不进时静默退回档 1（全金），同样不影响其它内容。

---

## Available JSON Fields Reference

| Field | Description |
|---|---|
| `model.display_name` | e.g. `"Sonnet 4.6"` |
| `context_window.used_percentage` | 0–100 float |
| `cost.total_cost_usd` | Session cumulative cost USD |
| `rate_limits.five_hour.used_percentage` | 5-hour API quota % used |
| `rate_limits.five_hour.resets_at` | Unix timestamp (seconds) when 5-hour window resets |
| `rate_limits.seven_day.used_percentage` | 7-day API quota % used |
| `rate_limits.seven_day.resets_at` | Unix timestamp (seconds) when 7-day window resets |

## Debugging: Dump Raw JSON

Temporarily add to the script to see all available fields:

```python
# Python — add after sys.stdout line
import os
raw = sys.stdin.read()
with open(os.path.expanduser("~/.claude/statusline_debug.json"), "w") as f:
    f.write(raw)
data = json.loads(raw)
```

```js
// Node.js — add inside stdin 'end' handler before JSON.parse
const fs = require('fs'), os = require('os');
fs.writeFileSync(os.homedir() + '/.claude/statusline_debug.json', raw);
```

## Platform Notes

**Windows Unicode fix (Python only)** — required to prevent cp1252 encoding errors with `█` `░` `↺` `♥` `★`:
```python
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```
Safe to include on macOS too (no-op since UTF-8 is already default).

**Why not bash + jq on Windows:**
- `jq` not bundled with Git Bash — requires admin rights via Chocolatey
- Python/Node.js solve Unicode and dependency issues on both platforms
