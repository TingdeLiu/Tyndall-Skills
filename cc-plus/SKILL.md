---
name: cc-plus
description: Set up a Claude Code custom status line AND completion notification sound on Windows or macOS. Use when configuring statusLine in settings.json, when bash/jq/Unicode errors occur, or when the user wants a sound alert when Claude finishes a response. Auto-detects OS and Python vs Node.js runtime.
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
- 80% 警告 / 95% 危险 (Recommended)
- 70% 警告 / 90% 危险
- 60% 警告 / 85% 危险

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
Sonnet 4.6  ctx [████░░░░░░░░░░░░] 25%  $0.050  5h:10%  7d:30%
```

Color coding (using chosen thresholds):
- Green — below warn threshold
- Yellow — warn to danger
- Red — at or above danger threshold

---

## Available JSON Fields Reference

| Field | Description |
|---|---|
| `model.display_name` | e.g. `"Sonnet 4.6"` |
| `context_window.used_percentage` | 0–100 float |
| `cost.total_cost_usd` | Session cumulative cost USD |
| `rate_limits.five_hour.used_percentage` | 5-hour API quota % used |
| `rate_limits.seven_day.used_percentage` | 7-day API quota % used |

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

**Windows Unicode fix (Python only)** — required to prevent cp1252 encoding errors with `█` `░`:
```python
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```
Safe to include on macOS too (no-op since UTF-8 is already default).

**Why not bash + jq on Windows:**
- `jq` not bundled with Git Bash — requires admin rights via Chocolatey
- Python/Node.js solve Unicode and dependency issues on both platforms
