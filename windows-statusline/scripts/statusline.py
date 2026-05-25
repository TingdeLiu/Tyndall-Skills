#!/usr/bin/env python3
import sys
import json
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

data = json.loads(sys.stdin.read())

model   = data.get('model', {}).get('display_name', 'Claude')
used    = data.get('context_window', {}).get('used_percentage')
cost    = data.get('cost', {}).get('total_cost_usd')
rl      = data.get('rate_limits', {})
h5      = rl.get('five_hour', {}).get('used_percentage')
d7      = rl.get('seven_day', {}).get('used_percentage')

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
DIM    = "\033[2m"

BAR_WIDTH = 16

def color_pct(pct):
    if pct < 50:   return GREEN
    if pct < 80:   return YELLOW
    return RED

def make_bar(pct):
    filled = round(pct) * BAR_WIDTH // 100
    empty  = BAR_WIDTH - filled
    col    = color_pct(pct)
    return col + "█" * filled + DIM + "░" * empty + RESET

# Context bar
if used is not None:
    bar = make_bar(used)
    ctx = f"[{bar}] {DIM}{round(used)}%{RESET}"
else:
    ctx = f"[{DIM}{'░' * BAR_WIDTH}{RESET}]"

# Cost
cost_str = f"  {DIM}${cost:.3f}{RESET}" if cost is not None else ""

# Rate limits
rl_parts = []
if h5 is not None:
    col = color_pct(h5)
    rl_parts.append(f"{DIM}5h:{RESET}{col}{round(h5)}%{RESET}")
if d7 is not None:
    col = color_pct(d7)
    rl_parts.append(f"{DIM}7d:{RESET}{col}{round(d7)}%{RESET}")
rl_str = ("  " + "  ".join(rl_parts)) if rl_parts else ""

print(f"{CYAN}{BOLD}{model}{RESET}  {DIM}ctx{RESET} {ctx}{cost_str}{rl_str}")
