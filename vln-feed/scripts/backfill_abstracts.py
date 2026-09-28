#!/usr/bin/env python3
"""
backfill_abstracts — 回填被截断的 arXiv 摘要，并补全条目的「基准」字段。

背景：2026-08-22 之前 fetch_vln.py 把所有源的摘要硬截断在 1200 字符，
而 arXiv 摘要通常 1000~2500 字符，实验结果（R2R-CE / SR / SPL 等数字）
恰好落在摘要末尾被切掉，导致按指标筛选出现假阴性。fetch_vln.py 已修，
本脚本负责把历史条目补回来。

行为：
  - type: arxiv 且带 arxiv.org 链接的条目 → 从 arXiv API 重取完整摘要，
    仅当新摘要更长时才替换（不会用更短的内容覆盖已有正文）。
  - 所有条目 → 依据标题 + 摘要（+ 正文）重算「- 基准:」行。
  - 不改动 "## 正文" / "## 图片" 等其余段落。

用法:
    python backfill_abstracts.py --out <资料库目录> --dry-run
    python backfill_abstracts.py --out <资料库目录>
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_vln import detect_benchmarks  # noqa: E402  复用同一套 benchmark 规则

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ARXIV_API = "http://export.arxiv.org/api/query?id_list={ids}&max_results=100"
BATCH = 20


def read_field(text: str, label: str) -> str:
    m = re.search(rf"^- {label}: (.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def read_title(text: str) -> str:
    m = re.search(r"^# (.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def get_summary(text: str) -> str:
    m = re.search(r"## 摘要\n\n(.*?)(?=\n\n## |\Z)", text, re.S)
    return m.group(1).strip() if m else ""


def get_body(text: str) -> str:
    """取「## 正文」段（微信条目的实质内容），不含「## 图片」。"""
    m = re.search(r"## 正文\n\n(.*?)(?=\n\n## |\Z)", text, re.S)
    return m.group(1).strip() if m else ""


def set_summary(text: str, new: str) -> str:
    return re.sub(r"(## 摘要\n\n)(.*?)(?=\n\n## |\Z)",
                  lambda m: m.group(1) + new, text, count=1, flags=re.S)


def set_benchmarks(text: str, labels: list[str]) -> str:
    line = f"- 基准: {', '.join(labels)}" if labels else None
    has = re.search(r"^- 基准: .*$", text, re.MULTILINE)
    if has:
        return re.sub(r"^- 基准: .*$", line, text, count=1, flags=re.MULTILINE) \
            if line else re.sub(r"^- 基准: .*\n", "", text, count=1, flags=re.MULTILINE)
    if not line:
        return text
    # 插在最后一个元信息行（- 链接 / - 日期 / - 作者 / - 类型 / - 来源）之后
    meta = list(re.finditer(r"^- (?:来源|类型|日期|作者|链接): .*$", text, re.MULTILINE))
    if not meta:
        return text
    at = meta[-1].end()
    return text[:at] + "\n" + line + text[at:]


def fetch_abstracts(ids: list[str]) -> dict[str, str]:
    """按 arXiv ID 批量取完整摘要，返回 {去版本号ID: abstract}。"""
    out: dict[str, str] = {}
    for i in range(0, len(ids), BATCH):
        batch = ids[i:i + BATCH]
        url = ARXIV_API.format(ids=",".join(batch))
        raw = ""
        for attempt in range(5):
            try:
                raw = urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
                break
            except Exception as e:  # noqa: BLE001
                print(f"    [重试 {attempt + 1}] {type(e).__name__}: {e}", file=sys.stderr)
                time.sleep(8)
        else:
            print(f"    [失败] 跳过一批 {len(batch)} 条", file=sys.stderr)
            continue
        for ent in re.findall(r"<entry>(.*?)</entry>", raw, re.S):
            aid = re.search(r"<id>http://arxiv\.org/abs/([^<]+)</id>", ent)
            sm = re.search(r"<summary>(.*?)</summary>", ent, re.S)
            if aid and sm:
                out[aid.group(1).split("v")[0]] = " ".join(sm.group(1).split())
        print(f"    已取 {len(out)}/{len(ids)}", file=sys.stderr)
        time.sleep(4)   # arXiv 对频繁请求会 429
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="资料库目录（含 items/）")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = ap.parse_args()

    items_dir = Path(args.out) / "items"
    if not items_dir.is_dir():
        sys.exit(f"找不到 {items_dir}")

    files = sorted(items_dir.glob("*.md"))
    print(f"扫描 {len(files)} 条条目…", file=sys.stderr)

    # 1) 收集需要回填摘要的 arXiv 条目
    todo: dict[str, list[Path]] = {}
    for p in files:
        text = p.read_text(encoding="utf-8")
        if read_field(text, "类型") != "arxiv":
            continue
        link = read_field(text, "链接")
        m = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+)", link)
        if m:
            todo.setdefault(m.group(1), []).append(p)

    print(f"arXiv 条目 {sum(len(v) for v in todo.values())} 条，唯一 ID {len(todo)} 个",
          file=sys.stderr)
    abstracts = {} if args.dry_run and not todo else fetch_abstracts(sorted(todo))

    # 2) 逐条写回：更长的摘要才替换；基准字段一律重算
    n_abs = n_bench = 0
    for p in files:
        text = original = p.read_text(encoding="utf-8")
        link = read_field(text, "链接")
        m = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+)", link)
        if m and m.group(1) in abstracts:
            new, old = abstracts[m.group(1)], get_summary(text)
            if len(new) > len(old):
                text = set_summary(text, new)
                n_abs += 1
        text = set_benchmarks(text, detect_benchmarks(
            read_title(text) or p.stem, get_summary(text), get_body(text)))
        if text != original:
            if not text.count("## 摘要"):
                print(f"    [跳过异常] {p.name}", file=sys.stderr)
                continue
            if re.search(r"^- 基准: ", text, re.MULTILINE):
                n_bench += 1
            if not args.dry_run:
                p.write_text(text, encoding="utf-8")

    verb = "将回填" if args.dry_run else "已回填"
    print(f"\n{verb}摘要 {n_abs} 条，带基准标注 {n_bench} 条。", file=sys.stderr)
    if args.dry_run:
        print("（--dry-run，未写入任何文件）", file=sys.stderr)


if __name__ == "__main__":
    main()
