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
    if (secs <= 0) return `${DIM}↺now${R}`;
    const d = (secs / 86400) | 0;
    const h = ((secs % 86400) / 3600) | 0;
    const m = ((secs % 3600) / 60) | 0;
    if (d > 0) return `${DIM}↺${d}d${h}h${R}`;
    if (h > 0) return `${DIM}↺${h}h${m}m${R}`;
    return `${DIM}↺${m}m${R}`;
  };

  const ctx = used != null
    ? `[${bar(used)}] ${DIM}${Math.round(used)}%${R}`
    : `[${DIM}${'░'.repeat(W)}${R}]`;

  const costStr = cost != null ? `  ${DIM}$${cost.toFixed(3)}${R}` : '';

  const rlParts = [];
  if (h5 != null) rlParts.push(`${DIM}5h:${R}${col(h5)}${Math.round(h5)}%${R}${countdown(h5r)}`);
  if (d7 != null) rlParts.push(`${DIM}7d:${R}${col(d7)}${Math.round(d7)}%${R}${countdown(d7r)}`);
  const rlStr = rlParts.length ? '  ' + rlParts.join('  ') : '';

  process.stdout.write(`${CYAN}${BOLD}${model}${R}  ${DIM}ctx${R} ${ctx}${costStr}${rlStr}\n`);
});
