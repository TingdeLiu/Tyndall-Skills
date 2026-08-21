#!/usr/bin/env python3
import sys, io, json, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WARN   = int(os.environ.get('WARN_PCT',   '80'))
DANGER = int(os.environ.get('DANGER_PCT', '95'))

data = json.loads(sys.stdin.read())

model  = data.get('model', {}).get('display_name', 'Claude')
used   = data.get('context_window', {}).get('used_percentage')
cost   = data.get('cost', {}).get('total_cost_usd')
api_ms = data.get('cost', {}).get('total_api_duration_ms')
sid    = data.get('session_id')
rl     = data.get('rate_limits', {})
h5     = rl.get('five_hour', {}).get('used_percentage')
d7     = rl.get('seven_day', {}).get('used_percentage')
h5r    = rl.get('five_hour', {}).get('resets_at')
d7r    = rl.get('seven_day', {}).get('resets_at')

R     = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
CYAN  = "\033[36m"
GREEN = "\033[32m"
YELL  = "\033[33m"
RED   = "\033[31m"

def col(p):
    return GREEN if p < WARN else (YELL if p < DANGER else RED)

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

# ---- daily streak: today's API working time unlocks the buddy's colour tiers ----
# Sessions each report only their own `total_api_duration_ms`, so we accumulate
# them in a small file to get a per-day total. Idle time never counts — this is
# API time, i.e. how much work actually got done today.
STATE = os.path.join(os.path.expanduser('~'), '.claude', 'statusline-buddy.json')
try:  # minutes that unlock tiers 2 / 3 / 4
    TIERS = [float(x) for x in os.environ.get('BUDDY_TIERS', '60,240,480').split(',')]
except Exception:
    TIERS = [60.0, 240.0, 480.0]

def daily_tier(session_id, ms):
    forced = os.environ.get('BUDDY_TIER')     # for previewing the tiers
    if forced:
        return max(1, min(4, int(forced)))
    if not session_id or ms is None:
        return 1
    today = time.strftime('%Y-%m-%d')
    try:
        with open(STATE, encoding='utf-8') as f:
            st = json.load(f)
    except Exception:
        st = {}
    if st.get('date') != today:                # new day, start the count over
        st = {'date': today, 'sessions': {}}
    sess = st.setdefault('sessions', {})
    prev = sess.get(session_id, 0)
    sess[session_id] = max(prev, ms)
    # The status bar re-renders several times a second, so only touch the disk
    # once this session has moved by 5s+ of API time.
    if ms - prev >= 5000:
        try:
            tmp = STATE + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(st, f)
            os.replace(tmp, STATE)
        except Exception:
            pass
    minutes = sum(sess.values()) / 60000.0
    return 1 + sum(1 for t in TIERS if minutes >= t)

# ---- buddy: a living golden capybara (Claude Code easter-egg port) ----
# It never just sits there. The wall clock drives the idle animation (chewing,
# blinking, the odd wink and wave); your session state picks the mood, and the
# mood decides both the little symbol it trails and the thing it says.
GOLD = "\033[93m"

# The critter's entire vocabulary lives here — edit freely.
#   pose : (left, right) limbs wrapped around the face — \ / paws, ~ ~ water
#   sym  : symbol cluster that ALWAYS trails the face, so it's never bare
#   says : the dim one-liners — keep under ~24 chars; the quip sits at the far
#          right, so it is the first thing a narrow terminal truncates
# Keep pose and sym on different characters, or you get muddle like "zZ z Z z".
MOODS = {
    'happy': {
        'pose': [("", ""), ("\\", "/"), ("", "/")],
        'sym':  ["♥♥♥", "✧✧✧", "♪♥♪", "♥ ♥"],
        'says': ["you got this", "we're vibing", "proud of you",
                 "look at you go", "chef's kiss", "ship it, friend",
                 "big brain hours", "cozy lil day", "good company",
                 "that one was clean"],
    },
    'chill': {
        'pose': [("", ""), ("~", "~")],
        'sym':  ["♪♪♪", ". . .", "♪ ♪"],
        'says': ["la la la~", "just chillin'", "doot doot doot",
                 "no thoughts, just grass", "the water's nice",
                 "floating along", "unbothered. moisturized.",
                 "zero urgency detected", "capy time is slow time",
                 "hmm hmm hmm"],
    },
    'snack': {
        'pose': [("", ""), ("", "/")],
        'sym':  ["*nom*", "°°°", "*munch*", "~*~"],
        'says': ["is that a tangerine?", "grass o'clock", "nom nom nom",
                 "saving you a snack", "one (1) melon please",
                 "chewing on it", "snack break, brb"],
    },
    'silly': {
        'pose': [("", ""), ("", "?"), ("\\", "/")],
        'sym':  ["^_^", ":3", "owo", ">_<"],
        'says': ["capybara.exe running", "i am but a small rodent",
                 "pro sitting expert", "friend to all",
                 "will work for melon", "largest rodent believes",
                 "just vibing, no notes"],
    },
    'sleepy': {
        'pose': [("", ""), ("~", "~")],
        'sym':  ["zzz", "z Z z", "zZz", "- - -"],
        'says': ["5 more minutes", "so very sleepy", "eyelids: heavy",
                 "context's getting cozy", "ok... carry on",
                 "/compact soon?", "maybe wrap this one up",
                 "running low, gently"],
    },
    'fried': {
        'pose': [("", ""), ("\\", "/")],
        'sym':  ["×××", "!?!", "@@@"],
        'says': ["brain full, send help", "no room left up here",
                 "/compact. please.", "everything is soup",
                 "we are at the brim", "screaming politely"],
    },
    'cash': {
        'pose': [("", ""), ("", "/")],
        'sym':  ["$$$", "$ $ $", "¢¢¢"],
        'says': ["worth every cent", "treat yourself", "money well spent",
                 "ooh, fancy", "investing in ourselves", "the tokens flow"],
    },
    'rich': {
        'pose': [("", ""), ("\\", "/")],
        'sym':  ["$$$", "★★★", "$★$"],
        'says': ["simply built different", "hope it's billable",
                 "capy has a corp card", "wow. ok. luxury.",
                 "no notes, just invoices"],
    },
    'alert': {
        'pose': [("", ""), ("\\", "/")],
        'sym':  ["!!!", "! !", "!?!"],
        'says': ["breathe, you ok?", "ease up soon", "take a lil break",
                 "pace yourself", "go outside, i'll wait",
                 "the limit approaches", "hydrate maybe?"],
    },
}

# 256-colour (face, symbol) pair per mood — face is the pale shade, symbol the
# vivid one. Tier 2 lights up the symbol, tier 3 the face as well.
PALETTE = {
    'happy':  (223, 211), 'chill':  (152, 117), 'snack': (223, 215),
    'silly':  (183, 141), 'sleepy': (146, 103), 'fried': (217, 203),
    'cash':   (157, 149), 'rich':   (229, 220), 'alert': (217, 196),
}
# tier 4: hue ramp for the per-character rainbow, scrolled by the wall clock
RAINBOW = [196, 202, 208, 214, 220, 226, 190, 154, 118, 82, 46, 47, 48, 49, 50,
           51, 45, 39, 33, 27, 21, 57, 93, 129, 165, 201, 200, 199, 198, 197]

def c256(n):
    return f"\033[38;5;{n}m"

def rainbow(text, phase):
    return "".join(c256(RAINBOW[(i + phase) % len(RAINBOW)]) + ch
                   for i, ch in enumerate(text))

def buddy(used, cost, h5, d7, tier):
    # phase advances with wall-clock; each status-bar refresh samples a new beat
    phase = int(os.environ.get('BUDDY_NOW') or time.time())

    # eyes — mood from context usage, plus blinks and the occasional wink
    if used is None:        eye = '·'
    elif used >= DANGER:    eye = '×'      # cross-eyed, fried
    elif used >= WARN:      eye = '-'      # tired, half-lidded
    elif used >= 50:        eye = '·'      # awake
    else:                   eye = '^'      # happy, ctx still roomy
    l_eye = r_eye = eye
    if eye in ('·', '^'):
        if   phase % 7  == 0: l_eye = r_eye = '-'   # blink
        elif phase % 11 == 0: r_eye = '-'           # wink

    # mouth — slow chewing / idle cycle, with the odd little smile
    mouth = ['oo', 'Oo', 'oO', 'oo', 'ww', 'oo', 'vv', 'oo'][phase % 8]

    # mood — session state wins most beats, fillers rotate through the rest
    rl = max(h5 or 0, d7 or 0)
    state = None
    if   rl >= 90:                             state = 'alert'
    elif used is not None and used >= DANGER:  state = 'fried'
    elif used is not None and used >= WARN:    state = 'sleepy'
    elif (cost or 0) >= 5:                     state = 'rich'
    elif (cost or 0) >= 1:                     state = 'cash'

    fillers = ['chill', 'snack', 'silly']
    if used is None or used < 50:
        fillers.insert(0, 'happy')
    # a live state mood owns 2 beats in 3, so fillers keep it from getting samey —
    # but when something is actually wrong it stays on message every beat
    urgent = state in ('alert', 'fried')
    mood = (state if (state and (urgent or phase % 3))
            else fillers[(phase // 3) % len(fillers)])
    m = MOODS[mood]

    # coprime-ish strides so pose / symbol / quip never march in lockstep
    l, r = m['pose'][(phase // 4) % len(m['pose'])]
    sym  = m['sym'][(phase // 3) % len(m['sym'])]
    say  = m['says'][(phase // 5) % len(m['says'])]

    face  = f"{l}({l_eye}{mouth}{r_eye}){r}"
    talks = phase % 4 != 3                  # it talks 3 beats out of 4

    if tier >= 4:                           # whole critter goes rainbow, and flows
        text = f"{face} {sym}" + (f" {say}" if talks else "")
        return BOLD + rainbow(text, phase) + R

    fc, sc = PALETTE.get(mood, (None, None))
    face_col = c256(fc) if tier >= 3 and fc else GOLD
    sym_col  = c256(sc) if tier >= 2 and sc else GOLD
    out = f"{BOLD}{face_col}{face}{R} {BOLD}{sym_col}{sym}{R}"
    if talks:
        out += f" {DIM}{say}{R}"
    return out

# No progress bar: it cost 12-34 columns depending on locale and fill, and the
# quip at the far right is what got truncated to pay for it. The percentage
# carries the same signal in 3 columns, colour-coded by the same thresholds.
ctx = f"{col(used)}{round(used)}%{R}" if used is not None else f"{DIM}--{R}"

cost_str = f"  {DIM}${cost:.3f}{R}" if cost is not None else ""

rl_parts = []
if h5 is not None: rl_parts.append(f"{DIM}5h:{R}{col(h5)}{round(h5)}%{R}{countdown(h5r)}")
if d7 is not None: rl_parts.append(f"{DIM}7d:{R}{col(d7)}{round(d7)}%{R}{countdown(d7r)}")
rl_str = ("  " + "  ".join(rl_parts)) if rl_parts else ""

try:
    tier = daily_tier(sid, api_ms)
except Exception:
    tier = 1
try:
    buddy_str = "  " + buddy(used, cost, h5, d7, tier)
except Exception:
    buddy_str = ""

print(f"{CYAN}{BOLD}{model}{R}  {DIM}ctx{R} {ctx}{cost_str}{rl_str}{buddy_str}")
