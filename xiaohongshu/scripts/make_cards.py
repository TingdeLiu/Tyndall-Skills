# -*- coding: utf-8 -*-
"""从 JSON 配置生成小红书配图（1080x1440 竖版）。

用法:
    python make_cards.py config.json

页面类型:
    cover   封面：两行大标题 + 主数字 + 要点 + 可选 footer；给 hero 则用插图替代主数字
    figure  图文页：kicker + 标题 + 副标题 + 原图 + 可选 stat 块 + 要点
    bar     横向条形图页：自绘对比图 + 要点

约定:
    - bullets 里以 "*" 开头的行 = 加粗高亮行
    - crop_bottom: 裁掉原图底部比例，用于去掉论文自带的英文 Figure caption
    - cta 全局默认值可由页面 cta 覆盖，false 隐藏该页引流条
    - previews: true 输出独立缩略图与手机阅读总览
"""
import argparse
import json
from pathlib import Path
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1440
CTA_TOP = H - 216

BG = (255, 255, 255)
INK = (17, 19, 24)
GREY = (122, 128, 138)
LINE = (232, 234, 238)
SOFT = (248, 249, 251)
MUTE = (216, 219, 225)


def pick_font(bold, configured=None):
    setting = "font_bold" if bold else "font_regular"
    override = configured or os.environ.get("XHS_FONT_BOLD" if bold else "XHS_FONT_REGULAR")
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise SystemExit(f"找不到 {setting} 指定的字体: {path}")
        return str(path)
    if bold:
        cands = [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]
    else:
        cands = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc"]
    cands += ["/System/Library/Fonts/PingFang.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]
    for candidate in cands:
        if os.path.isfile(candidate):
            return candidate
    raise SystemExit(f"找不到中文字体，请设置配置字段 {setting} 或对应的 XHS_FONT 环境变量。")


FB = FR = None


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c, bg, t):
    return tuple(int(a * (1 - t) + b * t) for a, b in zip(c, bg))


def f(path, size):
    return ImageFont.truetype(path, size)


def tw(d, t, fn):
    b = d.textbbox((0, 0), t, font=fn)
    return b[2] - b[0], b[3] - b[1]


class Deck:
    def __init__(self, cfg):
        global FB, FR
        FB, FR = pick_font(True, cfg.get("font_bold")), pick_font(False, cfg.get("font_regular"))
        pages = cfg.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError("pages 必须是非空页面列表")
        for page in pages:
            if page.get("type") not in {"cover", "figure", "bar"}:
                raise ValueError("页面 type 只支持 cover、figure、bar")
            name = page.get("name", page["type"])
            if not isinstance(name, str) or not name or any(c in name for c in '/\\:*?"<>|'):
                raise ValueError("页面 name 应是文件名，不能包含路径或保留字符")
        self.cfg = cfg
        self.src = cfg.get("src_root", "")
        self.out = cfg["out_dir"]
        self.accent = hex2rgb(cfg.get("accent", "#FF5A1F"))
        self.tint = mix(self.accent, (255, 255, 255), 0.90)
        self.cta_cfg = cfg.get("cta")
        self.watermark = cfg.get("watermark", "")
        os.makedirs(self.out, exist_ok=True)

    # ---------- 公共组件 ----------
    def page(self):
        c = Image.new("RGB", (W, H), BG)
        return c, ImageDraw.Draw(c)

    def header(self, d, kicker, title, sub=None):
        y = 74
        if kicker:
            fk = f(FB, 26)
            kw, _ = tw(d, kicker, fk)
            d.rounded_rectangle([60, y, 60 + kw + 40, y + 50], radius=25, fill=self.tint)
            d.text((80, y + 11), kicker, font=fk, fill=self.accent)
            y += 84
        ft = f(FB, 58)
        for ln in title.split("\n"):
            d.text((60, y), ln, font=ft, fill=INK)
            y += 76
        y += 4
        if sub:
            fs = f(FR, 30)
            for ln in sub.split("\n"):
                d.text((60, y), ln, font=fs, fill=GREY)
                y += 44
        return y + 26

    def place(self, canvas, rel, y, max_h=None, crop_bottom=0.0, pad=44, card=True):
        im = Image.open(os.path.join(self.src, rel.lstrip("/\\")))
        if im.mode != "RGB":
            im = im.convert("RGBA")
            b = Image.new("RGB", im.size, (255, 255, 255))
            b.paste(im, mask=im.split()[-1])
            im = b
        if crop_bottom > 0:
            im = im.crop((0, 0, im.width, int(im.height * (1 - crop_bottom))))
        sc = (W - pad * 2) / im.width
        nh = int(im.height * sc)
        if max_h and nh > max_h:
            sc, nh = max_h / im.height, max_h
        nw = int(im.width * sc)
        im = im.resize((nw, nh), Image.LANCZOS)
        x = (W - nw) // 2
        if card:
            ImageDraw.Draw(canvas).rounded_rectangle(
                [x - 12, y - 12, x + nw + 12, y + nh + 12],
                radius=18, fill=(255, 255, 255), outline=LINE, width=2)
        canvas.paste(im, (x, y))
        return y + nh

    def stat(self, d, y, big, unit, title, sub):
        """大数字强调块，如 22x / 训练 Token 消耗直降"""
        d.rounded_rectangle([56, y, W - 56, y + 150], radius=20, fill=SOFT)
        d.text((96, y + 30), big, font=f(FB, 92), fill=self.accent)
        bw, _ = tw(d, big, f(FB, 92))
        uw = 0
        if unit:
            d.text((96 + bw + 8, y + 62), unit, font=f(FB, 52), fill=self.accent)
            uw, _ = tw(d, unit, f(FB, 52))
            uw += 8
        tx = max(300, 96 + bw + uw + 28)      # 数字过宽时把文案右推，避免压字
        d.text((tx, y + 34), title, font=f(FB, 34), fill=INK)
        d.text((tx, y + 82), sub, font=f(FR, 26), fill=GREY)
        return y + 150

    def bullets(self, d, y_top, lines, y_bottom=None, gap=None):
        """在剩余空间里垂直居中，行距自适应，避免大片留白"""
        if not lines:
            return y_top
        fcb, fc = f(FB, 29), f(FR, 29)
        yb = y_bottom if y_bottom is not None else (CTA_TOP if self.cta_cfg else H - 90)
        space = yb - y_top
        if gap is None:
            gap = min(74, max(46, int((space - 48) / len(lines))))
        y = y_top + max(30, (space - gap * len(lines)) // 2)
        for ln in lines:
            bold = ln.startswith("*")
            ln = ln.lstrip("*")
            d.rectangle([60, y + 10, 66, y + 36], fill=self.accent if bold else MUTE)
            d.text((84, y), ln, font=fcb if bold else fc, fill=INK if bold else GREY)
            y += gap
        return y

    def footer(self, d):
        if self.cta_cfg:
            d.rounded_rectangle([56, CTA_TOP, W - 56, CTA_TOP + 118], radius=20, fill=self.tint)
            d.text((88, CTA_TOP + 24), self.cta_cfg["title"], font=f(FB, 33),
                   fill=mix(self.accent, (0, 0, 0), 0.22))
            d.text((88, CTA_TOP + 72), self.cta_cfg["sub"], font=f(FR, 26),
                   fill=mix(mix(self.accent, (0, 0, 0), 0.22), (255, 255, 255), 0.32))
        if self.watermark:
            d.text((60, H - 58), self.watermark, font=f(FR, 24), fill=(196, 200, 206))

    # ---------- 页面类型 ----------
    def cover(self, p):
        c, d = self.page()
        d.rectangle([0, 0, W, 14], fill=self.accent)
        y = 132
        d.text((60, y), p["line1"], font=f(FB, 66), fill=INK)
        y += 94
        d.text((60, y), p["line2"], font=f(FB, 66), fill=self.accent)
        y += 116
        if p.get("hero"):
            # 插图封面：hero 图替代主数字块，要点一般并入插图
            if p.get("hero_label"):
                d.text((60, y), p["hero_label"], font=f(FR, 34), fill=GREY)
                y += 74
            y = self.place(c, p["hero"], y + 12, max_h=p.get("max_h", 700)) + 46
            d = ImageDraw.Draw(c)
        if p.get("metric"):
            d.text((60, y), p.get("metric_label", ""), font=f(FR, 34), fill=GREY)
            y += 54
            d.text((56, y), p["metric"], font=f(FB, 196), fill=INK)
            w0, _ = tw(d, p["metric"], f(FB, 196))
            d.text((56 + w0 + 16, y + 106), p.get("metric_unit", ""),
                   font=f(FB, 70), fill=self.accent)
            y += 244
            d.line([60, y, W - 60, y], fill=LINE, width=2)
            y += 34
        for t, s in p.get("points", []):
            d.rectangle([60, y + 10, 66, y + 42], fill=self.accent)
            d.text((84, y), t, font=f(FB, 37), fill=INK)
            y += 50
            d.text((84, y), s, font=f(FR, 27), fill=GREY)
            y += 66
        if p.get("footer"):
            y += 10
            d.rounded_rectangle([60, y, W - 60, y + 104], radius=18, fill=SOFT)
            d.text((88, y + 20), p["footer"][0], font=f(FB, 34), fill=INK)
            d.text((88, y + 62), p["footer"][1], font=f(FR, 26), fill=GREY)
        self.footer(d)
        return c

    def figure(self, p):
        c, d = self.page()
        y = self.header(d, p.get("kicker"), p["title"], p.get("sub"))
        y = self.place(c, p["image"], y, max_h=p.get("max_h", 620),
                       crop_bottom=p.get("crop_bottom", 0.0))
        d = ImageDraw.Draw(c)
        if p.get("stat"):
            s = p["stat"]
            y = self.stat(d, y + 46, s["big"], s.get("unit", ""), s["title"], s["sub"])
        self.bullets(d, y, p.get("bullets", []))
        self.footer(d)
        return c

    def bar(self, p):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        from matplotlib.patches import Patch

        font_manager.fontManager.addfont(FR)
        plt.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=FR).get_name()]
        plt.rcParams["axes.unicode_minus"] = False

        acc = "#%02X%02X%02X" % self.accent
        C = {"ours": acc, "other": "#94A3B8", "alt": "#CBD5E1"}
        series = p["series"]                      # [[name, value, kind], ...] 由低到高
        names = [s[0] for s in series]
        vals = [s[1] for s in series]

        fig, ax = plt.subplots(figsize=tuple(p.get("figsize", [9.6, 6.0])), dpi=110)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        bars = ax.barh(names, vals, height=0.68, zorder=3, edgecolor="none",
                       color=[C[s[2]] for s in series])
        span = max(vals) - min(vals) or 1
        for b, s in zip(bars, series):
            ours = s[2] == "ours"
            ax.text(s[1] + span * 0.025, b.get_y() + b.get_height() / 2,
                    p.get("value_fmt", "{}%").format(s[1]), va="center", ha="left", zorder=4,
                    fontsize=15 if ours else 13, fontweight="bold" if ours else "normal",
                    color=acc if ours else "#4B5563")
        if p.get("xlim"):
            ax.set_xlim(*p["xlim"])
        ax.tick_params(axis="y", length=0, labelsize=14)
        ax.tick_params(axis="x", length=0, labelsize=12, colors="#9CA3AF")
        for lbl, s in zip(ax.get_yticklabels(), series):
            if s[2] == "ours":
                lbl.set_fontweight("bold")
                lbl.set_color(acc)
                lbl.set_fontsize(16)
            else:
                lbl.set_color("#374151")
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color("#E5E7EB")
        ax.grid(axis="x", color="#F1F3F5", zorder=0)
        ax.set_xlabel(p.get("xlabel", ""), fontsize=13, color="#6B7280", labelpad=12)
        lg = p.get("legend")
        if lg:
            ax.legend(handles=[Patch(color=C[k], label=v) for k, v in lg.items()],
                      loc=p.get("legend_loc", "lower right"), frameon=False,
                      fontsize=12, labelcolor="#4B5563")
        plt.tight_layout()
        tmp = os.path.join(self.out, "_chart_tmp.png")
        plt.savefig(tmp, dpi=110, facecolor="white")
        plt.close()

        c, d = self.page()
        y = self.header(d, p.get("kicker"), p["title"], p.get("sub"))
        im = Image.open(tmp).convert("RGB")
        sc = (W - 100) / im.width
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        c.paste(im, ((W - im.width) // 2, y))
        d = ImageDraw.Draw(c)
        self.bullets(d, y + im.height + 24, p.get("bullets", []))
        self.footer(d)
        os.remove(tmp)
        return c

    def run(self):
        made = []
        default_cta = self.cta_cfg
        for i, p in enumerate(self.cfg["pages"], 1):
            self.cta_cfg = p.get("cta", default_cta)
            try:
                img = getattr(self, p["type"])(p)
            finally:
                self.cta_cfg = default_cta
            name = "%02d-%s.png" % (i, p.get("name", p["type"]))
            img.save(os.path.join(self.out, name))
            made.append(name)
        if self.cfg.get("previews") and made:
            self.previews(made)
        return made

    def previews(self, made):
        """独立目录存放阅读预览，不混入发布图片。"""
        dest = os.path.join(self.out, "_previews")
        os.makedirs(dest, exist_ok=True)
        width, height, pad, label_h = 360, 480, 20, 38
        cols = min(3, len(made))
        rows = (len(made) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (width + pad) + pad,
                                  rows * (height + label_h + pad) + pad), SOFT)
        draw = ImageDraw.Draw(sheet)
        for i, name in enumerate(made):
            with Image.open(os.path.join(self.out, name)) as source:
                small = source.convert("RGB").resize((width, height), Image.LANCZOS)
                if i == 0:
                    source.resize((240, 320), Image.LANCZOS).save(
                        os.path.join(dest, "cover-240.png"))
            small.save(os.path.join(dest, name))
            x = pad + (i % cols) * (width + pad)
            y = pad + (i // cols) * (height + label_h + pad)
            sheet.paste(small, (x, y))
            draw.text((x, y + height + 6), str(i + 1), font=f(FR, 24), fill=INK)
        sheet.save(os.path.join(dest, "overview.png"))


def load_config(path):
    """Resolve all relative file paths from the JSON file, not the caller's cwd."""
    config_path = Path(path).expanduser().resolve()
    with config_path.open(encoding="utf-8-sig") as handle:
        config = json.load(handle)
    for key in ("src_root", "out_dir", "font_regular", "font_bold"):
        value = config.get(key)
        if value is None:
            if key != "src_root":
                continue
            value = "."
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = config_path.parent / candidate
        config[key] = str(candidate.resolve())
    return config


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="从 JSON 生成 1080×1440 图文卡片及独立阅读预览")
    parser.add_argument("config", help="配置文件路径；配置内相对路径以该文件所在目录为准")
    args = parser.parse_args()
    try:
        conf = load_config(args.config)
        for name in Deck(conf).run():
            print("saved", name)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"错误: {exc}\n")
