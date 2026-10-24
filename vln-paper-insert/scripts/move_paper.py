#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在主篇 /VLN-Papers/ 与扩展篇 /VLN-Papers-Extended/ 之间调换一篇论文。

主篇上限 60 篇，满员时想加新论文就得先调一篇出去；排行榜调整时也用它批量调篇。
一次搬运要同时处理四处：章节正文、参考资料条目、TAG_MAP 条目，
以及**留在原页排行榜/会议表里的锚点链接**——论文搬走后那些链接必须
改成跨页形式，否则会变成死链。

方向自动判断：给出锚点，脚本查出它当前在哪一篇，搬到另一篇。
插入位置遵循两篇统一的排序约定（按年份升序）。

搬完记得跑 sync_remote.py 更新跨页筛选清单（--sync 可一并执行）。

用法:
    python move_paper.py --anchor navcon [--dry-run] [--sync]
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# skill 经 GitHub 同步到多台电脑，博客仓库位置不同：按顺序取本机存在的那个
# 博客仓库根目录：优先读环境变量 BLOG_ROOT，否则用当前目录
BLOG_ROOT = Path(os.environ.get('BLOG_ROOT') or Path.cwd())
BASE = BLOG_ROOT / "_posts/research"
MAIN = BASE / "2026-01-05-VLN-Papers.md"
SUPP = BASE / "2026-01-06-VLN-Papers-Extended.md"
URL = {MAIN: "/VLN-Papers/", SUPP: "/VLN-Papers-Extended/"}
ORDER_DESC = {MAIN: False, SUPP: False}   # 两篇均按年份升序
MAIN_CAP = 60

SEC_RE = re.compile(r"^## (\d+)\. (.*?) \{#([a-z0-9-]+)\}\s*$")
REF_RE = re.compile(r"^(\d+)\. \*\*(.+?)\*\*(.*)$")
YEAR_RE = re.compile(r"\((\d{4})\)")


def load(path):
    raw = path.read_bytes().decode("utf-8")
    return raw.replace("\r\n", "\n").split("\n"), ("\r\n" if "\r\n" in raw else "\n")


def split_doc(lines):
    """切成 (前言+正文头, 章节列表, 参考资料头, 参考条目, 尾部)"""
    i_refs = next(i for i, l in enumerate(lines) if l.startswith("# 参考资料"))
    i_script = next(i for i, l in enumerate(lines) if l == "<script>")

    head, sections, cur = [], [], None
    for l in lines[:i_refs]:
        m = SEC_RE.match(l)
        if m:
            if cur:
                sections.append(cur)
            cur = {"title": m.group(2), "anchor": m.group(3), "lines": [l]}
        elif cur:
            cur["lines"].append(l)
        else:
            head.append(l)
    if cur:
        sections.append(cur)

    ref_head, refs, ref_tail, seen = [], [], [], False
    for l in lines[i_refs:i_script]:
        if REF_RE.match(l):
            seen = True
            refs.append(l)
        elif seen:
            ref_tail.append(l)
        else:
            ref_head.append(l)

    return head, sections, ref_head, refs, ref_tail, lines[i_script:]


def year_of(title):
    m = YEAR_RE.search(title)
    return int(m.group(1)) if m else 0


def insert_index(sections, year, desc):
    """按年份排序约定求插入位置：同年放在该年份组的末尾"""
    for i, s in enumerate(sections):
        y = year_of(s["title"])
        if (y < year) if desc else (y > year):
            return i
    return len(sections)


def assemble(head, sections, ref_head, refs, ref_tail, tail):
    out = list(head)
    for n, s in enumerate(sections, start=1):
        body = list(s["lines"])
        body[0] = f'## {n}. {s["title"]} {{#{s["anchor"]}}}'
        out += body
    out += ref_head
    for n, l in enumerate(refs, start=1):
        out.append(REF_RE.sub(lambda m: f"{n}. **{m.group(2)}**{m.group(3)}", l))
    return out + ref_tail + tail


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anchor", required=True, help="要搬运的论文锚点，如 navcon")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    ap.add_argument("--sync", action="store_true", help="搬完自动跑 sync_remote.py")
    args = ap.parse_args()

    docs = {p: split_doc(load(p)[0]) for p in (MAIN, SUPP)}
    nl = {p: load(p)[1] for p in (MAIN, SUPP)}

    src = next((p for p in (MAIN, SUPP)
                if any(s["anchor"] == args.anchor for s in docs[p][1])), None)
    if src is None:
        sys.exit(f"错误: 两篇文章里都找不到锚点 #{args.anchor}")
    dst = SUPP if src is MAIN else MAIN

    s_head, s_secs, s_rh, s_refs, s_rt, s_tail = docs[src]
    d_head, d_secs, d_rh, d_refs, d_rt, d_tail = docs[dst]

    idx = next(i for i, s in enumerate(s_secs) if s["anchor"] == args.anchor)
    sec = s_secs[idx]
    name = sec["title"]

    if dst is MAIN and len(d_secs) + 1 > MAIN_CAP:
        sys.exit(f"错误: 主篇已有 {len(d_secs)} 篇，达到上限 {MAIN_CAP}，"
                 "请先调一篇出去")

    # 参考条目与 TAG_MAP 条目按论文名定位
    base = name.split(" (")[0]
    ref_i = next((i for i, l in enumerate(s_refs)
                  if REF_RE.match(l).group(2).strip() == base), None)
    if ref_i is None:
        sys.exit(f"错误: 在 {src.name} 的参考资料里找不到 **{base}**")

    tag_i = next((i for i, l in enumerate(s_tail)
                  if re.match(rf"^\s*\{{ m: '{re.escape(base)}',", l)), None)
    if tag_i is None:
        sys.exit(f"错误: 在 {src.name} 的 TAG_MAP 里找不到 '{base}'")

    print(f"搬运 {base}  {src.name} -> {dst.name}")
    print(f"  章节  第 {idx + 1} 节，{len(sec['lines'])} 行")
    print(f"  参考  {s_refs[ref_i].strip()[:60]}")
    print(f"  标签  {s_tail[tag_i].strip()[:70]}")

    # 从源页取出
    s_secs.pop(idx)
    ref_line = s_refs.pop(ref_i)
    tag_line = s_tail.pop(tag_i)

    # 放进目标页（按年份约定定位）
    pos = insert_index(d_secs, year_of(name), ORDER_DESC[dst])
    d_secs.insert(pos, sec)
    d_refs.insert(pos, ref_line)
    print(f"  插入目标页第 {pos + 1} 节（{'年份降序' if ORDER_DESC[dst] else '年份升序'}）")

    # TAG_MAP 放到目标页列表末尾
    d_close = next(i for i, l in enumerate(d_tail) if l.strip() == "];")
    d_tail.insert(d_close, tag_line)

    # 原页残留的锚点链接（排行榜、会议表）改成跨页形式；目标页反向还原
    src_out = assemble(s_head, s_secs, s_rh, s_refs, s_rt, s_tail)
    dst_out = assemble(d_head, d_secs, d_rh, d_refs, d_rt, d_tail)

    # 源页：论文走了，页内锚点失效，改成指向目标页
    n_cross = sum(l.count(f"](#{args.anchor})") for l in src_out)
    src_out = [l.replace(f"](#{args.anchor})", f"]({URL[dst]}#{args.anchor})") for l in src_out]

    # 目标页：论文来了，原先指向「论文旧位置」的跨页链接还原为页内锚点。
    # 注意要匹配 URL[src]（论文搬走前所在的页），不是 URL[dst]。
    stale = f"]({URL[src]}#{args.anchor})"
    n_back = sum(l.count(stale) for l in dst_out)
    dst_out = [l.replace(stale, f"](#{args.anchor})") for l in dst_out]

    if n_cross:
        print(f"  原页 {n_cross} 处链接改为跨页 -> {URL[dst]}#{args.anchor}")
    if n_back:
        print(f"  目标页 {n_back} 处跨页链接还原为页内锚点")

    print(f"  结果: {src.name} {len(s_secs)} 篇 | {dst.name} {len(d_secs)} 篇")

    if args.dry_run:
        print("\n[dry-run] 未写入任何文件")
        return

    src.write_bytes(nl[src].join(src_out).encode("utf-8"))
    dst.write_bytes(nl[dst].join(dst_out).encode("utf-8"))
    print("已写入")

    if args.sync:
        print()
        subprocess.run([sys.executable, str(Path(__file__).with_name("sync_remote.py"))],
                       check=True)


if __name__ == "__main__":
    main()
