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
    if secs <= 0: return f" {DIM}↺:{YELL}now{R}"
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d > 0: return f" {DIM}↺:{YELL}{d}d{h}h{R}"
    if h > 0: return f" {DIM}↺:{YELL}{h}h{m}m{R}"
    return f" {DIM}↺:{YELL}{m}m{R}"

# ---- buddy: a living golden capybara (Claude Code easter-egg port) ----
# Single line, but it fidgets between refreshes: time drives idle animation,
# session state drives mood + the occasional emote. No words — just the critter.
GOLD = "\033[93m"

# capybara is the chillest animal alive — keep the quips warm, calm, a little silly
QUIPS = {
    'happy':   ["you got this", "we're vibing", "cozy lil day", "proud of you", "good company"],
    'humming': ["la la la~", "just chillin'", "doot doot doot", "hmm hmm hmm"],
    'sleepy':  ["5 more minutes", "context's cozy", "so very sleepy", "ok... carry on"],
    'cash':    ["worth every cent", "treat yourself", "money well spent", "ooh, fancy"],
    'alert':   ["breathe, you ok?", "ease up soon", "take a lil break", "pace yourself"],
}

def buddy(used, cost, h5, d7):
    # phase advances with wall-clock; each status-bar refresh samples a new beat
    phase = int(os.environ.get('BUDDY_NOW') or time.time())

    # eyes — mood from context usage
    if used is None:        eye = '·'
    elif used >= DANGER:    eye = '×'      # cross-eyed, exhausted
    elif used >= WARN:      eye = '-'      # tired, half-lidded
    elif used >= 50:        eye = '·'      # awake
    else:                   eye = '^'      # happy, ctx still roomy
    # blink every so often (only when not already squinting)
    if eye in ('·', '^') and phase % 7 == 0:
        eye = '-'

    # mouth — slow chewing / idle cycle
    mouth = ['oo', 'Oo', 'oO', 'oo'][phase % 4]

    # emote — a small reaction floats out now and then, picked by state
    rl   = max(h5 or 0, d7 or 0)
    slot = phase % 12
    kind = sym = None
    if   rl >= 90 and slot in (0, 1):                     kind, sym = 'alert', '!!!'
    elif (cost or 0) >= 1 and slot == 3:                  kind, sym = 'cash', '$$$'
    elif used is not None and used >= WARN and slot == 5: kind, sym = 'sleepy', 'zzz'
    elif (used is None or used < 50) and slot == 8:       kind, sym = 'happy', '♥♥♥'
    elif slot == 10:                                      kind, sym = 'humming', '~~~'
    emote = ''
    if kind:
        pool  = QUIPS[kind]
        emote = f" {sym} {DIM}{pool[(phase // 12) % len(pool)]}{R}{GOLD}{BOLD}"

    return GOLD + BOLD + f"({eye}{mouth}{eye})" + emote + R

ctx = (f"[{bar(used)}] {DIM}{round(used)}%{R}" if used is not None
       else f"[{DIM}{'░' * W}{R}]")

cost_str = f"  {DIM}${cost:.3f}{R}" if cost is not None else ""

rl_parts = []
if h5 is not None: rl_parts.append(f"{DIM}5h:{R}{col(h5)}{round(h5)}%{R}{countdown(h5r)}")
if d7 is not None: rl_parts.append(f"{DIM}7d:{R}{col(d7)}{round(d7)}%{R}{countdown(d7r)}")
rl_str = ("  " + "  ".join(rl_parts)) if rl_parts else ""

try:
    buddy_str = "  " + buddy(used, cost, h5, d7)
except Exception:
    buddy_str = ""

print(f"{CYAN}{BOLD}{model}{R}  {DIM}ctx{R} {ctx}{cost_str}{rl_str}{buddy_str}")
