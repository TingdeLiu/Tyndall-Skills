#!/usr/bin/env python3
"""给 items/ 里的历史条目补算「领域」字段（导航 / 具身Agent / 自动驾驶 / VLA·操作 / 其他）。

「领域」是 2026-09-19 加的分池标签，此前抓的条目都没有这一行；而且分池规则
本身还会随实测调整（已经改过三轮），每次调完都要把存量重算一遍，否则
index.md 的主池计数和周报的筛选依据就和当前规则对不上。

用法:
    python backfill_domain.py --out <资料库目录> --dry-run   # 先看影响面
    python backfill_domain.py --out <资料库目录>

字段插在「- 基准:」之后、「## 摘要」之前，与 fetch_vln.py 写新条目时的位置一致。
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_vln import detect_domain, rebuild_index, PRIMARY_DOMAINS  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def split_sections(text: str) -> tuple[list[str], str]:
    """拆成（头部元信息行, 其余全文）。头部止于第一个空行后的 '## '。"""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            return lines[:i], "\n".join(lines[i:])
    return lines, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="资料库目录（含 items/）")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = ap.parse_args()

    out = Path(args.out)
    items_dir = out / "items"
    if not items_dir.is_dir():
        sys.exit(f"找不到 {items_dir}")

    changed, added = 0, 0
    stat = collections.Counter()
    moves = collections.Counter()

    for md in sorted(items_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        head, body = split_sections(text)
        title = head[0][2:].strip() if head and head[0].startswith("# ") else md.stem
        # 摘要与正文都参与判定，与 fetch_vln.write_item 保持一致
        domain = detect_domain(title, body)
        stat[domain] += 1

        old = next((ln[len("- 领域: "):].strip() for ln in head
                    if ln.startswith("- 领域: ")), None)
        if old == domain:
            continue
        if old is None:
            added += 1
        else:
            changed += 1
            moves[f"{old} -> {domain}"] += 1

        head = [ln for ln in head if not ln.startswith("- 领域: ")]
        # 插在最后一个元信息行之后（元信息行以 "- " 开头）
        last = max((i for i, ln in enumerate(head) if ln.startswith("- ")),
                   default=0)
        head.insert(last + 1, f"- 领域: {domain}")
        if not args.dry_run:
            md.write_text("\n".join(head) + "\n" + body, encoding="utf-8")

    print(f"扫描 {sum(stat.values())} 条：新增字段 {added}，改判 {changed}")
    if moves:
        print("\n改判分布：")
        for k, v in moves.most_common(12):
            print(f"  {k}: {v}")
    print("\n分池结果：")
    for k, v in stat.most_common():
        print(f"  {k:<10} {v}")
    print(f"\n主池（导航 + 具身Agent）= {sum(stat[d] for d in PRIMARY_DOMAINS)} 条")

    if args.dry_run:
        print("\n(dry-run：未写入任何文件)")
    else:
        total = rebuild_index(items_dir, out / "index.md")
        print(f"\n索引已重建：{total} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
