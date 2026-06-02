#!/usr/bin/env python3
# Thresholds: override via env vars WARN_PCT and DANGER_PCT
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WARN   = int(os.environ.get('WARN_PCT',   '80'))
DANGER = int(os.environ.get('DANGER_PCT', '95'))

data = json.loads(sys.stdin.read())

model = data.get('model', {}).get('display_name', 'Claude')
used  = data.get('context_window', {}).get('used_percentage')
cost  = data.get('cost', {}).get('total_cost_usd')
rl    = data.get('rate_limits', {})
h5    = rl.get('five_hour', {}).get('used_percentage')
d7    = rl.get('seven_day', {}).get('used_percentage')

R     = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
CYAN  = "\033[36m"
GREEN = "\033[32m"
YELL  = "\033[33m"
RED   = "\033[31m"
W = 16

def col(p):
    return GREEN if p < WARN else (YELL if p < DANGER else RED)

def bar(p):
    f = min(W, round(p) * W // 100)
    return col(p) + "█" * f + DIM + "░" * (W - f) + R

ctx = (f"[{bar(used)}] {DIM}{round(used)}%{R}" if used is not None
       else f"[{DIM}{'░' * W}{R}]")

cost_str = f"  {DIM}${cost:.3f}{R}" if cost is not None else ""

rl_parts = []
if h5 is not None: rl_parts.append(f"{DIM}5h:{R}{col(h5)}{round(h5)}%{R}")
if d7 is not None: rl_parts.append(f"{DIM}7d:{R}{col(d7)}{round(d7)}%{R}")
rl_str = ("  " + "  ".join(rl_parts)) if rl_parts else ""

print(f"{CYAN}{BOLD}{model}{R}  {DIM}ctx{R} {ctx}{cost_str}{rl_str}")
