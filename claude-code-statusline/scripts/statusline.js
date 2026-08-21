#!/usr/bin/env node
const os = require('os'), fs = require('fs'), path = require('path');

const WARN   = parseInt(process.env.WARN_PCT   || '80', 10);
const DANGER = parseInt(process.env.DANGER_PCT || '95', 10);

let raw = '';
process.stdin.setEncoding('utf-8');
process.stdin.on('data', c => raw += c);
process.stdin.on('end', () => {
  const data = JSON.parse(raw.replace(/^﻿/, ''));

  const model  = (data.model || {}).display_name || 'Claude';
  const used   = (data.context_window || {}).used_percentage;
  const cost   = (data.cost || {}).total_cost_usd;
  const apiMs  = (data.cost || {}).total_api_duration_ms;
  const sid    = data.session_id;
  const rl     = data.rate_limits || {};
  const h5     = (rl.five_hour  || {}).used_percentage;
  const d7     = (rl.seven_day  || {}).used_percentage;
  const h5r    = (rl.five_hour  || {}).resets_at;
  const d7r    = (rl.seven_day  || {}).resets_at;

  const R = '\x1b[0m', BOLD = '\x1b[1m', DIM = '\x1b[2m';
  const CYAN = '\x1b[36m', GREEN = '\x1b[32m', YELLOW = '\x1b[33m', RED = '\x1b[31m';
  const W = 16;

  const col = p => p < WARN ? GREEN : p < DANGER ? YELLOW : RED;

  const bar = p => {
    const f = Math.min(W, (p * W / 100) | 0);
    return col(p) + '█'.repeat(f) + DIM + '░'.repeat(W - f) + R;
  };

  const countdown = ts => {
    if (!ts) return '';
    const secs = ts - Math.floor(Date.now() / 1000);
    if (secs <= 0) return ` ${DIM}↺:${YELLOW}now${R}`;
    const d = (secs / 86400) | 0;
    const h = ((secs % 86400) / 3600) | 0;
    const m = ((secs % 3600) / 60) | 0;
    if (d > 0) return ` ${DIM}↺:${YELLOW}${d}d${h}h${R}`;
    if (h > 0) return ` ${DIM}↺:${YELLOW}${h}h${m}m${R}`;
    return ` ${DIM}↺:${YELLOW}${m}m${R}`;
  };

  // ---- daily streak: today's API working time unlocks the buddy's colour tiers ----
  // Sessions each report only their own `total_api_duration_ms`, so we accumulate
  // them in a small file to get a per-day total. Idle time never counts — this is
  // API time, i.e. how much work actually got done today.
  const STATE = path.join(os.homedir(), '.claude', 'statusline-buddy.json');
  let TIERS;                                  // minutes that unlock tiers 2 / 3 / 4
  try {
    TIERS = (process.env.BUDDY_TIERS || '60,240,480').split(',').map(Number);
    if (TIERS.some(isNaN)) throw new Error('bad');
  } catch (e) { TIERS = [60, 240, 480]; }

  const dailyTier = (sessionId, ms) => {
    const forced = process.env.BUDDY_TIER;    // for previewing the tiers
    if (forced) return Math.max(1, Math.min(4, parseInt(forced, 10)));
    if (!sessionId || ms == null) return 1;
    const d = new Date();
    const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    let st = {};
    try { st = JSON.parse(fs.readFileSync(STATE, 'utf-8')); } catch (e) { st = {}; }
    if (st.date !== today) st = { date: today, sessions: {} };  // new day, start over
    if (!st.sessions) st.sessions = {};
    const prev = st.sessions[sessionId] || 0;
    st.sessions[sessionId] = Math.max(prev, ms);
    // The status bar re-renders several times a second, so only touch the disk
    // once this session has moved by 5s+ of API time.
    if (ms - prev >= 5000) {
      try {
        fs.writeFileSync(STATE + '.tmp', JSON.stringify(st));
        fs.renameSync(STATE + '.tmp', STATE);
      } catch (e) {}
    }
    const minutes = Object.values(st.sessions).reduce((a, b) => a + b, 0) / 60000;
    return 1 + TIERS.filter(t => minutes >= t).length;
  };

  // ---- buddy: a living golden capybara (Claude Code easter-egg port) ----
  // It never just sits there. The wall clock drives the idle animation (chewing,
  // blinking, the odd wink and wave); your session state picks the mood, and the
  // mood decides both the little symbol it trails and the thing it says.
  const GOLD = '\x1b[93m';

  // The critter's entire vocabulary lives here — edit freely.
  //   pose : [left, right] limbs wrapped around the face — \ / paws, ~ ~ water
  //   sym  : symbol cluster that ALWAYS trails the face, so it's never bare
  //   says : the dim one-liners — keep under ~24 chars so the bar won't wrap
  // Keep pose and sym on different characters, or you get muddle like "zZ z Z z".
  const MOODS = {
    happy: {
      pose: [['', ''], ['\\', '/'], ['', '/']],
      sym:  ["♥♥♥", "✧✧✧", "♪♥♪", "♥ ♥"],
      says: ["you got this", "we're vibing", "proud of you",
             "look at you go", "chef's kiss", "ship it, friend",
             "big brain hours", "cozy lil day", "good company",
             "that one was clean"],
    },
    chill: {
      pose: [['', ''], ['~', '~']],
      sym:  ["♪♪♪", ". . .", "♪ ♪"],
      says: ["la la la~", "just chillin'", "doot doot doot",
             "no thoughts, just grass", "the water's nice",
             "floating along", "unbothered. moisturized.",
             "zero urgency detected", "capy time is slow time",
             "hmm hmm hmm"],
    },
    snack: {
      pose: [['', ''], ['', '/']],
      sym:  ["*nom*", "°°°", "*munch*", "~*~"],
      says: ["is that a tangerine?", "grass o'clock", "nom nom nom",
             "saving you a snack", "one (1) melon please",
             "chewing on it", "snack break, brb"],
    },
    silly: {
      pose: [['', ''], ['', '?'], ['\\', '/']],
      sym:  ["^_^", ":3", "owo", ">_<"],
      says: ["capybara.exe running", "i am but a small rodent",
             "pro sitting expert", "friend to all",
             "will work for melon", "largest rodent believes",
             "just vibing, no notes"],
    },
    sleepy: {
      pose: [['', ''], ['~', '~']],
      sym:  ["zzz", "z Z z", "zZz", "- - -"],
      says: ["5 more minutes", "so very sleepy", "eyelids: heavy",
             "context's getting cozy", "ok... carry on",
             "/compact soon?", "maybe wrap this one up",
             "running low, gently"],
    },
    fried: {
      pose: [['', ''], ['\\', '/']],
      sym:  ["×××", "!?!", "@@@"],
      says: ["brain full, send help", "no room left up here",
             "/compact. please.", "everything is soup",
             "we are at the brim", "screaming politely"],
    },
    cash: {
      pose: [['', ''], ['', '/']],
      sym:  ["$$$", "$ $ $", "¢¢¢"],
      says: ["worth every cent", "treat yourself", "money well spent",
             "ooh, fancy", "investing in ourselves", "the tokens flow"],
    },
    rich: {
      pose: [['', ''], ['\\', '/']],
      sym:  ["$$$", "★★★", "$★$"],
      says: ["simply built different", "hope it's billable",
             "capy has a corp card", "wow. ok. luxury.",
             "no notes, just invoices"],
    },
    alert: {
      pose: [['', ''], ['\\', '/']],
      sym:  ["!!!", "! !", "!?!"],
      says: ["breathe, you ok?", "ease up soon", "take a lil break",
             "pace yourself", "go outside, i'll wait",
             "the limit approaches", "hydrate maybe?"],
    },
  };

  // 256-colour [face, symbol] pair per mood — face is the pale shade, symbol the
  // vivid one. Tier 2 lights up the symbol, tier 3 the face as well.
  const PALETTE = {
    happy:  [223, 211], chill:  [152, 117], snack: [223, 215],
    silly:  [183, 141], sleepy: [146, 103], fried: [217, 203],
    cash:   [157, 149], rich:   [229, 220], alert: [217, 196],
  };
  // tier 4: hue ramp for the per-character rainbow, scrolled by the wall clock
  const RAINBOW = [196, 202, 208, 214, 220, 226, 190, 154, 118, 82, 46, 47, 48, 49, 50,
                   51, 45, 39, 33, 27, 21, 57, 93, 129, 165, 201, 200, 199, 198, 197];

  const c256 = n => `\x1b[38;5;${n}m`;

  const rainbow = (text, phase) => [...text]
    .map((ch, i) => c256(RAINBOW[(i + phase) % RAINBOW.length]) + ch)
    .join('');

  const buddy = (tier) => {
    // phase advances with wall-clock; each status-bar refresh samples a new beat
    const env = process.env.BUDDY_NOW;
    const phase = env ? parseInt(env, 10) : Math.floor(Date.now() / 1000);

    // eyes — mood from context usage, plus blinks and the occasional wink
    let eye;
    if (used == null)        eye = '·';
    else if (used >= DANGER) eye = '×';   // cross-eyed, fried
    else if (used >= WARN)   eye = '-';   // tired, half-lidded
    else if (used >= 50)     eye = '·';   // awake
    else                     eye = '^';   // happy, ctx still roomy
    let lEye = eye, rEye = eye;
    if (eye === '·' || eye === '^') {
      if      (phase % 7  === 0) { lEye = rEye = '-'; }   // blink
      else if (phase % 11 === 0) { rEye = '-'; }          // wink
    }

    // mouth — slow chewing / idle cycle, with the odd little smile
    const mouth = ['oo', 'Oo', 'oO', 'oo', 'ww', 'oo', 'vv', 'oo'][phase % 8];

    // mood — session state wins most beats, fillers rotate through the rest
    const lim = Math.max(h5 || 0, d7 || 0);
    let state = null;
    if      (lim >= 90)                        state = 'alert';
    else if (used != null && used >= DANGER)   state = 'fried';
    else if (used != null && used >= WARN)     state = 'sleepy';
    else if ((cost || 0) >= 5)                 state = 'rich';
    else if ((cost || 0) >= 1)                 state = 'cash';

    const fillers = ['chill', 'snack', 'silly'];
    if (used == null || used < 50) fillers.unshift('happy');
    // a live state mood owns 2 beats in 3, so fillers keep it from getting samey —
    // but when something is actually wrong it stays on message every beat
    const urgent = state === 'alert' || state === 'fried';
    const mood = (state && (urgent || phase % 3))
      ? state
      : fillers[Math.floor(phase / 3) % fillers.length];
    const m = MOODS[mood];

    // coprime-ish strides so pose / symbol / quip never march in lockstep
    const [l, r] = m.pose[Math.floor(phase / 4) % m.pose.length];
    const sym    = m.sym[Math.floor(phase / 3) % m.sym.length];
    const say    = m.says[Math.floor(phase / 5) % m.says.length];

    const face  = `${l}(${lEye}${mouth}${rEye})${r}`;
    const talks = phase % 4 !== 3;          // it talks 3 beats out of 4

    if (tier >= 4) {                        // whole critter goes rainbow, and flows
      const text = `${face} ${sym}` + (talks ? ` ${say}` : '');
      return BOLD + rainbow(text, phase) + R;
    }

    const [fc, sc] = PALETTE[mood] || [null, null];
    const faceCol = (tier >= 3 && fc) ? c256(fc) : GOLD;
    const symCol  = (tier >= 2 && sc) ? c256(sc) : GOLD;
    let out = `${BOLD}${faceCol}${face}${R} ${BOLD}${symCol}${sym}${R}`;
    if (talks) out += ` ${DIM}${say}${R}`;
    return out;
  };

  const ctx = used != null
    ? `[${bar(used)}] ${DIM}${Math.round(used)}%${R}`
    : `[${DIM}${'░'.repeat(W)}${R}]`;

  const costStr = cost != null ? `  ${DIM}$${cost.toFixed(3)}${R}` : '';

  const rlParts = [];
  if (h5 != null) rlParts.push(`${DIM}5h:${R}${col(h5)}${Math.round(h5)}%${R}${countdown(h5r)}`);
  if (d7 != null) rlParts.push(`${DIM}7d:${R}${col(d7)}${Math.round(d7)}%${R}${countdown(d7r)}`);
  const rlStr = rlParts.length ? '  ' + rlParts.join('  ') : '';

  let tier = 1;
  try { tier = dailyTier(sid, apiMs); } catch (e) {}
  let buddyStr = '';
  try { buddyStr = '  ' + buddy(tier); } catch (e) {}

  process.stdout.write(`${CYAN}${BOLD}${model}${R}  ${DIM}ctx${R} ${ctx}${costStr}${rlStr}${buddyStr}\n`);
});
