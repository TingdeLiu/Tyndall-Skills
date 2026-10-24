#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
刷新主篇「前列模型技术方案分析」下的「要素打勾矩阵」与「统计研判」。

矩阵的收录范围由排行榜 ①（R2R-CE）决定：SR ≥ 60% 且非灰显（不带 lb-flag，如 100 条子集）
的每一行都应在矩阵里有一行。子集成绩样本太少（100 条时标准误约 ±4.5 个点），不参与矩阵统计。
矩阵是排行榜的下游，排行榜一变（插入新论文、改数字、调篇）矩阵就会过期，本脚本负责
其中机械的部分：

  - 对账：排行榜 ① 中 SR ≥ 60 的行 ⇄ 矩阵行（按锚点匹配，同一锚点多行时按配置 / SR 区分）
  - 同步：矩阵行的 SR、链接（调篇后变成跨页链接）、开源列跟随排行榜
  - 删除：已不在排行榜 ① SR ≥ 60 里的矩阵行
  - 新增：用 --add 给出新行的打勾（打勾需要读论文判断，脚本不猜）
  - 重排：按 SR 降序重排并重编排名
  - 重算：矩阵底部「统计」行、「统计研判」里的两档对比表、以及正文里的条目计数

研判正文里的百分比、举例和结论是人写的，脚本只会打印新旧两档对比，提醒人工对照改写。

用法:
    python refresh_matrix.py [--check] [--add SPEC ...] [--blog PATH]

    --check  只报告，不写文件（有任何待改动或缺行时退出码 1）
    --add    新增一行矩阵，SPEC 为分号分隔的 key=value：
               anchor=<锚点>        必填，排行榜行链接里的 #anchor
               yes=<列1>,<列2>...   打 ✓ 的列，写列名前缀即可，如 堆相机,双系统,像素,强化学习,DAgger
               cfg=<配置>           可选，括号里的相机配置，如 三相机；缺省沿用排行榜名里的括号
               name=<显示名>        可选，缺省为排行榜名去掉括号
               sr=<SR>              可选，同一锚点在排行榜有多行（如全景 / 单目）时用来指定是哪一行
             「开源」列缺省跟随排行榜的开源列，也可以在 yes 里显式写上。

示例:
    python refresh_matrix.py --check
    python refresh_matrix.py --add "anchor=groundingvln;cfg=三相机;yes=堆相机,双系统,像素,强化学习"
"""
import argparse
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# skill 经 GitHub 同步到多台电脑，博客仓库位置不同：按顺序取本机存在的那个
# 博客仓库根目录：优先读环境变量 BLOG_ROOT，否则用当前目录
BLOG_ROOT = Path(os.environ.get('BLOG_ROOT') or Path.cwd())
DEFAULT_BLOG = BLOG_ROOT / "_posts/research/2026-01-05-VLN-Papers.md"

LB_HEADING = "## ① R2R-CE"
MATRIX_HEADING = "## 要素打勾矩阵"
ANALYSIS_HEADING = "## 统计研判"
MIN_SR = 60.0

LINK_RE = re.compile(r"\[(\*\*)?(.+?)(\*\*)?\]\(([^)]+)\)")
CFG_RE = re.compile(r"^(.*?)\s*[（(]([^（）()]*)[)）]\s*$")
YES, NO = "✓", "–"


def read(path):
    raw = path.read_bytes().decode("utf-8")
    return raw, ("\r\n" if "\r\n" in raw else "\n")


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def num(cell):
    c = cell.replace("*", "").replace("%", "").replace("≈", "").strip()
    try:
        return float(c)
    except ValueError:
        return None


def split_cfg(text):
    """'Qwen-RobotNav(全景)' -> ('Qwen-RobotNav', '全景')；无括号时 cfg 为空"""
    m = CFG_RE.match(text)
    return (m.group(1).strip(), m.group(2).strip()) if m else (text.strip(), "")


def norm(s):
    return re.sub(r"\s+", "", s or "")


def section(lines, heading):
    """返回 heading 所在行号到下一个同级（##）或更高级标题之前的行号区间"""
    start = next((i for i, l in enumerate(lines) if l.strip() == heading), None)
    if start is None:
        sys.exit(f"错误: 找不到标题「{heading}」")
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("## ") or lines[i].startswith("# ")), len(lines))
    return start, end


def table_rows(lines, start, end, header_pred):
    """在 [start, end) 中找第一张表头满足 header_pred 的表，返回 (表头行号, 数据起止行号)"""
    for i in range(start, end):
        if lines[i].lstrip().startswith("|") and header_pred(cells(lines[i])):
            j = i + 2
            k = j
            while k < end and lines[k].lstrip().startswith("|"):
                k += 1
            return i, j, k
    return None


def parse_leaderboard(lines):
    s, e = section(lines, LB_HEADING)
    found = table_rows(lines, s, e, lambda c: c and c[0] == "模型")
    if not found:
        sys.exit("错误: 排行榜 ① 找不到表头")
    h, j, k = found
    # 按表头取列（① 的列序是 模型 | 年份 | 范式 | 基模 | SR | SPL | NE | OSR | 开源，改列时这里不用跟着改）
    col = {c.split(" ")[0]: n for n, c in enumerate(cells(lines[h]))}
    if "SR" not in col or "开源" not in col:
        sys.exit("错误: 排行榜 ① 表头缺少 SR 或 开源 列")
    rows = []
    for i in range(j, k):
        c = cells(lines[i])
        m = LINK_RE.search(c[0])
        sr = num(c[col["SR"]]) if len(c) > col["SR"] else None
        if not m or sr is None or sr < MIN_SR:
            continue
        # 灰显行（lb-flag，如 100 条子集）样本太少、口径不同，不进矩阵
        if "lb-flag" in c[0]:
            continue
        name, cfg = split_cfg(m.group(2))
        href = m.group(4)
        rows.append({
            "name": name, "cfg": cfg, "href": href,
            "anchor": href.split("#")[-1], "sr": sr,
            "open": "是" in (c[col["开源"]] if len(c) > col["开源"] else ""),
        })
    return rows


def parse_matrix(lines):
    s, e = section(lines, MATRIX_HEADING)
    found = table_rows(lines, s, e, lambda c: c and c[0] == "排名")
    if not found:
        sys.exit("错误: 矩阵找不到「| 排名 |」表头")
    h, j, k = found
    header = cells(lines[h])
    cols = header[3:]
    rows, stat_idx = [], None
    for i in range(j, k):
        c = cells(lines[i])
        if c[0].replace("*", "") == "统计":
            stat_idx = i
            continue
        m = LINK_RE.search(c[1])
        if not m:
            sys.exit(f"错误: 矩阵第 {i + 1} 行解析不出模型链接: {lines[i][:60]}")
        rest = c[1][m.end():].strip()
        cm = re.match(r"^[（(](.*)[)）]$", rest)
        ticks = c[3:3 + len(cols)]
        if len(ticks) != len(cols) or any(t not in (YES, NO) for t in ticks):
            sys.exit(f"错误: 矩阵第 {i + 1} 行打勾列数或符号不对（只允许 {YES} / {NO}）")
        rows.append({
            "name": m.group(2), "href": m.group(4), "anchor": m.group(4).split("#")[-1],
            "cfg": cm.group(1) if cm else "", "sr": num(c[2]), "ticks": ticks,
        })
    return {"header_idx": h, "start": j, "end": k, "stat_idx": stat_idx,
            "cols": cols, "rows": rows}


def short(col):
    """'堆数据 (≥1M)' -> '堆数据'"""
    return re.split(r"\s+[（(]", col)[0].strip()


def resolve_cols(tokens, cols):
    idx = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        hits = [i for i, c in enumerate(cols) if t.lower() in short(c).lower()]
        if len(hits) != 1:
            names = "、".join(short(c) for c in cols)
            sys.exit(f"错误: 列名「{t}」匹配到 {len(hits)} 列，可选列: {names}")
        idx.append(hits[0])
    return idx


def parse_add(spec):
    f = {}
    for part in spec.split(";"):
        if part.strip():
            if "=" not in part:
                sys.exit(f"错误: --add 字段应为 key=value: {part!r}")
            k, v = part.split("=", 1)
            f[k.strip().lower()] = v.strip()
    if "anchor" not in f:
        sys.exit(f"错误: --add 缺少 anchor: {spec!r}")
    return f


def match(lb_rows, mx_rows):
    """返回 (pairs, 未匹配排行榜行, 待删矩阵行)；pairs 为 (矩阵行, 排行榜行)"""
    used, pairs, drop = set(), [], []
    for r in mx_rows:
        cands = [i for i, l in enumerate(lb_rows) if l["anchor"] == r["anchor"] and i not in used]
        pick = None
        if len(cands) == 1:
            pick = cands[0]
        elif cands:
            pick = next((i for i in cands if norm(lb_rows[i]["cfg"]) == norm(r["cfg"])), None)
            if pick is None:
                pick = next((i for i in cands if round(lb_rows[i]["sr"], 1) == round(r["sr"], 1)), None)
        if pick is None:
            drop.append(r)
        else:
            used.add(pick)
            pairs.append((r, lb_rows[pick]))
    missing = [l for i, l in enumerate(lb_rows) if i not in used]
    return pairs, missing, drop


def pct(a, b):
    return f"{a}/{b} ({round(100 * a / b) if b else 0}%)"


def render_matrix_row(rank, r):
    cfg = f" ({r['cfg']})" if r["cfg"] else ""
    ticks = " | ".join(r["ticks"])
    return f"| {rank} | [**{r['name']}**]({r['href']}){cfg} | **{r['sr']:.1f}%** | {ticks} |"


def render_stat_row(rows, cols):
    n = len(rows)
    counts = [sum(r["ticks"][j] == YES for r in rows) for j in range(len(cols))]
    top = max(r["sr"] for r in rows)
    cells_ = " | ".join(f"**{pct(c, n)}**" for c in counts)
    return f"| **统计** | **各要素采纳频次** | **最高 {top:.1f}%** | {cells_} |"


def refresh_tiers(lines, rows, cols, report):
    """重算「统计研判」里的两档对比表；返回 [(要素, 旧一档, 新一档, 旧二档, 新二档)]"""
    s, e = section(lines, ANALYSIS_HEADING)
    found = table_rows(lines, s, e, lambda c: c and c[0] == "要素" and len(c) >= 4)
    if not found:
        report.append("  ⚠ 统计研判里没找到两档对比表，跳过")
        return []
    h, j, k = found
    head = cells(lines[h])
    m = re.search(r"SR\s*≥\s*(\d+(?:\.\d+)?)%", head[1])
    if not m:
        report.append("  ⚠ 两档对比表表头里读不出分档阈值（SR ≥ X%），跳过")
        return []
    t = float(m.group(1))
    t_txt = m.group(1)
    top = [r for r in rows if r["sr"] >= t]
    low = [r for r in rows if r["sr"] < t]
    lo_txt = f"{MIN_SR:g}"
    lines[h] = (f"| 要素 | 第一梯队（SR ≥ {t_txt}%，{len(top)} 个） | "
                f"第二梯队（{lo_txt}%–{t_txt}%，{len(low)} 个） | 合计（{len(rows)} 个） |")

    changes = []
    for i in range(j, k):
        c = cells(lines[i])
        label = c[0].replace("*", "").strip()
        bold = c[0].startswith("**")
        hits = [x for x, col in enumerate(cols)
                if norm(label) in norm(short(col)) or norm(short(col)) in norm(label)]
        if len(hits) != 1:
            report.append(f"  ⚠ 两档对比表的「{label}」对不上矩阵列，保持原样")
            continue
        x = hits[0]
        a = sum(r["ticks"][x] == YES for r in top)
        b = sum(r["ticks"][x] == YES for r in low)
        tot = a + b
        ta, tb = pct(a, len(top)), pct(b, len(low))
        if bold:
            ta, tb = f"**{ta}**", f"**{tb}**"
        new = f"| {c[0]} | {ta} | {tb} | {pct(tot, len(rows))} |"
        if new != lines[i]:
            changes.append((label, c[1].replace("*", ""), ta.replace("*", ""),
                            c[2].replace("*", ""), tb.replace("*", "")))
        lines[i] = new

    # 正文「以 68% 为界把 23 个条目分成两档」
    for i in range(s, e):
        lines[i] = re.sub(r"(以 \d+(?:\.\d+)?% 为界把 )\d+( 个条目)", rf"\g<1>{len(rows)}\g<2>", lines[i])
    return changes


def refresh_intro(lines, rows, report):
    s, e = section(lines, MATRIX_HEADING)
    n, anchors = len(rows), {}
    for r in rows:
        anchors.setdefault(r["anchor"], []).append(r)
    dup = {a: v for a, v in anchors.items() if len(v) > 1}
    for i in range(s, e):
        if "个条目" not in lines[i]:
            continue
        new = re.sub(r"全部 \d+ 个条目（\d+ 个模型", f"全部 {n} 个条目（{len(anchors)} 个模型", lines[i])
        new = re.sub(r"全部 \d+ 个条目(?!（)", f"全部 {n} 个条目", new)
        lines[i] = new
        if "（" in new and not dup:
            report.append("  ⚠ 引言括号里说明了「同一模型多配置分列」，但现在没有重复锚点，请手工删改")
        elif dup:
            names = "、".join(v[0]["name"] for v in dup.values())
            report.append(f"  · 多配置分列的模型: {names}（引言括号里的说明请确认仍然准确）")
        break


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="只检查，不写入")
    ap.add_argument("--add", action="append", default=[], help="新增矩阵行（可重复）")
    ap.add_argument("--blog", type=Path, default=DEFAULT_BLOG, help="主篇路径")
    args = ap.parse_args()

    if not args.blog.exists():
        sys.exit(f"错误: 找不到 {args.blog}")
    raw, nl = read(args.blog)
    lines = raw.replace("\r\n", "\n").split("\n")

    lb = parse_leaderboard(lines)
    mx = parse_matrix(lines)
    cols = mx["cols"]
    open_col = next((j for j, c in enumerate(cols) if "开源" in c), None)

    pairs, missing, drop = match(lb, mx["rows"])
    report = []

    # 同步已有行：SR / 链接 / 开源跟随排行榜
    rows = []
    for r, l in pairs:
        if round(r["sr"], 1) != round(l["sr"], 1):
            report.append(f"  ~ SR   {r['name']} ({r['cfg']}): {r['sr']} -> {l['sr']}")
            r["sr"] = l["sr"]
        if r["href"] != l["href"]:
            report.append(f"  ~ 链接 {r['name']}: {r['href']} -> {l['href']}")
            r["href"] = l["href"]
        if open_col is not None:
            want = YES if l["open"] else NO
            if r["ticks"][open_col] != want:
                report.append(f"  ~ 开源 {r['name']}: {r['ticks'][open_col]} -> {want}")
                r["ticks"][open_col] = want
        rows.append(r)

    for r in drop:
        report.append(f"  - 删除 {r['name']} ({r['cfg']}) {r['sr']}%：排行榜 ① 里已没有对应的 SR ≥ {MIN_SR:g} 行")

    # 新增行
    for spec in args.add:
        f = parse_add(spec)
        cands = [l for l in missing if l["anchor"] == f["anchor"]]
        if "sr" in f:
            cands = [l for l in cands if round(l["sr"], 1) == round(float(f["sr"]), 1)]
        if len(cands) != 1:
            have = [l for l in lb if l["anchor"] == f["anchor"]]
            if have and not cands:
                sys.exit(f"错误: #{f['anchor']} 已在矩阵中，无需 --add")
            sys.exit(f"错误: --add #{f['anchor']} 在排行榜 ① SR ≥ {MIN_SR:g} 的待补行里匹配到 "
                     f"{len(cands)} 行（同一锚点多行时加 sr= 区分）")
        l = cands[0]
        missing.remove(l)
        yes = set(resolve_cols(f.get("yes", "").split(","), cols))
        ticks = [YES if j in yes else NO for j in range(len(cols))]
        if open_col is not None and open_col not in yes:
            ticks[open_col] = YES if l["open"] else NO
        r = {"name": f.get("name", l["name"]), "href": l["href"], "anchor": l["anchor"],
             "cfg": f.get("cfg", l["cfg"]), "sr": l["sr"], "ticks": ticks}
        if not r["cfg"]:
            report.append(f"  ⚠ {r['name']} 没有相机配置括号，建议用 cfg= 补上（如 单目 / 多目 / 全景）")
        report.append(f"  + 新增 {render_matrix_row('?', r)}")
        rows.append(r)

    if missing:
        print(f"排行榜 ① 中有 {len(missing)} 行 SR ≥ {MIN_SR:g} 但矩阵里没有，需要读论文后用 --add 补打勾：")
        for l in missing:
            cfg = f"({l['cfg']})" if l["cfg"] else ""
            print(f"  ? {l['name']}{cfg} #{l['anchor']}  SR {l['sr']}  开源 {'是' if l['open'] else '否'}")
            print(f"      --add \"anchor={l['anchor']}"
                  f"{';sr=' + format(l['sr'], 'g') if sum(x['anchor'] == l['anchor'] for x in lb) > 1 else ''}"
                  f"{';cfg=' + l['cfg'] if l['cfg'] else ';cfg=<单目/多目/全景>'};yes=<列,列,...>\"")
        print(f"可选列: {'、'.join(short(c) for c in cols)}")
        if report:
            print("\n其余待改动：")
            print("\n".join(report))
        sys.exit(1)

    rows.sort(key=lambda r: -r["sr"])
    body = [render_matrix_row(i, r) for i, r in enumerate(rows, 1)]
    body.append(render_stat_row(rows, cols))

    new_lines = lines[:mx["start"]] + body + lines[mx["end"]:]
    tier_changes = refresh_tiers(new_lines, rows, cols, report)
    refresh_intro(new_lines, rows, report)

    changed = new_lines != lines
    print(f"矩阵 {len(rows)} 行（排行榜 ① SR ≥ {MIN_SR:g} 共 {len(lb)} 行）")
    if report:
        print("\n".join(report))
    if tier_changes:
        print("\n两档对比表有变化，「统计研判」正文里引用的百分比和举例需要人工对照更新：")
        for label, oa, na, ob, nb in tier_changes:
            print(f"  {label}: 第一梯队 {oa} -> {na} | 第二梯队 {ob} -> {nb}")

    if not changed:
        print("已是最新")
        return
    if args.check:
        print("\n[check] 需要刷新，未写入")
        sys.exit(1)
    args.blog.write_bytes("\n".join(new_lines).replace("\n", nl).encode("utf-8"))
    print("\n已写入")


if __name__ == "__main__":
    main()
