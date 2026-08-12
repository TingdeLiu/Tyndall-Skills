# -*- coding: utf-8 -*-
"""
Step 2: Crop figures / tables / equations from the ORIGINAL pdf as PNGs.

Usage:
    python crop_regions.py <input.pdf> <workdir>

Reads <workdir>/crops.json:
    {
      "zoom": 4.0,                       # render scale (~72*zoom dpi); 4.0 == 288 dpi
      "crops": {
        "fig1": {"page": 2, "rect": [54, 50, 558, 300]},
        "tab1": {"page": 3, "rect": [314, 78, 557, 184]},
        "eq3":  {"page": 4, "rect": [355, 703, 558, 737]}
      }
    }
    (page is 1-based; rect is [x0,y0,x1,y1] in PDF points.)

Writes <workdir>/assets/<name>.png for every crop.
Keeps the original pixels -> figures/tables/equations stay pixel-perfect.
"""
import fitz, json, os, sys, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("workdir")
    a = ap.parse_args()

    spec_path = os.path.join(a.workdir, "crops.json")
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    zoom = float(spec.get("zoom", 4.0))
    mat = fitz.Matrix(zoom, zoom)

    assets = os.path.join(a.workdir, "assets")
    os.makedirs(assets, exist_ok=True)
    doc = fitz.open(a.pdf)

    for name, c in spec["crops"].items():
        pg = doc[int(c["page"]) - 1]
        clip = fitz.Rect(*c["rect"])
        pix = pg.get_pixmap(matrix=mat, clip=clip)
        path = os.path.join(assets, name + ".png")
        pix.save(path)
        w = c["rect"][2] - c["rect"][0]
        h = c["rect"][3] - c["rect"][1]
        print(f"{name}: {pix.width}x{pix.height}px  ({w:.0f}x{h:.0f}pt)  p{c['page']}")
    print(f"-> {assets}")


if __name__ == "__main__":
    main()
