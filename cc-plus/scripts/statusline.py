#!/usr/bin/env python3
import sys, io, json, os, time
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
h5r   = rl.get('five_hour', {}).get('resets_at')
d7r   = rl.get('seven_day', {}).get('resets_at')

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

def countdown(ts):
    if not ts: return ""
    secs = int(ts) - int(time.time())
    if secs <= 0: return f"{DIM}↺now{R}"
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d > 0: return f"{DIM}↺{d}d{h}h{R}"
    if h > 0: return f"{DIM}↺{h}h{m}m{R}"
    return f"{DIM}↺{m}m{R}"

ctx = (f"[{bar(used)}] {DIM}{round(used)}%{R}" if used is not None
       else f"[{DIM}{'░' * W}{R}]")

cost_str = f"  {DIM}${cost:.3f}{R}" if cost is not None else ""

rl_parts = []
if h5 is not None: rl_parts.append(f"{DIM}5h:{R}{col(h5)}{round(h5)}%{R}{countdown(h5r)}")
if d7 is not None: rl_parts.append(f"{DIM}7d:{R}{col(d7)}{round(d7)}%{R}{countdown(d7r)}")
rl_str = ("  " + "  ".join(rl_parts)) if rl_parts else ""

print(f"{CYAN}{BOLD}{model}{R}  {DIM}ctx{R} {ctx}{cost_str}{rl_str}")
