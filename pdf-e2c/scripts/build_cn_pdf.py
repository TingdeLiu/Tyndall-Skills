# -*- coding: utf-8 -*-
"""
Step 3: Build the free-flowing Chinese PDF from a data-driven document spec.

Usage:
    python build_cn_pdf.py <workdir> [--out <path.pdf>] [--zoom 4.0] [--font STSong-Light]

Reads <workdir>/document.json  and  <workdir>/assets/*.png.

document.json schema:
{
  "title": "DA-Nav 中文版",                # PDF metadata title (optional)
  "page": "A4",                            # "A4" | "letter" (optional)
  "font": "STSong-Light",                  # built-in Adobe CJK CID font (optional)
  "elements": [
    {"type":"title",   "text":"..."},
    {"type":"author",  "text":"..."},
    {"type":"affil",   "text":"..."},
    {"type":"abstract","text":"摘要——..."},
    {"type":"h1",      "text":"I. 引言"},
    {"type":"h2",      "text":"A. ..."},
    {"type":"body",    "text":"...", "indent": true},   # indent default true
    {"type":"bullet",  "text":"• ..."},
    {"type":"image",   "src":"fig1", "caption":"图 1：...", "max_ratio":1.0},
    {"type":"equation","src":"eq3", "max_ratio":0.8},
    {"type":"reference","text":"[1] ..."},
    {"type":"refs_block","text":"[1] ... [2] ..."},     # auto-split on [n]
    {"type":"spacer",  "h":6}
  ]
}

Built-in CJK fonts (no font file needed): STSong-Light (宋), STSongStd-Light,
MSung-Light, STHeiti-Regular-ish via 'STSong-Light' only on most installs.
STSong-Light is the safe default and ships with reportlab.
"""
import json, os, re, argparse
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Image, KeepTogether)
from PIL import Image as PILImage


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--zoom", type=float, default=4.0)
    ap.add_argument("--font", default=None)
    a = ap.parse_args()

    with open(os.path.join(a.workdir, "document.json"), encoding="utf-8") as f:
        spec = json.load(f)
    assets = os.path.join(a.workdir, "assets")
    ZOOM = a.zoom

    CN = a.font or spec.get("font", "STSong-Light")
    pdfmetrics.registerFont(UnicodeCIDFont(CN))

    PAGE = letter if str(spec.get("page", "A4")).lower() == "letter" else A4
    PAGE_W, PAGE_H = PAGE
    LM = RM = 2.0 * cm
    TM = 1.8 * cm
    BM = 1.8 * cm
    CW = PAGE_W - LM - RM

    DARK = HexColor("#111111")
    GRAY = HexColor("#444444")
    ACC = HexColor("#1a3a6b")

    S = {
        "title": ParagraphStyle("title", fontName=CN, fontSize=19, leading=26,
                                 alignment=TA_CENTER, textColor=DARK, spaceAfter=6),
        "author": ParagraphStyle("author", fontName=CN, fontSize=11, leading=15,
                                  alignment=TA_CENTER, textColor=DARK, spaceAfter=2),
        "affil": ParagraphStyle("affil", fontName=CN, fontSize=8, leading=11,
                                 alignment=TA_CENTER, textColor=GRAY, spaceAfter=10),
        "abstract": ParagraphStyle("abstract", fontName=CN, fontSize=9.5, leading=15,
                                   alignment=TA_JUSTIFY, wordWrap="CJK", textColor=DARK,
                                   leftIndent=10, rightIndent=10, spaceAfter=8),
        "h1": ParagraphStyle("h1", fontName=CN, fontSize=14, leading=20,
                             alignment=TA_LEFT, textColor=ACC, spaceBefore=14, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName=CN, fontSize=11.5, leading=16,
                             alignment=TA_LEFT, textColor=ACC, spaceBefore=9, spaceAfter=4),
        "body": ParagraphStyle("body", fontName=CN, fontSize=10.5, leading=17.5,
                               alignment=TA_JUSTIFY, wordWrap="CJK", textColor=DARK,
                               spaceAfter=7, firstLineIndent=21),
        "body_ni": ParagraphStyle("body_ni", fontName=CN, fontSize=10.5, leading=17.5,
                                  alignment=TA_JUSTIFY, wordWrap="CJK", textColor=DARK,
                                  spaceAfter=7, firstLineIndent=0),
        "bullet": ParagraphStyle("bullet", fontName=CN, fontSize=10.5, leading=17,
                                 alignment=TA_JUSTIFY, wordWrap="CJK", textColor=DARK,
                                 leftIndent=16, spaceAfter=5),
        "cap": ParagraphStyle("cap", fontName=CN, fontSize=9, leading=13.5,
                              alignment=TA_CENTER, wordWrap="CJK", textColor=GRAY,
                              spaceBefore=4, spaceAfter=12, leftIndent=8, rightIndent=8),
        "ref": ParagraphStyle("ref", fontName=CN, fontSize=8.5, leading=12.5,
                              alignment=TA_LEFT, textColor=DARK,
                              leftIndent=16, firstLineIndent=-16, spaceAfter=2),
    }

    def make_img(src, max_ratio=1.0):
        path = os.path.join(assets, src + ".png") if not src.endswith(".png") \
            else os.path.join(assets, src)
        iw, ih = PILImage.open(path).size
        nw, nh = iw / ZOOM, ih / ZOOM
        target = min(nw, CW * max_ratio)
        scale = target / nw
        return Image(path, width=nw * scale, height=nh * scale, hAlign="CENTER")

    story = [Spacer(1, 6)]
    for el in spec["elements"]:
        t = el["type"]
        if t == "spacer":
            story.append(Spacer(1, el.get("h", 6)))
        elif t in ("title", "author", "affil", "abstract", "h1", "h2", "bullet"):
            story.append(Paragraph(el["text"], S[t]))
        elif t == "body":
            sty = S["body"] if el.get("indent", True) else S["body_ni"]
            story.append(Paragraph(el["text"], sty))
        elif t == "image":
            flow = [make_img(el["src"], el.get("max_ratio", 1.0))]
            if el.get("caption"):
                flow.append(Paragraph(el["caption"], S["cap"]))
            story.append(KeepTogether(flow))
        elif t == "equation":
            story.append(KeepTogether([Spacer(1, 3),
                                       make_img(el["src"], el.get("max_ratio", 0.8)),
                                       Spacer(1, 6)]))
        elif t == "reference":
            story.append(Paragraph(esc(el["text"]), S["ref"]))
        elif t == "refs_block":
            for part in re.split(r"(?=\[\d+\]\s)", el["text"].strip()):
                part = part.strip()
                if part:
                    story.append(Paragraph(esc(part), S["ref"]))
        else:
            raise ValueError(f"unknown element type: {t}")

    out = a.out or os.path.join(a.workdir, "output_cn.pdf")

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(CN, 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(PAGE_W / 2, BM * 0.5, str(doc.page))
        canvas.restoreState()

    doc = BaseDocTemplate(out, pagesize=PAGE, leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM,
                          title=spec.get("title", "中文版"))
    frame = Frame(LM, BM, CW, PAGE_H - TM - BM, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])
    doc.build(story)
    print("built:", out)


if __name__ == "__main__":
    main()
