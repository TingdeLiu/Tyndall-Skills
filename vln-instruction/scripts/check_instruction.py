#!/usr/bin/env python3
"""
Self-check for VLN-CE (R2R-CE / RxR-CE) instruction_text.

Ports the acceptance rules of R2RA-RXR-VLNCE-Refined into a standalone checker,
so an instruction can be validated *before* it is written back into a
{split}.json.gz file. Standard library only.

Two things it does:

  1. --profile   read a 3D reference_path and print the motion facts the
                 wording must obey (turn sequence, elevation, goal geometry).
  2. (default)   audit English instruction text: lexicon, punctuation, shape,
                 object disambiguation, and -- when an episode is supplied --
                 agreement between the direction/elevation words and the real
                 3D path.

Two instruction genres, selected with --mode:

  route        (default) R2R-CE style multi-step route description:
               20-35 words, 2-3 sentences, landmark chain, ends in stop/wait.
  object-goal  single-target command: one action verb + one disambiguated
               object phrase, 3-16 words, "and stop" optional.

Exit code is 1 if any ERROR-level issue is found, else 0.

Examples
--------
  # motion facts, before writing a word
  python check_instruction.py --profile --episode ep.json

  # check one draft against its episode
  python check_instruction.py --episode ep.json \
      --text "Walk down the stairs, turn right, and stop near the piano."

  # check a batch of drafts (one per line)
  python check_instruction.py --file drafts.txt

  # single-target object-goal command
  python check_instruction.py --mode object-goal --text "Go to the front-left TV"

  # audit an existing split (each episode's text against its own path)
  python check_instruction.py --episodes val_seen/val_seen.json.gz --limit 200
"""

import argparse
import gzip
import json
import math
import os
import re
import sys
import unicodedata

# output must survive a legacy Windows console code page
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):  # pragma: no cover
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexicon import (  # noqa: E402
    WORD_CORRECTIONS,
    REGEX_REPLACEMENTS,
    FUSED_PATTERNS,
    LANDMARK_NOUNS,
    PHRASE_ENHANCEMENTS,
)

# --- thresholds (identical to the refining pipeline) -------------------------
TURN_MIN_DEG = 25.0           # trajectory_aligner: > 25 deg counts as a turn
U_TURN_MIN_DEG = 135.0        # trajectory_aligner: > 135 deg is a u-turn
SEGMENT_MIN_DIST = 0.05       # ignore waypoint jitter below 5 cm
STAIRS_MIN_DY = 0.25          # below this, stairs words are hallucination
STAIRS_MUST_MENTION_DY = 1.8  # above this, elevation must be described
TELEPORT_MAX_STEP = 5.0       # spatial_validator: a step above 5 m is broken
# route shape, measured on R2R val_seen + val_unseen (n=2617): p10=14, p90=42 words
WORDS_MIN, WORDS_MAX = 12, 60
SENTENCES_MAX = 6
# object-goal shape: a single-target command stays short and single-clause
OG_WORDS_MIN, OG_WORDS_MAX = 3, 16
OG_SENTENCES_MAX = 2

# zero-width space / non-joiner / joiner, LRM, RLM, BOM
ZERO_WIDTH_RE = re.compile("[\u200b\u200c\u200d\u200e\u200f\ufeff]")
SMART_QUOTE_RE = re.compile("[\u2018\u2019\u201c\u201d]")
GLUED_COMMA_RE = re.compile(r"([^\s,0-9])(,)([^\s0-9])")
GLUED_PERIOD_RE = re.compile(r"([A-Za-z])(\.)([A-Za-z])")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.?!;:])")
MULTI_PUNCT_RE = re.compile(r"\.{2,}|,{2,}")
LOWER_AFTER_PERIOD_RE = re.compile(r"\.\s+([a-z])")
WORD_RE = re.compile(r"\b[a-zA-Z0-9'-]+\b")
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
TRAILING_PUNCT = ".!?"

LEFT_RE = re.compile(r"\b(left|left-hand|leftward|leftside)\b", re.I)
RIGHT_RE = re.compile(r"\b(right|right-hand|rightward|rightside)\b", re.I)
U_TURN_RE = re.compile(r"\b(turn around|turn 180|u-turn|about-face|reverse)\b", re.I)
STAIRS_RE = re.compile(r"\b(stairs|steps|upstairs|downstairs|staircase|stairway)\b", re.I)
TERMINAL_RE = re.compile(r"\b(stop|wait|stand)\b", re.I)

# --- object disambiguation strategies, ranked by reliability -----------------
# (1) direction + object  (2) relational anchor  (3) extreme  (4) ordinal
ACTION_VERB_RE = re.compile(r"^(go|walk|head|approach|move|turn|navigate|drive)\b", re.I)
DIRECTION_CUE_RE = re.compile(
    r"\b(front[- ]left|front[- ]right|in front|ahead|behind you|behind me|"
    r"turn around|on your (left|right)|on the (left|right)|to your (left|right)|"
    r"turn (left|right))\b", re.I)
RELATION_CUE_RE = re.compile(
    r"\b(next to|beside|beneath|underneath|beyond|"
    r"on top of|in front of the|behind the|under the|between the|"
    r"on the (dining table|table|desk|counter|shelf|floor|wall|lawn|grass|bench|rug|carpet))\b",
    re.I)
EXTREME_CUE_RE = re.compile(
    r"\b(leftmost|rightmost|left-most|right-most|nearest|closest|farthest|furthest)\b", re.I)
DEPTH_EXTREME_RE = re.compile(r"\b(nearest|closest|farthest|furthest)\b", re.I)
ORDINAL_CUE_RE = re.compile(
    r"\b(first|second|third|fourth|fifth|sixth|1st|2nd|3rd|4th|5th|6th)\b", re.I)
ORDINAL_BEYOND_THIRD_RE = re.compile(r"\b(fourth|fifth|sixth|4th|5th|6th)\b", re.I)
COUNT_ANCHOR_RE = re.compile(
    r"\b(from the (left|right|front|back|door|window)|on the (left|right)|"
    r"on your (left|right)|left side|right side)\b", re.I)


def issue(level, code, message, detail=None):
    return {"level": level, "code": code, "message": message, "detail": detail}


# --------------------------------------------------------------------------- #
# 3D motion profile  (port of scripts/r2r/trajectory_aligner.py)
# --------------------------------------------------------------------------- #
def motion_profile(ref_path):
    """Turn sequence, elevation and length of a Habitat reference_path."""
    if not ref_path or len(ref_path) < 2:
        return {
            "waypoints": len(ref_path or []),
            "path_length": 0.0,
            "elevation_change": 0.0,
            "max_step_dist": 0.0,
            "turn_sequence": [],
            "net_turns": {"left": 0, "right": 0, "u_turn": 0},
        }

    segments = []
    max_step = 0.0
    elevations = [p[1] for p in ref_path]
    for i in range(len(ref_path) - 1):
        p1, p2 = ref_path[i], ref_path[i + 1]
        dx, dy, dz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
        dist_2d = math.hypot(dx, dz)
        dist_3d = math.sqrt(dx * dx + dy * dy + dz * dz)
        max_step = max(max_step, dist_3d)
        if dist_2d > SEGMENT_MIN_DIST:
            segments.append({"dx": dx, "dz": dz, "d2": dist_2d, "d3": dist_3d})

    turns, left, right, u_turn = [], 0, 0, 0
    for i in range(len(segments) - 1):
        s1, s2 = segments[i], segments[i + 1]
        # Habitat (X, Z): a positive cross product is a RIGHT turn
        cross = s1["dx"] * s2["dz"] - s1["dz"] * s2["dx"]
        dot = s1["dx"] * s2["dx"] + s1["dz"] * s2["dz"]
        cos_a = max(-1.0, min(1.0, dot / (s1["d2"] * s2["d2"] + 1e-8)))
        angle = math.degrees(math.acos(cos_a))
        if angle <= TURN_MIN_DEG:
            continue
        if angle > U_TURN_MIN_DEG:
            direction, u_turn = "u_turn", u_turn + 1
        elif cross > 0:
            direction, right = "right", right + 1
        else:
            direction, left = "left", left + 1
        turns.append({"waypoint_index": i + 1, "direction": direction,
                      "angle_deg": round(angle, 1)})

    return {
        "waypoints": len(ref_path),
        "path_length": round(sum(s["d3"] for s in segments), 2),
        "elevation_change": round(max(elevations) - min(elevations), 2),
        "max_step_dist": round(max_step, 2),
        "turn_sequence": turns,
        "net_turns": {"left": left, "right": right, "u_turn": u_turn},
    }


def language_cues(text):
    return {
        "left": len(LEFT_RE.findall(text)),
        "right": len(RIGHT_RE.findall(text)),
        "u_turn": len(U_TURN_RE.findall(text)),
        "stairs": len(STAIRS_RE.findall(text)),
    }


def disambiguation_strategies(text):
    """Which of the four object-disambiguation strategies the text uses."""
    found = []
    if DIRECTION_CUE_RE.search(text):
        found.append("direction")
    if RELATION_CUE_RE.search(text):
        found.append("relation")
    if EXTREME_CUE_RE.search(text):
        found.append("extreme")
    if ORDINAL_CUE_RE.search(text):
        found.append("ordinal")
    return found


def check_disambiguation(text, strategies, mode):
    """Reliability rules for singling out the target object.

    Ranked best to worst: direction+object > relational anchor > extreme > ordinal.
    """
    issues = []

    if "ordinal" in strategies:
        if not COUNT_ANCHOR_RE.search(text):
            issues.append(issue("WARN", "ordinal_without_anchor",
                                "an ordinal needs a counting direction (from the left / "
                                "on the right), otherwise counting is ambiguous"))
        m = ORDINAL_BEYOND_THIRD_RE.search(text)
        if m:
            issues.append(issue("WARN", "ordinal_beyond_third",
                                "ordinals past third are unreliable; prefer an extreme "
                                "(leftmost) or a relation (next to the door)", m.group(0)))

    m = DEPTH_EXTREME_RE.search(text)
    if m and not re.search(r"\b(left|right)-?most\b", text, re.I):
        issues.append(issue("WARN", "depth_dependent_extreme",
                            "nearest/farthest require depth estimation; leftmost/rightmost "
                            "are directly visible and outperform them", m.group(0)))

    if mode == "object-goal":
        if not strategies:
            issues.append(issue("WARN", "no_disambiguation",
                                "no direction, relation, extreme or ordinal; the target "
                                "object is ambiguous whenever more than one exists"))
        if len(strategies) >= 3:
            issues.append(issue("WARN", "stacked_disambiguation",
                                "pick one strategy, do not stack them", "+".join(strategies)))
    return issues


# --------------------------------------------------------------------------- #
# text checks
# --------------------------------------------------------------------------- #
def check_text(text, mode="route"):
    issues = []
    if not text or not text.strip():
        return [issue("ERROR", "empty", "instruction is empty")]

    raw = text
    stripped = text.strip()

    # -- Unicode ------------------------------------------------------------
    if unicodedata.normalize("NFC", raw) != raw:
        issues.append(issue("ERROR", "not_nfc",
                            "not in Unicode NFC form; decomposed characters fragment "
                            "modern tokenizers"))
    if ZERO_WIDTH_RE.search(raw):
        issues.append(issue("ERROR", "zero_width",
                            "contains zero-width / bidi control characters"))
    if SMART_QUOTE_RE.search(raw):
        issues.append(issue("WARN", "smart_quotes",
                            "curly quotes; normalize to ASCII ' and \""))

    # -- punctuation --------------------------------------------------------
    for m in GLUED_COMMA_RE.finditer(raw):
        issues.append(issue("ERROR", "glued_comma", "missing space after comma", m.group(0)))
    for m in GLUED_PERIOD_RE.finditer(raw):
        issues.append(issue("ERROR", "glued_period", "missing space after period", m.group(0)))
    if MULTI_PUNCT_RE.search(raw):
        issues.append(issue("ERROR", "multi_punct", "repeated punctuation (.. or ,,)"))
    if SPACE_BEFORE_PUNCT_RE.search(raw):
        issues.append(issue("WARN", "space_before_punct", "space before punctuation"))
    if re.search(r"  +", raw):
        issues.append(issue("WARN", "double_space", "whitespace needs collapsing"))
    # object-goal commands are typed at a robot, not written into a corpus; a
    # missing final period is normal there, but never in a dataset instruction
    if mode != "object-goal" and stripped[-1] not in TRAILING_PUNCT:
        issues.append(issue("WARN", "no_trailing_punct", "no sentence-final punctuation"))

    # -- casing -------------------------------------------------------------
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) > 20 and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        issues.append(issue("ERROR", "all_caps", "shouted in ALL CAPS; use sentence case"))
    elif stripped[0].islower():
        issues.append(issue("WARN", "lower_initial", "first letter is lowercase"))
    for m in LOWER_AFTER_PERIOD_RE.finditer(stripped):
        issues.append(issue("WARN", "lower_after_period",
                            "sentence after a period starts lowercase", m.group(0)))

    # -- lexicon ------------------------------------------------------------
    for w in WORD_RE.findall(stripped):
        fix = WORD_CORRECTIONS.get(w.lower())
        if fix and fix != w.lower():
            issues.append(issue("ERROR", "typo", "misspelling -> %s" % fix, w))
    for pat, rep in FUSED_PATTERNS:
        m = re.search(pat, stripped, re.I)
        if m:
            issues.append(issue("ERROR", "fused_word", "fused token -> %s" % rep, m.group(0)))
    for pat, rep in REGEX_REPLACEMENTS:
        m = re.search(pat, stripped, re.I)
        if m:
            issues.append(issue("ERROR", "stretched_word",
                                "stretched spelling -> %s" % rep, m.group(0)))
    for pat, rep in PHRASE_ENHANCEMENTS:
        m = re.search(pat, stripped, re.I)
        if m:
            issues.append(issue("WARN", "awkward_phrase",
                                "AMT phrasing -> %s" % rep, m.group(0)))

    # -- shape --------------------------------------------------------------
    words = stripped.split()
    sentences = [s for s in SENTENCE_SPLIT_RE.split(stripped) if s.strip()]

    if mode == "object-goal":
        if not ACTION_VERB_RE.match(stripped):
            issues.append(issue("WARN", "no_action_verb",
                                "start with Go to / Walk to / Head to / Walk towards / "
                                "Approach"))
        if len(words) < OG_WORDS_MIN:
            issues.append(issue("WARN", "too_short",
                                "%d words; too little to name an object" % len(words)))
        if len(words) > OG_WORDS_MAX:
            issues.append(issue("WARN", "too_long",
                                "%d words; a single-target command stays under %d -- if it "
                                "needs more, it is a route, use --mode route"
                                % (len(words), OG_WORDS_MAX)))
        if len(sentences) > OG_SENTENCES_MAX:
            issues.append(issue("WARN", "too_many_sentences",
                                "%d sentences; a single-target command is one clause"
                                % len(sentences)))
    else:
        if len(words) < WORDS_MIN:
            issues.append(issue("WARN", "too_short",
                                "%d words; R2R sits at 14-42 (p10-p90)" % len(words)))
        if len(words) > WORDS_MAX:
            issues.append(issue("WARN", "too_long",
                                "%d words; consider splitting the trajectory" % len(words)))
        if len(sentences) > SENTENCES_MAX:
            issues.append(issue("WARN", "too_many_sentences",
                                "%d sentences; typical is 2-4" % len(sentences)))
        if not TERMINAL_RE.search(stripped):
            issues.append(issue("WARN", "no_terminal_action",
                                "no stop/wait/stand; 85.6% of R2R instructions have one"))

    if not [n for n in LANDMARK_NOUNS if n in stripped.lower()]:
        issues.append(issue("WARN", "no_landmark",
                            "no recognizable landmark noun; nothing to ground on"))

    # -- object disambiguation ----------------------------------------------
    issues += check_disambiguation(stripped, disambiguation_strategies(stripped), mode)

    return issues


# --------------------------------------------------------------------------- #
# text vs. 3D path  (port of evaluate_spatial_alignment)
# --------------------------------------------------------------------------- #
def check_alignment(text, profile):
    issues = []
    cues = language_cues(text)
    net = profile["net_turns"]
    dy = profile["elevation_change"]

    if cues["left"] > 0 and cues["right"] == 0 and net["left"] == 0 and net["right"] >= 2:
        issues.append(issue("ERROR", "direction_contradiction",
                            "text only says LEFT but the path turns RIGHT %d times and "
                            "LEFT 0 times" % net["right"]))
    if cues["right"] > 0 and cues["left"] == 0 and net["right"] == 0 and net["left"] >= 2:
        issues.append(issue("ERROR", "direction_contradiction",
                            "text only says RIGHT but the path turns LEFT %d times and "
                            "RIGHT 0 times" % net["left"]))
    if cues["stairs"] > 0 and dy < STAIRS_MIN_DY:
        issues.append(issue("ERROR", "stairs_hallucination",
                            "text mentions stairs but the path is flat (dy=%.2fm < %.2fm)"
                            % (dy, STAIRS_MIN_DY)))
    if cues["stairs"] == 0 and dy > STAIRS_MUST_MENTION_DY:
        issues.append(issue("WARN", "elevation_unmentioned",
                            "path changes height by %.2fm > %.2fm but the text never says so"
                            % (dy, STAIRS_MUST_MENTION_DY)))
    if not profile["turn_sequence"] and (cues["left"] or cues["right"]):
        issues.append(issue("WARN", "turn_without_path_turn",
                            "text gives a turn but the path has no turn above %.0f deg"
                            % TURN_MIN_DEG))
    return issues


def check_episode_geometry(ep, profile):
    """Sanity of the episode itself, not of the wording."""
    issues = []
    start = ep.get("start_position") or []
    rot = ep.get("start_rotation") or []
    ref = ep.get("reference_path") or []
    goals = ep.get("goals") or []

    if len(start) == 3 and ref:
        d = math.dist(start, ref[0])
        if d > 1e-3:
            issues.append(issue("ERROR", "start_ref_mismatch",
                                "start_position is %.4fm from reference_path[0]" % d))
    if len(rot) == 4:
        norm = math.sqrt(sum(x * x for x in rot))
        if abs(norm - 1.0) > 1e-3:
            issues.append(issue("ERROR", "bad_quaternion",
                                "start_rotation is not normalized (norm=%.4f)" % norm))
    if profile["max_step_dist"] > TELEPORT_MAX_STEP:
        issues.append(issue("ERROR", "teleport",
                            "single waypoint step of %.2fm" % profile["max_step_dist"]))
    if goals and ref:
        gp = goals[0].get("position") or []
        gr = goals[0].get("radius", 3.0)
        if len(gp) == 3:
            d = math.dist(ref[-1], gp)
            if d > gr + 1.0:
                issues.append(issue("ERROR", "goal_unreached",
                                    "reference_path ends %.2fm from the goal (radius %.1fm)"
                                    % (d, gr)))
    vq = ep.get("visual_quality") or {}
    if vq.get("is_valid") is False:
        issues.append(issue("WARN", "visual_void",
                            "episode flagged for mesh voids %s; landmarks may be invisible "
                            "to the agent" % (vq.get("flags") or [])))
    return issues


# --------------------------------------------------------------------------- #
# io / rendering
# --------------------------------------------------------------------------- #
def load_json(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def episodes_of(data):
    if isinstance(data, dict) and "episodes" in data:
        return data["episodes"]
    if isinstance(data, list):
        return data
    return [data]


def shape_of(text):
    return {
        "words": len(text.split()),
        "sentences": len([s for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]),
        "landmarks": len([n for n in LANDMARK_NOUNS if n in text.lower()]),
        "strategies": disambiguation_strategies(text),
    }


def render_profile(profile, ep=None):
    lines = ["motion profile  (%d waypoints)" % profile["waypoints"],
             "  path length      %.2f m" % profile["path_length"],
             "  max step         %.2f m" % profile["max_step_dist"]]

    dy = profile["elevation_change"]
    if dy < STAIRS_MIN_DY:
        verdict = "flat -> stairs/steps words are FORBIDDEN"
    elif dy > STAIRS_MUST_MENTION_DY:
        verdict = "climb -> elevation MUST be described"
    else:
        verdict = "mild slope -> stairs optional"
    lines.append("  elevation dy     %.2f m   (%s)" % (dy, verdict))

    net = profile["net_turns"]
    lines.append("  net turns        left=%d  right=%d  u_turn=%d"
                 % (net["left"], net["right"], net["u_turn"]))
    if profile["turn_sequence"]:
        lines.append("  turn sequence:")
        for t in profile["turn_sequence"]:
            lines.append("    wp%-4d %-7s %5.1f deg"
                         % (t["waypoint_index"], t["direction"], t["angle_deg"]))
    else:
        lines.append("  turn sequence:   none above %.0f deg -- do not write a turn"
                     % TURN_MIN_DEG)

    goal_radius = 3.0
    if ep:
        goals = ep.get("goals") or []
        ref = ep.get("reference_path") or []
        if goals:
            gp = goals[0].get("position") or []
            goal_radius = goals[0].get("radius", 3.0)
            if len(gp) == 3 and ref:
                lines.append("  goal             radius %.1f m, final waypoint %.2f m away"
                             % (goal_radius, math.dist(ref[-1], gp)))
        if ep.get("scene_id"):
            lines.append("  scene            %s" % ep["scene_id"])

    skeleton = ["<start action from the spawn pose>"]
    skeleton += ["turn %s" % ("around" if t["direction"] == "u_turn" else t["direction"])
                 for t in profile["turn_sequence"]]
    skeleton += ["stop near <landmark inside the %.1f m goal radius>" % goal_radius]
    lines.append("  skeleton         " + " -> ".join(skeleton))
    return "\n".join(lines)


def render_issues(label, text, issues, shape):
    shown = text if len(text) <= 100 else text[:97] + "..."
    lines = ['[%s] "%s"' % (label, shown)]
    if not issues:
        lines.append("    OK     clean")
    for it in issues:
        detail = "  <<%s>>" % it["detail"] if it["detail"] else ""
        lines.append("    %-6s %-22s %s%s"
                     % (it["level"], it["code"], it["message"], detail))
    lines.append("    ----   %d words / %d sentences / %d landmarks / disambiguation: %s"
                 % (shape["words"], shape["sentences"], shape["landmarks"],
                    "+".join(shape["strategies"]) or "none"))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", action="append", default=[],
                    help="instruction text to check (repeatable)")
    ap.add_argument("--file", help="file with one instruction per line")
    ap.add_argument("--episode", help="json/json.gz holding the episode the text belongs to")
    ap.add_argument("--episodes", help="a split file; audit each episode against its own text")
    ap.add_argument("--episode-id", help="pick this episode_id out of --episode/--episodes")
    ap.add_argument("--limit", type=int, default=0, help="max episodes to audit")
    ap.add_argument("--mode", choices=("route", "object-goal"), default="route",
                    help="instruction genre: R2R-CE route description (default) or "
                         "single-target object-goal command")
    ap.add_argument("--profile", action="store_true",
                    help="only print the 3D motion profile of --episode")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="machine-readable output")
    args = ap.parse_args(argv)

    ep, profile = None, None
    if args.episode:
        eps = episodes_of(load_json(args.episode))
        if args.episode_id is not None:
            eps = [e for e in eps if str(e.get("episode_id")) == str(args.episode_id)] or eps
        ep = eps[0]
        profile = motion_profile(ep.get("reference_path") or [])

    if args.profile:
        if not ep:
            ap.error("--profile needs --episode")
        print(json.dumps(profile, indent=2) if args.as_json else render_profile(profile, ep))
        return 0

    records = []
    if args.episodes:
        eps = episodes_of(load_json(args.episodes))
        if args.episode_id is not None:
            eps = [e for e in eps if str(e.get("episode_id")) == str(args.episode_id)]
        if args.limit:
            eps = eps[:args.limit]
        for e in eps:
            inst = e.get("instruction") or {}
            records.append((inst.get("instruction_text", ""), e, e.get("episode_id")))
    else:
        texts = list(args.text)
        if args.file:
            with open(args.file, encoding="utf-8") as f:
                texts += [ln.strip() for ln in f if ln.strip()]
        if not texts:
            ap.error("nothing to check: pass --text, --file or --episodes")
        for t in texts:
            records.append((t, ep, None))

    results, n_err = [], 0
    for i, (text, episode, eid) in enumerate(records, 1):
        issues = check_text(text, args.mode)
        if episode is not None:
            prof = profile if (episode is ep and profile) else \
                motion_profile(episode.get("reference_path") or [])
            issues += check_alignment(text, prof)
            issues += check_episode_geometry(episode, prof)
        errs = sum(1 for it in issues if it["level"] == "ERROR")
        n_err += errs
        results.append({"index": i, "episode_id": eid, "text": text,
                        "shape": shape_of(text), "issues": issues, "errors": errs})

    if args.as_json:
        print(json.dumps({"checked": len(results), "error_count": n_err,
                          "results": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if args.episodes and not r["issues"]:
                continue  # batch audits print only what is wrong
            label = r["episode_id"] if r["episode_id"] is not None else r["index"]
            print(render_issues(label, r["text"], r["issues"], r["shape"]))
            print()
        print("checked %d instruction(s), %d ERROR-level issue(s)" % (len(results), n_err))

    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
