# -*- coding: utf-8 -*-
"""
Step 1: Extract text blocks + page previews from an English paper PDF.

Usage:
    python extract_blocks.py <input.pdf> <workdir> [--dpi 100]

Outputs (in <workdir>):
    blocks.json      : per-page text blocks with bbox / font / size / heuristics
    preview/pN.png   : full-page renders (for the model to SEE the layout)
    image_rects.json : embedded raster image placement rects (figure candidates)

The model then reads blocks.json + previews to (a) translate prose and
(b) decide crop rectangles for figures / tables / equations.
"""
import fitz, json, re, os, sys, argparse

MATH_FONTS = ("CM", "MSAM", "MSBM", "StandardSymL", "CMEX", "CMMI", "CMR",
              "CMSY", "MSA", "MSB", "EUSM", "EUFM")


def looks_math(fonts):
    return any(any(f.startswith(m) for m in MATH_FONTS) for f in fonts)


def ascii_ratio(t):
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if ord(c) < 128) / len(letters)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("workdir")
    ap.add_argument("--dpi", type=int, default=100)
    a = ap.parse_args()

    os.makedirs(a.workdir, exist_ok=True)
    prev = os.path.join(a.workdir, "preview")
    os.makedirs(prev, exist_ok=True)
    doc = fitz.open(a.pdf)

    out, rects = [], []
    for pno in range(doc.page_count):
        page = doc[pno]
        d = page.get_text("dict")
        blocks = []
        for b in d["blocks"]:
            if b.get("type", 0) != 0:
                continue
            txt, sizes, fonts, bold = "", [], set(), False
            for line in b["lines"]:
                for sp in line["spans"]:
                    txt += sp["text"]
                    sizes.append(round(sp["size"], 1))
                    fonts.add(sp["font"])
                    if sp["flags"] & 16:
                        bold = True
                txt += " "
            txt = re.sub(r"\s+", " ", txt).strip()
            if not txt:
                continue
            sz = max(set(sizes), key=sizes.count) if sizes else 0
            blocks.append({
                "bbox": [round(x, 1) for x in b["bbox"]],
                "size": sz, "bold": bold, "fonts": sorted(fonts),
                "is_math": looks_math(fonts),
                "ascii_ratio": round(ascii_ratio(txt), 2),
                "nchars": len(txt), "text": txt,
            })
        out.append({"page": pno + 1,
                    "width": round(page.rect.width, 1),
                    "height": round(page.rect.height, 1),
                    "blocks": blocks})
        # image placement rects (figure candidates)
        for im in page.get_image_info(xrefs=True):
            x0, y0, x1, y1 = im["bbox"]
            rects.append({"page": pno + 1, "xref": im["xref"],
                          "rect": [round(x0), round(y0), round(x1), round(y1)]})
        page.get_pixmap(dpi=a.dpi).save(os.path.join(prev, f"p{pno+1}.png"))

    with open(os.path.join(a.workdir, "blocks.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.workdir, "image_rects.json"), "w", encoding="utf-8") as f:
        json.dump(rects, f, ensure_ascii=False, indent=1)

    print(f"pages={doc.page_count} blocks={sum(len(p['blocks']) for p in out)} "
          f"figures={len(rects)}")
    print(f"-> {os.path.join(a.workdir,'blocks.json')}")
    print(f"-> {os.path.join(a.workdir,'image_rects.json')}")
    print(f"-> {prev}\\p*.png")


if __name__ == "__main__":
    main()
