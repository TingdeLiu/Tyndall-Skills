"""Small SVG helpers shared by post build scripts (cover art, inner diagrams).

Usage from a post folder:
    import sys; sys.path.insert(0, r"<skill目录>/scripts")
    from svgkit import *

Palette matches the 「带你看懂X」 survey-promo look: warm paper, ink, terracotta accent, teal.
"""
from xml.sax.saxutils import escape

INK, ACC, MUTED = "#172E3C", "#D95E36", "#68747A"
PAPER, TEAL, LINE = "#F8F5EE", "#147D78", "#D7D2C8"
TINT, TEALT, GOLDT = "#FBE9E1", "#E3F0EC", "#FFF6D9"
FONT = "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif"

__all__ = ["INK", "ACC", "MUTED", "PAPER", "TEAL", "LINE", "TINT", "TEALT", "GOLDT", "FONT",
           "text", "rect", "line", "path", "arrow", "svg", "survey_cover_frame", "reading_guide"]


def text(x, y, value, size=32, fill=INK, weight=400, anchor="start", **attrs):
    extra = " ".join(f'{key.replace("_", "-")}="{val}"' for key, val in attrs.items())
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(str(value))}</text>')


def rect(x, y, w, h, fill, rx=0, stroke="none", sw=1):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def line(x1, y1, x2, y2, stroke, sw=2, dash=""):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-dasharray="{dash}"/>')


def path(d, stroke, sw=4, fill="none", dash=""):
    return (f'<path d="{d}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}" '
            f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{dash}"/>')


def arrow(x1, y1, x2, y2, stroke=MUTED, sw=3):
    """Horizontal or vertical arrow with a small open head."""
    out = line(x1, y1, x2, y2, stroke, sw)
    if x1 == x2:
        s = 1 if y2 > y1 else -1
        out += path(f"M{x2-9},{y2-11*s}L{x2},{y2}L{x2+9},{y2-11*s}", stroke, sw)
    else:
        s = 1 if x2 > x1 else -1
        out += path(f"M{x2-11*s},{y2-9}L{x2},{y2}L{x2-11*s},{y2+9}", stroke, sw)
    return out


def svg(w, h, body, bg=PAPER):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            + rect(0, 0, w, h, bg) + f'<g font-family="{FONT}">' + body + '</g></svg>')


def survey_cover_frame(eyebrow, topic, subtitle, scene, headline, keywords, author, tagline):
    """1080x1440 「带你看懂 / <topic>」 cover. `scene` is SVG drawn inside y≈570–1170.

    topic should be 4 CJK chars at 204px (wider topics: lower the size in a post-local copy).
    """
    b = text(65, 81, eyebrow, 26, INK, 700, letter_spacing="2")
    b += rect(823, 45, 192, 52, ACC, 26) + text(919, 80, "综述导读", 27, "white", 700, "middle")
    b += line(65, 116, 1015, 116, LINE, 2)
    b += text(61, 248, "带你看懂", 106, INK, 700)
    b += text(51, 449, topic, 204, ACC, 700, letter_spacing="5")
    b += text(67, 540, subtitle, 43, INK, 400)
    b += scene
    b += line(65, 1190, 1015, 1190, LINE, 2)
    b += text(65, 1262, headline, 48, INK, 700)
    b += text(67, 1316, keywords, 30, MUTED)
    b += text(65, 1392, author, 27, INK, 700)
    b += text(1015, 1392, tagline, 26, MUTED, 400, "end")
    return svg(1080, 1440, b)


def reading_guide(kicker, routes, search, site, article, author, lead="把零散名词，放回同一张技术地图。"):
    """1080x1440 「先看全景 / 再选方向」 closing page.

    routes: up to 3 tuples (who, sections, path_text). search: blog search keyword.
    """
    fills = [(TINT, ACC), (TEALT, TEAL), (GOLDT, "#A27A12")]
    b = text(65, 87, kicker, 28, ACC, 700)
    b += text(60, 226, "先看全景", 108, INK, 700)
    b += text(60, 367, "再选方向", 108, ACC, 700)
    b += text(67, 438, lead, 34, MUTED)
    y = 500
    for (who, sec, p_), (fill, col) in zip(routes, fills):
        b += rect(65, y, 950, 190, fill, 20)
        b += text(98, y + 70, who, 46, INK, 700)
        b += text(985, y + 70, sec, 34, col, 700, "end")
        b += text(98, y + 136, p_, 29, MUTED)
        y += 210
    b += rect(65, 1150, 950, 210, INK, 20)
    b += text(98, 1204, "完整内容在我的博客 · 浏览器打开", 30, "#D4DFD9")
    b += text(95, 1275, site, 59, "#FFFDF6", 700)
    b += text(98, 1330, f"博客中搜索：{search}", 35, "#FFFDF6", 700)
    b += path("M924,1250h47m-17,-17 18,17 -18,17", "#E9AC86", 4)
    b += text(65, 1411, f"原文《{article}》 · {author}", 24, MUTED)
    return svg(1080, 1440, b)
