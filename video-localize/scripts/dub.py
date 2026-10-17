#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Speak the proofread Chinese track with IndexTTS-2.5 and lay it on the timeline.

Subcommands:
    segment    regroup caption lines into speakable sentences
    voice      cut a reference voice clip out of the source video
    synth      run IndexTTS-2.5 over the sentences
    assemble   place the clips on the original timeline as one audio track
    all        segment -> voice -> synth -> assemble

Runs after `subs.py pairs` + proofreading, before `subs.py build`. Reads
en.json (the timeline) and zh_final.json (the proofread lines); writes dub.wav.

Caption lines are breath-sized fragments -- "and that's why we" / "need to
think about". Speaking them one at a time gives every half sentence its own
falling final contour, which is the loudest tell of machine dubbing. `segment`
regroups them into whole sentences first; everything downstream works on
sentences, not lines.
"""

import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(SKILL_DIR, "tts.json")

# Regrouping thresholds. A gap is the silence between two caption lines; 320ms
# is about where a speaker's breath stops being phrasing and starts being a
# sentence boundary. The char and duration caps stop one runaway sentence from
# swallowing a whole paragraph when the speaker never pauses.
GAP_MS = 320
# Clip size trades two errors against each other, and the curve is U-shaped.
# Every clip carries a fixed ~1.5s of onset and decay that no speed-up
# recovers, so cutting finely drags the whole track late. But a long clip spans
# many caption lines, and how it paces them internally is the TTS's decision,
# not the timeline's -- so its later lines wander off the picture. Measured
# over a 24-minute interview, per-line offset bottomed out near one clip per 9s
# of video: 159 clips gave a 0.7s median and 5.3s worst, against 1.0s/7.0s at
# 105 clips and 0.9s/8.5s at 210. These caps sit at that bottom.
MAX_CHARS = 48
MAX_SEG_MS = 15000

# A pause shorter than GAP_MS but longer than this is a comma, not a sentence
# break: the speaker drew breath mid-thought. Dropping it merges two clauses
# into one unbroken rush, which is most of what makes dubbing sound frantic.
COMMA_GAP_MS = 120

# Fallback for speakers who never audibly pause, and for the no-audio path:
# force a breath at the next fragment boundary once this many characters have
# gone by without punctuation. Fragment boundaries follow the speaker's own
# phrasing, so they are the least bad place to break when nothing else tells us.
COMMA_AFTER_CHARS = 22

# duration_factor is IndexTTS-2.5's speaking-rate knob: below 1.0 speeds up.
# Under 0.82 the voice turns rushed and clipped, so we refuse to go further and
# report the overflow instead of quietly degrading the audio.
MIN_FACTOR = 0.82
SR = 22050                 # IndexTTS-2.5 output rate
TAIL_PAD_MS = 120          # breathing room before the next sentence starts

# Unhurried Chinese, measured over clips IndexTTS-2.5 rendered at factor 1.0.
# Only used to predict the total before synthesising, never to fake a duration.
MS_PER_CHAR = 240

ENDERS = "。！？!?；;…"


def force_utf8():
    """Keep Unicode printable on the Windows console, and keep it flowing:
    synth runs for as long as the video does, and a block-buffered stream shows
    the caller nothing until it finishes."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream and hasattr(stream, "buffer"):
            setattr(sys, name,
                    io.TextIOWrapper(stream.buffer, encoding="utf-8",
                                     errors="replace", line_buffering=True))


def die(msg):
    print(f"[Error] {msg}")
    sys.exit(1)


def load_json(path, hint):
    """Read a step's input, naming the step that should have produced it."""
    if not os.path.isfile(path):
        die(f"{os.path.basename(path)} missing in {os.path.dirname(path) or '.'} -- {hint}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def to_ms(ts):
    hh, mm, rest = ts.split(":")
    ss, ms = rest.split(",")
    return ((int(hh) * 60 + int(mm)) * 60 + int(ss)) * 1000 + int(ms)


def to_ts(ms):
    ms = max(0, int(ms))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def load_config():
    if not os.path.isfile(CONFIG):
        die(f"{CONFIG} missing -- run `python dub.py setup --indextts-dir <path>` first")
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def venv_python(cfg):
    d = cfg["indextts_dir"]
    for rel in (os.path.join(".venv", "Scripts", "python.exe"),
                os.path.join(".venv", "bin", "python")):
        p = os.path.join(d, rel)
        if os.path.isfile(p):
            return p
    return None


def reexec_in_venv(cfg):
    """synth needs IndexTTS's own environment. Re-run there rather than making
    the caller remember which of the two interpreters a command needs."""
    py = venv_python(cfg)
    if not py:
        die(f"no venv under {cfg['indextts_dir']} -- run `uv sync` in that repo")
    if os.path.abspath(sys.executable).lower() == os.path.abspath(py).lower():
        return
    r = subprocess.run([py, os.path.abspath(__file__)] + sys.argv[1:])
    sys.exit(r.returncode)


def find_video(work):
    for pat in ("media.mp4", "media.mkv", "media.webm", "media.m4a"):
        hits = sorted(glob.glob(os.path.join(work, pat)))
        if hits:
            return hits[0]
    return None


# --------------------------------------------------------------------------- #
# segment -- caption fragments into whole sentences
# --------------------------------------------------------------------------- #

def detect_pauses(media, min_ms=COMMA_GAP_MS, noise_db=-32):
    """Read the speaker's real pauses off the audio.

    De-rolling destroys them in the caption timeline: a filler cue stretches
    each line's `end` forward to the next line's `start`, so every silence is
    absorbed into the preceding line and every gap measures 0ms. Segmenting on
    caption timing alone therefore degrades to cutting every N characters. The
    audio still holds the truth, so we read it from there."""
    cmd = ["ffmpeg", "-v", "info", "-i", media, "-af",
           f"silencedetect=noise={noise_db}dB:d={min_ms / 1000:.3f}",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    pauses, start = [], None
    for line in (r.stderr or "").splitlines():
        m = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1))) * 1000
        m = re.search(r"silence_end:\s*([\d.]+)", line)
        if m and start is not None:
            pauses.append((int(start), int(float(m.group(1)) * 1000)))
            start = None
    return pauses


def longest_pause(pauses, t0, t1):
    """Longest silence overlapping [t0, t1]. Pauses arrive in time order."""
    best = 0
    for ps, pe in pauses:
        if ps >= t1:
            break
        best = max(best, min(pe, t1) - max(ps, t0))
    return max(0, best)


PUNCT = ENDERS + "，,、"


def since_punct(s):
    """Characters since the last punctuation -- how long the reader has gone
    without a place to breathe."""
    for k in range(len(s) - 1, -1, -1):
        if s[k] in PUNCT:
            return len(s) - 1 - k
    return len(s)


def join_zh(a, b, gap=0):
    """Join two fragments, restoring the punctuation the captions never had.

    Chinese runs together with no spaces, but two Latin words would fuse into
    one, and a clause boundary with no comma gets read without a breath."""
    if not a:
        return b
    if a[-1] in PUNCT:
        sep = ""
    elif gap >= COMMA_GAP_MS or since_punct(a) >= COMMA_AFTER_CHARS:
        sep = "，"
    elif a[-1].isascii() and a[-1].isalnum() and b[:1].isascii() and b[:1].isalnum():
        sep = " "
    else:
        sep = ""
    return a + sep + b


def build_segments(base, zh, pauses=None, gap_ms=GAP_MS, max_chars=MAX_CHARS,
                   max_ms=MAX_SEG_MS):
    segs, cur = [], None
    for i, (cue, text) in enumerate(zip(base, zh)):
        text = (text or "").strip()
        if not text:
            continue
        start, end = to_ms(cue["start"]), to_ms(cue["end"])
        if cur is None:
            cur = {"i": len(segs), "start": start, "end": end,
                   "text": text, "lines": [i]}
            continue
        # The pause in front of this line. Taken from the audio when we have
        # it; the caption timeline flattened it to zero (see detect_pauses).
        if pauses:
            gap = longest_pause(pauses, to_ms(base[cur["lines"][-1]]["start"]), start)
        else:
            gap = start - cur["end"]
        merged = join_zh(cur["text"], text, gap)
        # Only a real pause or a size cap closes a clip -- deliberately NOT a
        # full stop. A TTS reads consecutive sentences perfectly well and gives
        # them a more connected line than rendering each alone would, while
        # each extra clip costs a fixed ~1.5s of onset and decay that no
        # speed-up can recover. On a 24-minute interview, breaking at every
        # full stop cost 283 clips and 7 minutes of pure overhead; letting them
        # run to the caps gave 101 clips, 2.5 minutes, and cut the worst
        # timeline drift from 12.8s to 1.3s.
        if (gap >= gap_ms
                or len(merged) > max_chars
                or end - cur["start"] > max_ms):
            segs.append(cur)
            cur = {"i": len(segs), "start": start, "end": end,
                   "text": text, "lines": [i]}
        else:
            cur["text"] = merged
            cur["end"] = end
            cur["lines"].append(i)
    if cur:
        segs.append(cur)

    # The window is how much room a sentence really has: up to the next one
    # starting. `natural` is how long the speaker took, kept for the report.
    for k, s in enumerate(segs):
        nxt = segs[k + 1]["start"] if k + 1 < len(segs) else s["end"] + 4000
        s["window"] = max(400, nxt - s["start"] - TAIL_PAD_MS)
        s["natural"] = s["end"] - s["start"]
    return segs


def cmd_segment(a):
    base = load_json(os.path.join(a.work, "en.json"), "run `subs.py pairs` first")
    zh = load_json(os.path.join(a.work, a.lines),
                   "proofread first, or pass --lines zh_mt.json")
    if len(zh) != len(base):
        die(f"{a.lines} has {len(zh)} lines, en.json has {len(base)}")

    pauses = None
    if not a.no_audio_pauses:
        media = find_video(a.work)
        if media:
            pauses = detect_pauses(media, noise_db=a.noise)
            print(f"[Info] {len(pauses)} pauses heard in {os.path.basename(media)}")
        else:
            print("[Warn] no media file -- falling back to caption gaps, which "
                  "de-rolling flattens to zero; sentences will be cut by length alone")

    segs = build_segments(base, zh, pauses, a.gap, a.max_chars)
    out = os.path.join(a.work, "segments.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(segs, f, ensure_ascii=False, indent=1)

    # ~180ms per Chinese character is an unhurried reading pace; anything under
    # that in the slot means synth will have to speed the sentence up.
    tight = sum(1 for s in segs if s["window"] < len(s["text"]) * 180)
    avg = sum(len(s["text"]) for s in segs) // max(1, len(segs))
    print(f"[OK] {len(base)} caption lines -> {len(segs)} sentences  ({out})")
    print(f"[Info] {avg} chars per sentence on average")
    if tight:
        print(f"[Info] {tight} sentences look tight for their slot; synth will "
              f"speed those up and report anything it cannot fit")


# --------------------------------------------------------------------------- #
# voice -- reference clip for zero-shot cloning
# --------------------------------------------------------------------------- #

def cmd_voice(a):
    """Cut the densest stretch of speech out of the source as a voice prompt.

    IndexTTS clones from a single clip, so that clip decides the whole dub's
    voice. The densest run of caption lines is the safest automatic pick: no
    intro music, no applause, no long pause for a slide change."""
    video = find_video(a.work)
    if not video:
        die(f"no media file in {a.work}")
    base = load_json(os.path.join(a.work, "en.json"), "run `subs.py pairs` first")

    want = a.seconds * 1000
    total = to_ms(base[-1]["end"])
    floor = total * 0.05                  # skip intros: music, titles, applause
    # Judged on the audio, not on caption timing -- de-rolling flattens every
    # caption gap to zero, so "densest run of lines" would pick arbitrarily.
    pauses = detect_pauses(video, noise_db=a.noise)
    best, best_sil = None, None
    for c in base:
        start = to_ms(c["start"])
        if start < floor or start + want > total:
            continue
        sil = sum(max(0, min(pe, start + want) - max(ps, start)) for ps, pe in pauses)
        if best_sil is None or sil < best_sil:
            best, best_sil = start, sil

    if best is None:
        best = to_ms(base[len(base) // 3]["start"])
    out = os.path.join(a.work, "voice_ref.wav")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{best / 1000:.3f}",
           "-t", str(a.seconds), "-i", video,
           "-vn", "-ac", "1", "-ar", str(SR), out]
    if subprocess.run(cmd).returncode != 0:
        die("ffmpeg failed to cut the reference clip")
    print(f"[OK] {a.seconds}s voice reference from {to_ts(best)} "
          f"({best_sil or 0}ms of it silent) -> {out}")
    print("[Info] listen to it -- if it caught applause or a second speaker, "
          "pass --voice <your own clip.wav> to synth instead")


# --------------------------------------------------------------------------- #
# synth -- IndexTTS-2.5
# --------------------------------------------------------------------------- #

def cmd_synth(a):
    cfg = load_config()
    reexec_in_venv(cfg)

    # A few small models (semantic codec, speaker encoder) are pulled from
    # HuggingFace on first run; the mirror is the difference between a minute
    # and a timeout on a mainland connection.
    sys.path.insert(0, cfg["indextts_dir"])

    import soundfile as sf
    from indextts.infer_v2_5 import IndexTTS2

    segs = load_json(os.path.join(a.work, "segments.json"), "run `dub.py segment` first")
    voice = os.path.abspath(a.voice or os.path.join(a.work, "voice_ref.wav"))
    if not os.path.isfile(voice):
        die(f"{voice} missing -- run `dub.py voice` or pass --voice")

    ckpt = cfg["checkpoints"]
    if not os.path.isfile(os.path.join(ckpt, "config.yaml")):
        die(f"no config.yaml in {ckpt} -- model weights not downloaded yet")
    clips = os.path.join(a.work, "clips")
    os.makedirs(clips, exist_ok=True)

    def clip_path(s):
        return os.path.join(clips, f"seg_{s['i']:04d}.wav")

    # A resumed run with every clip already on disk has nothing to synthesise,
    # and shouldn't spend a minute loading 5GB of weights to discover that.
    pending = [s for s in segs if not (a.resume and os.path.isfile(clip_path(s)))]
    tts = None
    if pending:
        print(f"[Info] loading IndexTTS-2.5 from {ckpt} ...")
        tts = IndexTTS2(cfg_path=os.path.join(ckpt, "config.yaml"), model_dir=ckpt,
                        use_bf16=a.bf16, use_cuda_kernel=False, use_deepspeed=False)
    else:
        print(f"[Info] all {len(segs)} clips already exist, nothing to synthesise")

    # Whether the dub can fit at all is a whole-track question, not a per
    # sentence one. Dense interview captions leave some sentences a window no
    # speech could fill -- 12 characters in 700ms -- so letting those few race
    # at MIN_FACTOR while everything else sits at 1.0 both sounds worse and
    # doesn't recover the time. One small global slowdown, inaudible at ~0.9,
    # buys back far more than the outliers ever could.
    pace = 1.0
    if a.pace == "auto":
        est = sum(len(s["text"]) for s in segs) * MS_PER_CHAR
        win = sum(s["window"] for s in segs)
        if est > win:
            pace = max(MIN_FACTOR, win / est * 0.98)
            print(f"[Info] the Chinese needs about {est / 60000:.1f} min against "
                  f"{win / 60000:.1f} min of window -- pacing every line at {pace:.2f}")
    else:
        pace = float(a.pace)

    report, retried, overflow = [], 0, 0
    for s in segs:
        path = clip_path(s)
        if a.resume and os.path.isfile(path):
            dur = int(sf.info(path).duration * 1000)
            report.append({**s, "dur": dur, "factor": None, "fit": dur <= s["window"]})
            continue

        tts.infer(voice, s["text"], path, a.lang,
                  duration_factor=pace, verbose=False)
        dur = int(sf.info(path).duration * 1000)
        factor = pace if pace < 1.0 else None

        # Still over after the global pace: tighten this one further, but never
        # past MIN_FACTOR -- beyond that the voice sounds hurried, and assemble
        # pushing the line late is the lesser evil.
        if dur > s["window"]:
            tighter = max(MIN_FACTOR, pace * s["window"] / dur * 0.98)
            if tighter < pace - 0.005:
                factor = tighter
                tts.infer(voice, s["text"], path, a.lang,
                          duration_factor=factor, verbose=False)
                dur = int(sf.info(path).duration * 1000)
                retried += 1

        fit = dur <= s["window"]
        if not fit:
            overflow += 1
        report.append({**s, "dur": dur, "factor": factor, "fit": fit})
        flag = "" if fit else f"  OVERFLOW +{dur - s['window']}ms"
        print(f"  [{s['i']:>4}/{len(segs)}] {to_ts(s['start'])} "
              f"{dur:>5}ms/{s['window']:>5}ms{flag}")

    with open(os.path.join(a.work, "dub_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"\n[OK] {len(segs)} clips -> {clips}")
    print(f"[Info] {retried} needed speeding up; {overflow} still overflow "
          f"(assemble pushes those later and reports the drift)")


# --------------------------------------------------------------------------- #
# assemble -- one track on the original timeline
# --------------------------------------------------------------------------- #

def line_offsets(work, placed, lines_file="zh_final.json"):
    """How far each caption line lands from its cue -- what a viewer sees.

    `assemble` can only place whole clips. Inside one, the TTS decides how the
    lines are paced and the timeline gets no say, so a long clip's last line can
    sit seconds from its cue while the clip's own start is dead on. Clip drift
    therefore flatters the result; this is the number to judge a dub on.

    Positions are estimated by character share, which is an approximation --
    good enough to rank configurations and to catch a bad one."""
    base_p = os.path.join(work, "en.json")
    zh_p = os.path.join(work, lines_file)
    if not (os.path.isfile(base_p) and os.path.isfile(zh_p)):
        return None
    with open(base_p, encoding="utf-8") as f:
        base = json.load(f)
    with open(zh_p, encoding="utf-8") as f:
        zh = json.load(f)
    if len(base) != len(zh):
        return None

    errs = []
    for _, pos, s, dur in placed:
        idx = s.get("lines") or []
        total = sum(len(zh[i]) for i in idx) or 1
        acc = 0
        for i in idx:
            errs.append(abs(pos + dur * acc / total - to_ms(base[i]["start"])))
            acc += len(zh[i])
    return sorted(errs) or None


def cmd_assemble(a):
    cfg = load_config()
    reexec_in_venv(cfg)
    import numpy as np
    import soundfile as sf

    segs = load_json(os.path.join(a.work, "dub_report.json"),
                     "run `dub.py synth` first")
    if not segs:
        die("dub_report.json is empty -- nothing was synthesised")
    clips = os.path.join(a.work, "clips")

    # First pass: work out where each clip actually lands. A sentence that
    # outgrew its slot pushes the next one later rather than talking over it,
    # so with enough overflow the track finishes well past the video -- and we
    # need that real end before allocating, or the last clips fall off it.
    placed, cursor, drifted, worst = [], 0, 0, 0
    for s in segs:
        path = os.path.join(clips, f"seg_{s['i']:04d}.wav")
        if not os.path.isfile(path):
            print(f"[Warn] no clip for sentence {s['i']}, skipping")
            continue
        pos = max(s["start"], cursor)
        if pos > s["start"]:
            drifted += 1
            worst = max(worst, pos - s["start"])
        dur = int(sf.info(path).duration * 1000)
        placed.append((path, pos, s, dur))
        cursor = pos + dur

    total_ms = cursor + 500
    video = find_video(a.work)
    video_ms = 0
    if video:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", video], capture_output=True, text=True)
        try:
            video_ms = int(float(probe.stdout.strip()) * 1000)
        except ValueError:
            pass
        total_ms = max(total_ms, video_ms)

    # Second pass: mix. Drift is not cumulative by design -- the next sentence
    # with room in front of it snaps back to its own timestamp.
    track = np.zeros(int(total_ms / 1000 * SR) + 1, dtype=np.float32)
    for path, pos, _, _ in placed:
        audio, sr = sf.read(path, dtype="float32", always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != SR:
            idx = np.linspace(0, len(audio) - 1, int(len(audio) * SR / sr))
            audio = np.interp(idx, np.arange(len(audio)), audio).astype(np.float32)
        a0 = int(pos / 1000 * SR)
        end = min(a0 + len(audio), len(track))
        if end > a0:
            track[a0:end] += audio[:end - a0]

    peak = float(np.max(np.abs(track))) or 1.0
    track = track / peak * 0.89          # headroom; a hard 1.0 clips on remux
    out = os.path.join(a.work, "dub.wav")
    sf.write(out, track, SR)

    print(f"[OK] {len(track) / SR / 60:.1f} min dub track -> {out}")
    if drifted:
        print(f"[Info] {drifted} of {len(placed)} clips start late, "
              f"worst {worst / 1000:.1f}s")

    # The figure that actually matters -- see line_offsets.
    errs = line_offsets(a.work, placed, a.lines)
    if errs:
        med, p90 = errs[len(errs) // 2], errs[int(len(errs) * 0.9)]
        print(f"[Info] caption lines land {med / 1000:.1f}s from their cue at the "
              f"median, {p90 / 1000:.1f}s at the 90th percentile, "
              f"{errs[-1] / 1000:.1f}s at worst  <- judge the dub on this")
        if p90 > 3000:
            print(f"[Warn] the 90th percentile is over 3s, so roughly one line in "
                  f"ten is visibly out of step. Clip size is the usual cause and "
                  f"the curve is U-shaped: try --max-chars a step either side of "
                  f"{MAX_CHARS} and re-run segment to compare.")
    if video_ms and cursor > video_ms + 1000:
        print(f"[Warn] the dub overruns the video by {(cursor - video_ms) / 1000:.0f}s "
              f"-- the Chinese is too long for the timeline. Shorten the lines "
              f"marked \"fit\": false in dub_report.json and re-run; speeding the "
              f"voice up further would only make it sound frantic.")
    elif worst > 1500:
        print("[Warn] over 1.5s adrift -- check dub_report.json for "
              "\"fit\": false and shorten those Chinese lines")


# --------------------------------------------------------------------------- #

def cmd_setup(a):
    d = os.path.abspath(a.indextts_dir)
    ckpt = os.path.abspath(a.checkpoints or os.path.join(d, "checkpoints"))
    if not os.path.isdir(d):
        die(f"{d} is not a directory")
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump({"indextts_dir": d, "checkpoints": ckpt}, f, indent=1)
    py = venv_python({"indextts_dir": d})
    print(f"[OK] {CONFIG}")
    print(f"  indextts_dir  {d}")
    print(f"  checkpoints   {ckpt}"
          f"{'' if os.path.isdir(ckpt) else '   (NOT DOWNLOADED YET)'}")
    print(f"  venv          {py or '(NOT BUILT -- run `uv sync` there)'}")


def cmd_all(a):
    # Switch interpreters once, up front. Leaving it to synth would re-exec the
    # whole `all` command and run segment and voice a second time.
    reexec_in_venv(load_config())
    cmd_segment(a)
    if not a.voice:
        cmd_voice(a)
    cmd_synth(a)
    cmd_assemble(a)


def main():
    force_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="record where IndexTTS lives")
    s.add_argument("--indextts-dir", required=True)
    s.add_argument("--checkpoints")
    s.set_defaults(func=cmd_setup)

    def seg_args(p):
        p.add_argument("--lines", default="zh_final.json",
                       help="proofread lines (default zh_final.json)")
        p.add_argument("--gap", type=int, default=GAP_MS,
                       help="pause that ends a sentence, ms")
        p.add_argument("--max-chars", type=int, default=MAX_CHARS)
        p.add_argument("--noise", type=int, default=-32,
                       help="silence threshold in dB (default -32)")
        p.add_argument("--no-audio-pauses", action="store_true",
                       help="cut on caption gaps instead of listening to the audio")

    def synth_args(p):
        p.add_argument("--voice", help="reference clip (default work/voice_ref.wav)")
        p.add_argument("--pace", default="auto",
                       help="global speaking rate: 'auto' fits the whole track to "
                            "the timeline, or a fixed factor such as 0.95")
        p.add_argument("--lang", default="zhen",
                       help="zhen keeps English terms readable inside Chinese")
        p.add_argument("--bf16", action="store_true", help="faster, slightly rougher")
        p.add_argument("--resume", action="store_true", help="keep existing clips")

    g = sub.add_parser("segment", help="regroup caption lines into sentences")
    g.add_argument("--work", "-w", required=True)
    seg_args(g)
    g.set_defaults(func=cmd_segment)

    v = sub.add_parser("voice", help="cut a reference voice clip")
    v.add_argument("--work", "-w", required=True)
    v.add_argument("--seconds", type=int, default=10)
    v.add_argument("--noise", type=int, default=-32,
                   help="silence threshold in dB (default -32)")
    v.set_defaults(func=cmd_voice)

    y = sub.add_parser("synth", help="run IndexTTS-2.5 over the sentences")
    y.add_argument("--work", "-w", required=True)
    synth_args(y)
    y.set_defaults(func=cmd_synth)

    m = sub.add_parser("assemble", help="lay clips on the timeline")
    m.add_argument("--work", "-w", required=True)
    m.add_argument("--lines", default="zh_final.json",
                   help="the lines that were spoken, for the line-offset report")
    m.set_defaults(func=cmd_assemble)

    z = sub.add_parser("all", help="segment -> voice -> synth -> assemble")
    z.add_argument("--work", "-w", required=True)
    seg_args(z)
    synth_args(z)
    z.add_argument("--seconds", type=int, default=10)
    z.set_defaults(func=cmd_all)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
