---
name: windows-statusline
description: Set up a Claude Code custom status line on Windows. Use when the user wants to configure statusLine in settings.json on Windows, especially when bash/jq-based scripts fail due to missing jq or Unicode encoding errors. Provides a ready-to-use Python script showing model name, context usage bar (color-coded), session cost in USD, and 5h/7d rate limit percentages.
---

# Windows Status Line Setup

## Quick Setup

1. Copy `scripts/statusline.py` to `C:/Users/<username>/.claude/statusline.py`
2. Add to `C:/Users/<username>/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "python C:/Users/<username>/.claude/statusline.py"
}
```

Output looks like:
```
Sonnet 4.6  ctx [████░░░░░░░░░░░░] 25%  $0.123  5h:6%  7d:56%
```

## Why Not bash + jq on Windows

- `jq` is not bundled with Git Bash — requires admin rights to install via Chocolatey
- Block characters (`█` `░`) cause `UnicodeEncodeError` in Python's default cp1252 encoding
- Python (Miniconda or system) is reliably available and solves both problems

## Windows Unicode Fix

Any Python statusline script must include this at the top:

```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

## Available JSON Fields

Claude Code pipes a JSON object to the statusline command on each response. Key fields:

| Field | Description |
|---|---|
| `model.display_name` | e.g. `"Sonnet 4.6"` |
| `context_window.used_percentage` | 0–100 float |
| `cost.total_cost_usd` | Session cumulative cost in USD |
| `rate_limits.five_hour.used_percentage` | 5-hour API quota % used |
| `rate_limits.seven_day.used_percentage` | 7-day API quota % used |

## Debugging Available Fields

To discover all fields, temporarily dump the raw input to a file:

```python
raw = sys.stdin.read()
with open("C:/Users/<username>/.claude/statusline_debug.json", "w") as f:
    f.write(raw)
data = json.loads(raw)
```

Send any message, then read the debug file to see the complete JSON structure.
