#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步两篇 VLN 论文文章里的 REMOTE_PAPERS 清单。

两篇文章的筛选器会合并展示彼此的命中项：另一篇的论文以跨页链接出现在结果面板里。
实现方式是每页内嵌一份对方的论文清单，而这份清单是静态的——任一篇增删论文后
都必须重跑本脚本，否则跨页筛选会漏掉新论文、总数也会对不上。

标签的算法必须与页面内的 getTagsForTitle 完全一致（按 TAG_MAP 顺序取首个子串命中），
否则结果面板列出的论文会和实际章节的标签对不上。

用法:
    python sync_remote.py [--check]

    --check  只报告是否需要同步，不写文件（退出码 1 表示不同步）
"""
import argparse
import os
import json
import re
import sys
from pathlib import Path

# skill 经 GitHub 同步到多台电脑，博客仓库位置不同：按顺序取本机存在的那个
# 博客仓库根目录：优先读环境变量 BLOG_ROOT，否则用当前目录
BLOG_ROOT = Path(os.environ.get('BLOG_ROOT') or Path.cwd())
BASE = BLOG_ROOT / "_posts/research"

# (文件, 对方的 URL, 结果面板上显示的角标)
PAGES = [
    (BASE / "2026-01-05-VLN-Papers.md", "/VLN-Papers-Extended/", "扩展篇"),
    (BASE / "2026-01-06-VLN-Papers-Extended.md", "/VLN-Papers/", "主篇"),
]

SEC_RE = re.compile(r"^## (\d+)\. (.*?) \{#([a-z0-9-]+)\}\s*$")
TAG_RE = re.compile(r"^\s*\{ m: '([^']+)',\s*t: (\[.*\]) \},?\s*$")
BLOCK_RE = re.compile(
    r"\n  // 另一篇文章的论文清单。.*?\n  var REMOTE_PAPERS = \[\n.*?\n  \];\n",
    re.DOTALL,
)


def read(path):
    raw = path.read_bytes().decode("utf-8")
    return raw, ("\r\n" if "\r\n" in raw else "\n")


def parse_papers(text):
    """解析出 [(编号, 标题, 锚点, 标签)]，标签算法与 getTagsForTitle 一致"""
    lines = text.replace("\r\n", "\n").split("\n")

    tag_map, in_map = [], False
    for l in lines:
        if "var TAG_MAP = [" in l:
            in_map = True
            continue
        if in_map and l.strip() == "];":
            break
        m = TAG_RE.match(l)
        if in_map and m:
            tag_map.append((m.group(1), json.loads(m.group(2).replace("'", '"'))))

    papers = []
    for l in lines:
        m = SEC_RE.match(l)
        if not m:
            continue
        num, title, anchor = int(m.group(1)), m.group(2), m.group(3)
        heading = f"{num}. {title}"
        tags = next((t for name, t in tag_map if name in heading), None)
        papers.append((num, title, anchor, tags))
    return papers


def build_block(papers, url, label):
    rows = []
    for num, title, anchor, tags in papers:
        if not tags:
            print(f"  ⚠ 跳过（TAG_MAP 无匹配，不会出现在跨页筛选中）: {num}. {title}")
            continue
        t = "[" + ", ".join(f"'{x}'" for x in tags) + "]"
        n = f"{num}. {title}".replace("\\", "\\\\").replace("'", "\\'")
        rows.append(f"    {{ n: '{n}', a: '{anchor}', t: {t} }},")
    return (
        "\n"
        "  // 另一篇文章的论文清单。两篇的 .paper-section 各自只在本页存在，\n"
        "  // 所以这些条目不参与显示/隐藏，只在结果面板里作为跨页链接列出。\n"
        "  // 由 vln-paper-insert/scripts/sync_remote.py 生成，勿手工编辑。\n"
        f"  var REMOTE_PAGE = {{ url: '{url}', label: '{label}' }};\n"
        "  var REMOTE_PAPERS = [\n" + "\n".join(rows) + "\n"
        "  ];\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="只检查，不写入")
    args = ap.parse_args()

    for path, _, _ in PAGES:
        if not path.exists():
            sys.exit(f"错误: 找不到 {path}")

    texts = {path: read(path) for path, _, _ in PAGES}
    papers = {path: parse_papers(texts[path][0]) for path, _, _ in PAGES}

    total = sum(len(v) for v in papers.values())
    for path, _, _ in PAGES:
        print(f"{path.name}: {len(papers[path])} 篇")
    print(f"合计 {total} 篇\n")

    stale = False
    for i, (path, url, label) in enumerate(PAGES):
        other = PAGES[1 - i][0]
        raw, nl = texts[path]
        block = build_block(papers[other], url, label)

        body = raw.replace("\r\n", "\n")
        if not BLOCK_RE.search(body):
            sys.exit(f"错误: {path.name} 中找不到 REMOTE_PAPERS 区块，"
                     "可能被手工改过或尚未初始化")

        new_body = BLOCK_RE.sub(lambda _: block, body, count=1)
        if new_body == body:
            print(f"{path.name}: 已是最新（{len(papers[other])} 条）")
            continue

        stale = True
        if args.check:
            print(f"{path.name}: 需要同步 -> {len(papers[other])} 条")
        else:
            path.write_bytes(new_body.replace("\n", nl).encode("utf-8"))
            print(f"{path.name}: 已更新为 {len(papers[other])} 条（指向 {url}）")

    if args.check and stale:
        sys.exit(1)


if __name__ == "__main__":
    main()
