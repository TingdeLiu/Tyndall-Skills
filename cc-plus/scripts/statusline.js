#!/usr/bin/env node
const WARN   = parseInt(process.env.WARN_PCT   || '80', 10);
const DANGER = parseInt(process.env.DANGER_PCT || '95', 10);

let raw = '';
process.stdin.setEncoding('utf-8');
process.stdin.on('data', c => raw += c);
process.stdin.on('end', () => {
  const data = JSON.parse(raw.replace(/^﻿/, ''));

  const model = (data.model || {}).display_name || 'Claude';
  const used  = (data.context_window || {}).used_percentage;
  const cost  = (data.cost || {}).total_cost_usd;
  const rl    = data.rate_limits || {};
  const h5    = (rl.five_hour  || {}).used_percentage;
  const d7    = (rl.seven_day  || {}).used_percentage;
  const h5r   = (rl.five_hour  || {}).resets_at;
  const d7r   = (rl.seven_day  || {}).resets_at;

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

  // ---- buddy: a living golden capybara (Claude Code easter-egg port) ----
  // Single line, but it fidgets between refreshes: time drives idle animation,
  // session state drives mood + the occasional emote. No words — just the critter.
  const GOLD = '\x1b[93m';
  // capybara is the chillest animal alive — keep the quips warm, calm, a little silly
  const QUIPS = {
    happy:   ["you got this", "we're vibing", "cozy lil day", "proud of you", "good company"],
    humming: ["la la la~", "just chillin'", "doot doot doot", "hmm hmm hmm"],
    sleepy:  ["5 more minutes", "context's cozy", "so very sleepy", "ok... carry on"],
    cash:    ["worth every cent", "treat yourself", "money well spent", "ooh, fancy"],
    alert:   ["breathe, you ok?", "ease up soon", "take a lil break", "pace yourself"],
  };
  const buddy = () => {
    const env = process.env.BUDDY_NOW;
    const phase = env ? parseInt(env, 10) : Math.floor(Date.now() / 1000);

    // eyes — mood from context usage
    let eye;
    if (used == null)       eye = '·';
    else if (used >= DANGER) eye = '×';   // cross-eyed, exhausted
    else if (used >= WARN)   eye = '-';   // tired, half-lidded
    else if (used >= 50)     eye = '·';   // awake
    else                     eye = '^';   // happy, ctx still roomy
    if ((eye === '·' || eye === '^') && phase % 7 === 0) eye = '-';  // blink

    // mouth — slow chewing / idle cycle
    const mouth = ['oo', 'Oo', 'oO', 'oo'][phase % 4];

    // emote — a small reaction floats out now and then, picked by state
    const rl = Math.max(h5 || 0, d7 || 0);
    const slot = phase % 12;
    let kind = null, sym = null;
    if      (rl >= 90 && (slot === 0 || slot === 1))           { kind = 'alert';   sym = '!!!'; }
    else if ((cost || 0) >= 1 && slot === 3)                   { kind = 'cash';    sym = '$$$'; }
    else if (used != null && used >= WARN && slot === 5)       { kind = 'sleepy';  sym = 'zzz'; }
    else if ((used == null || used < 50) && slot === 8)        { kind = 'happy';   sym = '♥♥♥'; }
    else if (slot === 10)                                      { kind = 'humming'; sym = '~~~'; }
    let emote = '';
    if (kind) {
      const pool = QUIPS[kind];
      emote = ` ${sym} ${DIM}${pool[Math.floor(phase / 12) % pool.length]}${R}${GOLD}${BOLD}`;
    }

    return GOLD + BOLD + `(${eye}${mouth}${eye})` + emote + R;
  };

  const ctx = used != null
    ? `[${bar(used)}] ${DIM}${Math.round(used)}%${R}`
    : `[${DIM}${'░'.repeat(W)}${R}]`;

  const costStr = cost != null ? `  ${DIM}$${cost.toFixed(3)}${R}` : '';

  const rlParts = [];
  if (h5 != null) rlParts.push(`${DIM}5h:${R}${col(h5)}${Math.round(h5)}%${R}${countdown(h5r)}`);
  if (d7 != null) rlParts.push(`${DIM}7d:${R}${col(d7)}${Math.round(d7)}%${R}${countdown(d7r)}`);
  const rlStr = rlParts.length ? '  ' + rlParts.join('  ') : '';

  let buddyStr = '';
  try { buddyStr = '  ' + buddy(); } catch (e) {}

  process.stdout.write(`${CYAN}${BOLD}${model}${R}  ${DIM}ctx${R} ${ctx}${costStr}${rlStr}${buddyStr}\n`);
});
