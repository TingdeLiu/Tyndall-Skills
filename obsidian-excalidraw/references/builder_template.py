"""
Reusable Excalidraw diagram builder for Obsidian.

Drop this into your project (or import inline), instantiate Builder, add elements,
then call .write(path). All known footguns are guarded by validators that run
before write — index trailing-zero, container binding mismatches, text overflow,
duplicate IDs.

Usage:
    from builder_template import Builder
    b = Builder()
    b.add_rect("box1", 100, 100, 200, 140, "#1e40af", "#dbeafe")
    b.add_text("txt1", 100, 100, 200, 140, "Vision Encoder\nDINOv2", container="box1")
    b.add_arrow("a1", 300, 170, [[0,0],[40,0]])
    b.subbox("sub1", "txt_sub1", 110, 150, 90, 80, "#475569", "#f1f5f9", "Depth\n(H,W)")
    b.write("MyDiagram.architecture.md")

Index allocation is automatic — Builder hands out fractional-indexing-safe values
in insertion order: a1, a2, ..., a9, aA, aB, ..., aZ, aa, ab, ..., az, b1, b2, ...
"""
import json
import string

# ===== Color palette (parent stroke / parent fill / sub stroke / sub fill / text) =====
PALETTE = {
    "input":      ("#0891b2", "#cffafe", "#0e7490", "#ecfeff", "#1f2937"),
    "vision":     ("#1e40af", "#dbeafe", "#2563eb", "#eff6ff", "#1f2937"),
    "llm":        ("#6d28d9", "#ede9fe", "#7c3aed", "#f5f3ff", "#1f2937"),
    "fusion":     ("#be185d", "#fce7f3", "#db2777", "#fdf2f8", "#1f2937"),
    "policy":     ("#047857", "#d1fae5", "#059669", "#ecfdf5", "#1f2937"),
    "action":     ("#c2410c", "#fed7aa", "#ea580c", "#ffedd5", "#1f2937"),
    "controller": ("#475569", "#f1f5f9", "#64748b", "#f8fafc", "#1f2937"),
    "annotation": ("#b45309", "#fef3c7", "#d97706", "#fffbeb", "#1f2937"),
    "emphasis":   ("#dc2626", "#fee2e2", "#ef4444", "#fef2f2", "#1f2937"),
}


def _index_seq():
    """Yield fractional-indexing-safe strings in lex order. Never ends in '0'."""
    # bucket 'a': a1..a9, aA..aZ, aa..az = 61 values
    # then 'b': b1..b9, bA..bZ, ba..bz = 61 values
    # etc.
    digits = "123456789" + string.ascii_uppercase + string.ascii_lowercase
    for prefix in string.ascii_lowercase:  # a, b, c, ...
        for d in digits:
            yield prefix + d


def _est_chars_per_line(width, fs):
    """Excalifont (fontFamily=5) average 0.6*fontSize per char, conservative 0.65."""
    return (width - 12) / (fs * 0.65)


class Builder:
    def __init__(self, source="https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.16.1",
                 bg_color="#ffffff"):
        self.elements = []
        self.source = source
        self.bg = bg_color
        self._idx_iter = _index_seq()
        self._used_ids = set()

    # ----- internal helpers -----
    def _next_idx(self):
        return next(self._idx_iter)

    def _seed(self, eid):
        h = abs(hash(eid))
        return h % 999_999

    def _claim_id(self, eid):
        if eid in self._used_ids:
            raise ValueError(f"Duplicate element id: {eid}")
        self._used_ids.add(eid)

    def _common(self, eid, etype, x, y, w, h, stroke, fill, sw, ss, rough, opa, rnd, idx=None, bound_to=None):
        self._claim_id(eid)
        be = [{"type": "text", "id": bound_to}] if bound_to else []
        d = {
            "id": eid, "type": etype,
            "x": x, "y": y, "width": w, "height": h, "angle": 0,
            "strokeColor": stroke, "backgroundColor": fill,
            "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": ss,
            "roughness": rough, "opacity": opa,
            "groupIds": [], "frameId": None,
            "index": idx if idx is not None else self._next_idx(),
            "roundness": {"type": rnd} if rnd else None,
            "seed": self._seed(eid), "version": 1, "versionNonce": self._seed(eid) + 1,
            "isDeleted": False, "boundElements": be,
            "updated": 1772505596772, "link": None, "locked": False,
        }
        if bound_to:
            d["customData"] = {"legacyTextWrap": True}
        return d

    # ----- element constructors -----
    def add_rect(self, eid, x, y, w, h, stroke, fill, sw=2, ss="solid", rough=1, opa=100, rnd=3, bound_to=None):
        d = self._common(eid, "rectangle", x, y, w, h, stroke, fill, sw, ss, rough, opa, rnd, bound_to=bound_to)
        self.elements.append(d)
        return d

    def add_ellipse(self, eid, x, y, w, h, stroke, fill, sw=2, ss="solid", rough=1, opa=100):
        d = self._common(eid, "ellipse", x, y, w, h, stroke, fill, sw, ss, rough, opa, rnd=None)
        self.elements.append(d)
        return d

    def add_diamond(self, eid, x, y, w, h, stroke, fill):
        d = self._common(eid, "diamond", x, y, w, h, stroke, fill, sw=2, ss="solid", rough=1, opa=100, rnd=None)
        self.elements.append(d)
        return d

    def add_text(self, eid, x, y, w, h, text, fs=14, color="#1f2937",
                 align="center", valign="middle", auto_resize=False, container=None):
        self._claim_id(eid)
        d = {
            "id": eid, "type": "text",
            "x": x, "y": y, "width": w, "height": h, "angle": 0,
            "strokeColor": color, "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100,
            "groupIds": [], "frameId": None,
            "index": self._next_idx(),
            "roundness": None,
            "seed": self._seed(eid), "version": 1, "versionNonce": self._seed(eid) + 1,
            "isDeleted": False, "boundElements": [],
            "updated": 1772505596772, "link": None, "locked": False,
            "text": text, "rawText": text,
            "fontSize": fs, "fontFamily": 5,
            "textAlign": align, "verticalAlign": valign,
            "containerId": container,
            "originalText": text, "autoResize": auto_resize,
            "lineHeight": 1.25,
        }
        self.elements.append(d)
        return d

    def add_arrow(self, eid, x, y, points, color="#374151", style="solid", sw=2, end_arrow="arrow"):
        self._claim_id(eid)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        d = {
            "id": eid, "type": "arrow",
            "x": x, "y": y,
            "width": max(xs) - min(xs), "height": max(ys) - min(ys),
            "angle": 0,
            "strokeColor": color, "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": style,
            "roughness": 1, "opacity": 100,
            "groupIds": [], "frameId": None,
            "index": self._next_idx(),
            "roundness": {"type": 2},
            "seed": self._seed(eid), "version": 1, "versionNonce": self._seed(eid) + 1,
            "isDeleted": False, "boundElements": [],
            "updated": 1772505596772, "link": None, "locked": False,
            "points": points,
            "lastCommittedPoint": None,
            "startBinding": None, "endBinding": None,
            "startArrowhead": None, "endArrowhead": end_arrow,
        }
        self.elements.append(d)
        return d

    # ----- composite: sub-box (rect + container-bound centered text) -----
    def subbox(self, rect_id, txt_id, x, y, w, h, stroke, fill, text, fs=11, sw=1, color="#1f2937"):
        """Sub-box = small rect + centered text, bound via containerId.
        Use this inside a parent module to show internal sub-components."""
        self.add_rect(rect_id, x, y, w, h, stroke, fill, sw=sw, bound_to=txt_id)
        self.add_text(txt_id, x, y, w, h, text, fs=fs, color=color,
                      align="center", valign="middle", auto_resize=False, container=rect_id)

    # ----- composite: simple module (rect + container-bound centered text) -----
    def module(self, rect_id, txt_id, x, y, w, h, stroke, fill, text, fs=13):
        """Simple module: single rect with container-bound centered multi-line text.
        Use for Input / Output / leaf modules with 3-5 lines of content."""
        self.add_rect(rect_id, x, y, w, h, stroke, fill, sw=2, bound_to=txt_id)
        self.add_text(txt_id, x, y, w, h, text, fs=fs, container=rect_id)

    # ----- composite: parent box (parent rect + free top-aligned title) -----
    def parent_box(self, rect_id, title_id, x, y, w, h, stroke, fill, title, sw=3, fs_title=14):
        """Parent container: thick stroke + title strip at top.
        Add sub-boxes inside afterwards via .subbox()."""
        self.add_rect(rect_id, x, y, w, h, stroke, fill, sw=sw)
        self.add_text(title_id, x, y + 4, w, 22, title, fs=fs_title, color=stroke,
                      align="center", valign="top", auto_resize=False)

    # ===== Validation =====
    def validate(self, strict=True):
        """Run all known sanity checks. Returns list of issues; raises if strict and any."""
        issues = []
        ids = [e["id"] for e in self.elements]
        # 1. duplicate ids
        dup = {x for x in ids if ids.count(x) > 1}
        if dup:
            issues.append(f"DUP_ID: {dup}")
        # 2. fractional indexing: no trailing zero
        bad_idx = [(e["id"], e["index"]) for e in self.elements if e["index"].endswith("0")]
        if bad_idx:
            issues.append(f"TRAILING_ZERO_INDEX: {bad_idx}")
        # 3. unique indices
        idxs = [e["index"] for e in self.elements]
        if len(set(idxs)) != len(idxs):
            issues.append(f"DUP_INDEX")
        # 4. container binding bidirectional (both directions)
        # 4a. text → rect: containerId must point to existing rect with backref
        for e in self.elements:
            cid = e.get("containerId")
            if cid:
                cont = next((x for x in self.elements if x["id"] == cid), None)
                if not cont:
                    issues.append(f"MISSING_CONTAINER: text {e['id']} → {cid}")
                else:
                    be_ids = [b["id"] for b in cont.get("boundElements", [])]
                    if e["id"] not in be_ids:
                        issues.append(f"MISSING_BACKREF: rect {cid} should bind text {e['id']}")
        # 4b. rect.boundElements → text: each ref'd text must exist with matching containerId
        for e in self.elements:
            for b in e.get("boundElements", []):
                if b.get("type") != "text":
                    continue
                tgt = next((x for x in self.elements if x["id"] == b["id"]), None)
                if not tgt:
                    issues.append(f"DANGLING_BOUND_TEXT: rect {e['id']} → text {b['id']} (text doesn't exist)")
                elif tgt.get("containerId") != e["id"]:
                    issues.append(f"BACKREF_MISMATCH: rect {e['id']} binds text {b['id']} but text.containerId={tgt.get('containerId')!r}")
        # 5. arrow binding bidirectional (if any)
        for e in self.elements:
            if e["type"] == "arrow":
                for side in ("startBinding", "endBinding"):
                    b = e.get(side)
                    if b:
                        target = next((x for x in self.elements if x["id"] == b["elementId"]), None)
                        if not target:
                            issues.append(f"DANGLING_ARROW_BIND: {e['id']} {side} → {b['elementId']}")
                        else:
                            be_ids = [be["id"] for be in target.get("boundElements", [])]
                            if e["id"] not in be_ids:
                                issues.append(f"MISSING_ARROW_BACKREF: {e['id']} {side}")
        # 6. text overflow (free text only — bound text auto-wraps)
        for e in self.elements:
            if e["type"] != "text":
                continue
            if e.get("containerId") or e.get("autoResize"):
                continue  # bound or auto-resized text doesn't overflow
            max_chars = _est_chars_per_line(e["width"], e["fontSize"])
            longest = max((len(line) for line in e["text"].split("\n")), default=0)
            if longest > max_chars + 0.5:
                issues.append(f"OVERFLOW: {e['id']} longest={longest} max={max_chars:.1f}")
        # 7. no curly-brace superscripts (potential compression issue)
        for e in self.elements:
            if e["type"] == "text" and ("^{" in e["text"] or "_{" in e["text"]):
                issues.append(f"CURLY_SUPERSCRIPT: {e['id']} — use flat notation")

        if strict and issues:
            for i in issues:
                print("  ✗", i)
            raise AssertionError(f"{len(issues)} validation issues — see above")
        return issues

    # ===== Output =====
    def to_json(self):
        """Build the compact JSON string (one element per line)."""
        header = f'{{"type":"excalidraw","version":2,"source":"{self.source}","elements":['
        footer = f'],"appState":{{"gridSize":null,"viewBackgroundColor":"{self.bg}"}},"files":{{}}}}'
        lines = [header]
        for i, e in enumerate(self.elements):
            line = json.dumps(e, ensure_ascii=False, separators=(",", ":"))
            if i < len(self.elements) - 1:
                line += ","
            lines.append(line)
        lines.append(footer)
        result = "\n".join(lines)
        json.loads(result)  # sanity: parses
        return result

    def to_markdown(self):
        """Build the full Obsidian-wrapped markdown."""
        json_block = self.to_json()
        text_blocks = [e["text"] + " ^" + e["id"] for e in self.elements if e["type"] == "text"]
        text_section = "\n\n".join(text_blocks)
        fence_open = "```json"
        fence_close = "```"
        return (
            "---\nexcalidraw-plugin: parsed\ntags: [excalidraw]\n---\n"
            "==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== "
            "You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. "
            "For more info check in plugin settings under 'Saving'\n\n"
            "# Excalidraw Data\n\n## Text Elements\n" + text_section + "\n\n%%\n## Drawing\n"
            + fence_open + "\n" + json_block + "\n" + fence_close + "\n%%\n"
        )

    def write(self, path, validate=True):
        """Validate and write to the given path."""
        if validate:
            self.validate(strict=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        print(f"✓ Wrote {len(self.elements)} elements → {path}")


# ===== Standalone helpers (functional API for users who don't want a class) =====
def estimate_max_chars(box_width, font_size):
    """How many chars fit per line in a box of given width at given fontSize."""
    return _est_chars_per_line(box_width, font_size)


__all__ = ["Builder", "PALETTE", "estimate_max_chars"]


# ===== Quickstart example =====
if __name__ == "__main__":
    b = Builder()
    px, fx = PALETTE["input"][:2]
    b.module("inp", "txt_inp", 40, 100, 180, 120, px, fx, "[Input]\n=====\n- RGB-D\n- Camera T*")

    # Hero module with 2x2 sub-boxes
    px, fx, sx, sf = PALETTE["llm"][:4]
    b.parent_box("dit", "dit_title", 260, 80, 360, 200, px, fx, "Wan 2.1-14B DiT")
    b.subbox("sub_tl", "txt_tl", 270, 120, 165, 50, sx, sf, "VAE 8x8 / 4x4")
    b.subbox("sub_tr", "txt_tr", 445, 120, 165, 50, sx, sf, "Flow Match")
    b.subbox("sub_bl", "txt_bl", 270, 180, 165, 50, sx, sf, "FramePack")
    b.subbox("sub_br", "txt_br", 445, 180, 165, 50, sx, sf, "Plücker rays")
    # Internal flow: TL → TR (main)
    b.add_arrow("flow_main", 435, 145, [[0, 0], [10, 0]], color=px, sw=2)
    # Internal conditioning: BL ↑, BR ↑
    b.add_arrow("cond_bl", 352, 180, [[0, 0], [175, -10]], color=px, style="dashed", sw=1)
    b.add_arrow("cond_br", 527, 180, [[0, 0], [0, -10]], color=px, style="dashed", sw=1)

    # Pipeline arrow
    b.add_arrow("a1", 220, 160, [[0, 0], [40, 0]])

    # Validate + write
    b.write("example_output.md")
