#!/usr/bin/env python3
"""
Insert a paper summary into the VLN Papers blog post.

Usage:
  python insert_paper.py <paper-summary.md> --tags "Agent,高斯表示,零样本" [--blog <path>]
"""

import sys
import re
import argparse
import os
import shutil
import subprocess
from pathlib import Path

# Ensure UTF-8 output so status glyphs (✓) and CJK print on Windows (GBK) consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# skill 经 GitHub 同步到多台电脑，博客仓库位置不同：按顺序取本机存在的那个
# 博客仓库根目录：优先读环境变量 BLOG_ROOT，否则用当前目录
BLOG_ROOT = Path(os.environ.get('BLOG_ROOT') or Path.cwd())
DEFAULT_BLOG_PRIMARY = str(BLOG_ROOT / "_posts/research/2026-01-05-VLN-Papers.md")
DEFAULT_BLOG_SECONDARY = str(BLOG_ROOT / "_posts/2026-01-05-VLN-Papers.md")
DEFAULT_BLOG = DEFAULT_BLOG_PRIMARY if Path(DEFAULT_BLOG_PRIMARY).exists() else DEFAULT_BLOG_SECONDARY

# 论文列表分两篇：主篇 /VLN-Papers/ 与扩展篇 /VLN-Papers-Extended/，两者标题不同。
VLN_SECTION_MARKERS = ["# 具身导航经典论文", "# 具身导航论文扩展", "# 具身导航论文增补"]
RELATED_SECTION_MARKER = "# 参考资料"
# 主篇把 VLN-CE 之后的条目留给基础工作，所以新条目插在它前面；
# 增补篇没有这一条，退回到插在 TAG_MAP 末尾。
TAGMAP_INSERT_BEFORE = "{ m: 'VLN-CE',"
TAGMAP_FALLBACK_BEFORE = "  ];"

# 排行榜子表按圈号定位。①②③（指令跟随）在主篇「# 性能排行榜」下，
# ④–⑧（目标导航）在扩展篇「# 目标导航性能排行榜」下；圈号在两篇间不重复。
CIRCLED = {1: '①', 2: '②', 3: '③', 4: '④', 5: '⑤', 6: '⑥', 7: '⑦', 8: '⑧'}
TABLE_NAMES = {1: 'R2R-CE', 2: 'RxR-CE', 3: 'R2R · REVERIE（离散）', 4: '封闭类别物体目标 · ObjectNav（HM3D · MP3D · Gibson）',
               5: '开放词汇物体目标 · HM3D-OVON', 6: '图像目标 · HM3D-IIN / Image-Goal',
               7: '点目标 · Point-Goal', 8: '多模态目标与自建基准'}
MAIN_POST = "2026-01-05-VLN-Papers.md"
EXT_POST = "2026-01-06-VLN-Papers-Extended.md"
POST_URL = {MAIN_POST: "/VLN-Papers/", EXT_POST: "/VLN-Papers-Extended/"}
TABLE_POST = {1: MAIN_POST, 2: MAIN_POST, 3: MAIN_POST,
              4: EXT_POST, 5: EXT_POST, 6: EXT_POST, 7: EXT_POST, 8: EXT_POST}
PARADIGMS = ('训练', '免训练')
LOWER_BETTER = {'NE'}
METRIC_COLS = ('SR', 'SPL', 'NE', 'OSR')
MISSING = '–'  # en-dash used in the blog for missing metrics

# "已发表论文（会议 / 期刊）" venue table — a published paper also gets a deep-link row there.
VENUE_TABLE_HEADING = "## 已发表论文（会议 / 期刊）"
JOURNAL_ROW = "期刊"  # catch-all row for journal venues (kept last in the table)
# Venues whose head token matches one of these get their own conference row; everything
# else (IEEE …, Sensors, Springer journals, …) falls into the 期刊 row.
KNOWN_CONFERENCES = ['CVPR', 'ICCV', 'ECCV', 'WACV', 'NeurIPS', 'ICLR', 'ICML',
                     'AAAI', 'IJCAI', 'ACL', 'EMNLP', 'NAACL', 'ICRA', 'IROS',
                     'CoRL', 'RSS', 'SIGGRAPH', '3DV']


def extract_summary_info(content: str) -> dict:
    title_match = re.search(r'^## (.+)$', content, re.MULTILINE)
    if not title_match:
        raise ValueError("No ## title found in summary file")
    title_line = title_match.group(1).strip()

    # Strip optional surrounding brackets e.g. [ReflectVLN (2026)] -> ReflectVLN (2026)
    clean_title = re.sub(r'[\[\]]', '', title_line)
    name_year = re.match(r'^(.+?)\s*\((\d{4})\)\s*$', clean_title)
    if not name_year:
        raise ValueError(f"Cannot parse 'PaperName (year)' from: {title_line}")

    subtitle_match = re.search(r'^———(.+)$', content, re.MULTILINE)
    arxiv_match = re.search(r'arxiv\.org/abs/([\d.]+)', content, re.IGNORECASE)
    # Venue from the 📄 **Paper** line: `· 🏛️ **VENUE YEAR**` (absent for preprints).
    venue_match = re.search(r'🏛️\s*\*\*(.+?)\*\*', content)
    # Extract code repository link if available e.g. `· [Code](url)`
    code_match = re.search(r'\[(?:Code|GitHub)\]\((https?://\S+)\)', content, re.IGNORECASE)

    return {
        'title_line': clean_title,
        'paper_name': name_year.group(1).strip(),
        'year': name_year.group(2),
        'subtitle': subtitle_match.group(1).strip() if subtitle_match else '',
        'arxiv_id': arxiv_match.group(1) if arxiv_match else None,
        'venue': venue_match.group(1).strip() if venue_match else None,
        'code_url': code_match.group(1) if code_match else None,
    }


def get_next_section_number(blog_content: str) -> int:
    vln_start = -1
    for marker in VLN_SECTION_MARKERS:
        vln_start = blog_content.find(marker)
        if vln_start != -1:
            break
    related_start = blog_content.find(RELATED_SECTION_MARKER)
    if vln_start == -1 or related_start == -1:
        raise ValueError(
            "Cannot find section markers in blog post "
            f"(looked for {VLN_SECTION_MARKERS} and {RELATED_SECTION_MARKER!r})"
        )
    vln_portion = blog_content[vln_start:related_start]
    numbers = re.findall(r'^## (\d+)\.', vln_portion, re.MULTILINE)
    return max(int(n) for n in numbers) + 1 if numbers else 1


def get_last_ref_number(blog_content: str) -> int:
    ref_start = blog_content.find('# 参考资料')
    script_start = blog_content.find('<script>', ref_start if ref_start != -1 else 0)
    if ref_start == -1:
        raise ValueError("Cannot find 参考资料 section")
    ref_portion = blog_content[ref_start:script_start if script_start != -1 else None]
    numbers = re.findall(r'^(\d+)\. \*\*', ref_portion, re.MULTILINE)
    return max(int(n) for n in numbers) if numbers else 0


def slugify(name: str) -> str:
    """Kramdown anchor slug from a paper name: 'WAM-Nav' -> 'wam-nav'."""
    s = re.sub(r'\([^)]*\)', '', name).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s


IMG_TAG_RE = re.compile(r'<img src="(/images/[^"]+)" width="(\d+%)" />')


def _image_size(web_path: str):
    """量出图片像素尺寸，用于 aspect-ratio 占位；取不到就返回 None"""
    f = BLOG_ROOT / web_path.lstrip("/")
    if not f.exists() or not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-hide_banner", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(f)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
        ).stdout.strip()
        w, h = out.split("x")
        return int(w), int(h)
    except Exception:
        return None


def stamp_images(content: str) -> tuple:
    """
    给正文里的 <img> 补上 loading="lazy" decoding="async" 和 aspect-ratio 占位。

    博客的图片一律延迟加载，另有脚本在页面 load 后台预取，所以打开页面时不拉图；
    aspect-ratio 用来给未加载的图预留高度，否则滚动时图片弹出会把正文推来推去。
    总结文件里是朴素的 <img>，插入时必须补齐，否则新论文会破坏这套机制。
    """
    stamped = missing_size = 0

    def repl(m):
        nonlocal stamped, missing_size
        src, width = m.group(1), m.group(2)
        extra = ' loading="lazy" decoding="async"'
        size = _image_size(src)
        if size:
            extra += f' style="aspect-ratio:{size[0]}/{size[1]}"'
        else:
            missing_size += 1
        stamped += 1
        return f'<img src="{src}" width="{width}"{extra} />'

    return IMG_TAG_RE.sub(repl, content), stamped, missing_size


def build_section_content(summary_content: str, entry_num: int, title_line: str, anchor: str) -> str:
    # Append a kramdown {#anchor} so leaderboard rows can deep-link to this section.
    heading = f'## {entry_num}. {title_line} {{#{anchor}}}'
    content = summary_content.replace(f'## {title_line}', heading, 1)
    content = content.rstrip('\n')
    if not content.endswith('---'):
        content += '\n\n---'
    return content + '\n\n'


def build_tag_entry(paper_name: str, tags: list) -> str:
    tags_js = ', '.join(f"'{t}'" for t in tags)
    padding = max(1, 22 - len(paper_name))
    return f"    {{ m: '{paper_name}',{' ' * padding}t: [{tags_js}] }},"


def build_ref_entry(ref_num: int, paper_name: str, year: str, subtitle: str, arxiv_id: str) -> str:
    line = f'{ref_num}. **{paper_name}** ({year}).'
    if subtitle:
        line += f' {subtitle}.'
    if arxiv_id:
        line += f' arXiv: [{arxiv_id}](https://arxiv.org/abs/{arxiv_id})'
    return line


def classify_venue(venue: str) -> tuple:
    """Map a venue string to (row_key, entry_suffix) for the 已发表论文 table.

    Conference (head token in KNOWN_CONFERENCES) -> (ACRONYM, '(year[, extra])'),
    matching rows like `| **ICRA** | [NoMaD](#nomad) (2024) |`.
    Anything else is treated as a journal -> ('期刊', '(full venue string)'),
    matching `| **期刊** | [GaussNav](#gaussnav) (IEEE TPAMI 2025) |`."""
    ym = re.search(r'((?:19|20|21)\d{2})', venue)
    year = ym.group(1) if ym else ''
    head = (venue[:ym.start()] if ym else venue).strip()
    tail = (venue[ym.end():] if ym else '').strip()

    for conf in KNOWN_CONFERENCES:
        if head.upper() == conf.upper():
            extra = tail.strip('() ').strip()
            suffix = f"({year}, {extra})" if extra else f"({year})"
            return conf, suffix
    # Journal / workshop / other: keep the full venue text verbatim.
    return JOURNAL_ROW, f"({venue})"


def insert_venue_entry(blog_content: str, row_key: str, label: str) -> tuple:
    """Append a deep-link entry to the 已发表论文（会议 / 期刊）table.

    Appends to row `row_key` if it exists, else inserts a new conference row just
    above the 期刊 row (so 期刊 stays last). Returns (new_content, row_text, note)."""
    lines = blog_content.split('\n')
    head_idx = next((i for i, ln in enumerate(lines)
                     if ln.strip() == VENUE_TABLE_HEADING), None)
    if head_idx is None:
        return blog_content, None, 'venue table heading not found — skipped'

    # Locate the table body: header `| 会议 / 期刊 | 论文 |`, separator, then data rows.
    hdr_idx = next((i for i in range(head_idx + 1, len(lines))
                    if lines[i].strip().startswith('|')), None)
    if hdr_idx is None:
        return blog_content, None, 'venue table body not found — skipped'
    data_start = hdr_idx + 2  # skip header + |---| separator
    data_end = data_start
    while data_end < len(lines) and lines[data_end].strip().startswith('|'):
        data_end += 1

    def first_cell(line):
        parts = [p.strip() for p in line.split('|')]
        return parts[1] if len(parts) > 1 else ''

    target = f'**{row_key}**'
    for i in range(data_start, data_end):
        if first_cell(lines[i]) == target:
            # Append `、{label}` before the row's trailing pipe.
            stripped = lines[i].rstrip()
            stripped = stripped[:-1].rstrip() if stripped.endswith('|') else stripped
            lines[i] = f"{stripped}、{label} |"
            return '\n'.join(lines), lines[i], ''

    # No existing row for this conference — insert a new one before the 期刊 row.
    new_row = f"| **{row_key}** | {label} |"
    journal_idx = next((i for i in range(data_start, data_end)
                        if first_cell(lines[i]) == f'**{JOURNAL_ROW}**'), data_end)
    lines.insert(journal_idx, new_row)
    return '\n'.join(lines), new_row, f'new venue row「{row_key}」created'


def parse_rank_spec(spec: str, default_model: str, default_year: str, default_code: str = '否') -> dict:
    """Parse a --rank spec: 'table=4;paradigm=训练;benchmark=...;SR=80.4;SPL=78.0[;NE=..;OSR=..;model=..;year=..;base=..;flag=..]'."""
    fields = {}
    for part in spec.split(';'):
        part = part.strip()
        if not part:
            continue
        if '=' not in part:
            raise ValueError(f"Bad --rank field (expected key=value): {part!r}")
        key, val = part.split('=', 1)
        fields[key.strip().lower()] = val.strip()

    if 'table' not in fields:
        raise ValueError(f"--rank missing required 'table' (1-8): {spec!r}")
    try:
        table = int(fields['table'])
    except ValueError:
        raise ValueError(f"--rank 'table' must be an integer 1-8: {fields['table']!r}")
    if table not in CIRCLED:
        raise ValueError(f"--rank 'table' must be 1-8, got {table}")
    paradigm = fields.get('paradigm', '')
    if paradigm not in PARADIGMS:
        raise ValueError(f"--rank needs 'paradigm=训练' or 'paradigm=免训练' (see SKILL.md 判定口径): {spec!r}")

    # Clean benchmark name (e.g. "R2R-CE (Val-Unseen)" -> "R2R-CE")
    bench = fields.get('benchmark', '')
    bench_clean = re.sub(r'\s*\([Vv]al-[Uu]nseen\)', '', bench).strip()

    return {
        'table': table,
        'model': fields.get('model', default_model),
        'year': fields.get('year', default_year),
        'benchmark': bench_clean,
        'paradigm': paradigm,
        'base': fields.get('base', MISSING),
        'SR': fields.get('sr', MISSING),
        'SPL': fields.get('spl', MISSING),
        'NE': fields.get('ne', MISSING),
        'OSR': fields.get('osr', MISSING),
        'code': fields.get('code', default_code),
        'flag': fields.get('flag', ''),
    }


def _cells(line: str) -> list:
    return [c.strip() for c in line.strip().strip('|').split('|')]


def _col_key(header_cell: str) -> str:
    """'SR ↑' -> 'SR'，'模型' -> '模型'"""
    return header_cell.split(' ')[0]


def build_rank_row(rank: dict, link: str, header: list) -> str:
    """按目标表的表头拼一行。灰显标记（非标准口径，如「100 条子集」）挂在模型格里。"""
    model = f"[{rank['model']}]({link})" if link else rank['model']
    if rank['flag']:
        model += f' <span class="lb-flag">{rank["flag"]}</span>'
    values = {'模型': model, '年份': rank['year'], '基准': rank['benchmark'], '范式': rank['paradigm'],
              '基模': rank['base'], 'SR': rank['SR'], 'SPL': rank['SPL'], 'NE': rank['NE'],
              'OSR': rank['OSR'], '开源': rank.get('code', '否')}
    cols = []
    for h in header:
        k = _col_key(h)
        if k not in values:
            raise ValueError(f"排行榜表头里有脚本不认识的列「{h}」，请同步更新 build_rank_row")
        cols.append(str(values[k] or MISSING))
    return '| ' + ' | '.join(cols) + ' |'


def parse_sr(cell: str):
    """Numeric value from a table cell, ignoring **bold**, ≈/~/≥ markers; None if not numeric."""
    c = cell.strip()
    for ch in ('*', '≈', '~', '≥', '≤'):
        c = c.replace(ch, '')
    c = c.strip()
    try:
        return float(c)
    except ValueError:
        return None


def rebold_table(lines: list, hdr_idx: int, data_start: int, data_end: int) -> None:
    """按页面「读表」里写明的规则重算加粗（与 js/leaderboard.js 一致）：
    同一基准（有「基准」列时按它分组）内、不带 lb-flag 的行、至少两个数值时取最优，并列都加粗。"""
    header = [_col_key(h) for h in _cells(lines[hdr_idx])]
    rows = [_cells(lines[i]) for i in range(data_start, data_end)]
    for r in rows:
        for m in METRIC_COLS:
            if m in header:
                j = header.index(m)
                r[j] = r[j].replace('**', '').strip()
    g = header.index('基准') if '基准' in header else None
    groups = {}
    for r in rows:
        if 'lb-flag' in r[0]:
            continue
        groups.setdefault(r[g] if g is not None else '', []).append(r)
    for grp in groups.values():
        for m in METRIC_COLS:
            if m not in header:
                continue
            j = header.index(m)
            vals = [parse_sr(r[j]) for r in grp]
            nums = [v for v in vals if v is not None]
            if len(nums) < 2:
                continue
            best = min(nums) if m in LOWER_BETTER else max(nums)
            for r, v in zip(grp, vals):
                if v == best:
                    r[j] = f'**{r[j]}**'
    for i, r in zip(range(data_start, data_end), rows):
        lines[i] = '| ' + ' | '.join(r) + ' |'


def insert_rank_row(blog_content: str, rank: dict, link: str) -> tuple:
    """Insert a leaderboard row into sub-table `rank['table']` and re-apply the bold rule.

    有「基准」列的表（③④⑥⑦⑧）按基准分组：插到同一基准组内按 SR 降序的位置，新基准放在表尾；
    没有「基准」列的表（①②⑤）整表按 SR 降序。Returns (new_content, row, note)."""
    lines = blog_content.split('\n')
    marker = CIRCLED[rank['table']]

    head_idx = next((i for i, ln in enumerate(lines)
                     if ln.startswith(f'## {marker} ')), None)
    if head_idx is None:
        raise ValueError(f"Cannot find leaderboard sub-table heading '## {marker} …'")

    hdr_idx = None
    for i in range(head_idx + 1, len(lines)):
        s = lines[i].strip()
        if s.startswith('|') and _cells(s)[0] == '模型':
            hdr_idx = i
            break
        if lines[i].startswith('#'):
            break
    if hdr_idx is None:
        raise ValueError(f"Cannot find table header under sub-table {rank['table']}")

    header = _cells(lines[hdr_idx])
    keys = [_col_key(h) for h in header]
    data_start = hdr_idx + 2  # skip header + |:---| separator
    data_end = data_start
    while data_end < len(lines) and lines[data_end].strip().startswith('|'):
        data_end += 1

    sr_j = keys.index('SR')
    bench_j = keys.index('基准') if '基准' in keys else None
    note = ''
    if bench_j is not None and not rank['benchmark']:
        raise ValueError(f"表{marker} 有「基准」列，--rank 必须给 benchmark=")
    if bench_j is None and rank['benchmark']:
        note = f"  （表{marker} 没有「基准」列，benchmark={rank['benchmark']} 未写入；标题已限定基准）"

    def row_sr(i):
        c = _cells(lines[i])
        return parse_sr(c[sr_j]) if len(c) > sr_j else None

    candidates = list(range(data_start, data_end))
    if bench_j is not None:
        same = [i for i in candidates if _cells(lines[i])[bench_j] == rank['benchmark']]
        if not same:
            note += (f"  ⚠ 表{marker} 新增基准组「{rank['benchmark']}」，放在表尾；"
                     f"确认它确实不是已有基准的另一种写法")
        candidates = same
    new_sr = parse_sr(rank['SR'])
    insert_at = (candidates[-1] + 1) if candidates else data_end
    if new_sr is not None:
        for i in candidates:
            esr = row_sr(i)
            if esr is None or esr < new_sr:
                insert_at = i
                break

    row = build_rank_row(rank, link, header)
    lines.insert(insert_at, row)
    rebold_table(lines, hdr_idx, data_start, data_end + 1)
    row = lines[insert_at]
    return '\n'.join(lines), row, note


def main():
    parser = argparse.ArgumentParser(description='Insert paper summary into VLN blog post')
    parser.add_argument('summary_file', help='Path to paper-summary-XXX.md')
    parser.add_argument('--tags', required=True,
                        help="Comma-separated tags, e.g. 'Agent,高斯表示,零样本'")
    parser.add_argument('--blog', default=DEFAULT_BLOG, help='Path to VLN-Papers.md blog post')
    parser.add_argument('--rank', action='append', default=[], metavar='SPEC',
                        help="Leaderboard row, repeatable. Semicolon-separated key=value: "
                             "'table=4;paradigm=训练;benchmark=HM3D-v2;SR=80.4;SPL=78.0' "
                             "(tables 1-3 also take NE/OSR; tables 3/4/6/7/8 need benchmark=; "
                             "flag= greys the row as non-standard, e.g. flag=100 条子集; "
                             "model/year default to the paper).")
    parser.add_argument('--anchor', default=None,
                        help="Section anchor slug for the {#id} heading and leaderboard links "
                             "(default: slugified paper name, e.g. WAM-Nav -> wam-nav).")
    parser.add_argument('--venue', default=None,
                        help="Publication venue, e.g. 'ICRA 2024' or 'IEEE TPAMI 2025'. "
                             "Adds a deep-link to the 已发表论文（会议 / 期刊）table. "
                             "Defaults to the 🏛️ venue parsed from the summary's Paper line; "
                             "omit for preprints (no table entry).")
    args = parser.parse_args()

    summary_path = Path(args.summary_file)
    if not summary_path.exists():
        print(f"ERROR: Summary file not found: {summary_path}")
        sys.exit(1)

    summary_content = summary_path.read_text(encoding='utf-8')
    info = extract_summary_info(summary_content)
    tags = [t.strip() for t in args.tags.split(',') if t.strip()]
    anchor = args.anchor or slugify(info['paper_name'])

    blog_path = Path(args.blog)
    if not blog_path.exists():
        print(f"ERROR: Blog post not found: {blog_path}")
        sys.exit(1)
    blog_content = blog_path.read_text(encoding='utf-8')

    entry_num = get_next_section_number(blog_content)
    last_ref = get_last_ref_number(blog_content)
    ref_num = last_ref + 1

    # 1. Insert main section content before # 相关基础工作
    section_content = build_section_content(summary_content, entry_num, info['title_line'], anchor)
    # 总结里的 <img> 是朴素写法，补上延迟加载与尺寸占位，与全站保持一致
    section_content, n_img, n_nosize = stamp_images(section_content)
    insert_marker = f'\n{RELATED_SECTION_MARKER}'
    if insert_marker not in blog_content:
        print(f"ERROR: Cannot find '{RELATED_SECTION_MARKER}' in blog post")
        sys.exit(1)
    blog_content = blog_content.replace(insert_marker, f'\n{section_content}{RELATED_SECTION_MARKER}', 1)

    # 2. Insert TAG_MAP entry before Diffusion Policy (first 基础工作 entry)。
    #    增补篇没有 VLN-CE 那条，退回到插在 TAG_MAP 列表末尾。
    tag_entry = build_tag_entry(info['paper_name'], tags)
    if TAGMAP_INSERT_BEFORE in blog_content:
        blog_content = blog_content.replace(
            TAGMAP_INSERT_BEFORE,
            f'{tag_entry}\n    {TAGMAP_INSERT_BEFORE}',
            1
        )
    elif TAGMAP_FALLBACK_BEFORE in blog_content:
        blog_content = blog_content.replace(
            TAGMAP_FALLBACK_BEFORE,
            f'{tag_entry}\n{TAGMAP_FALLBACK_BEFORE}',
            1
        )
    else:
        print("ERROR: Cannot find TAG_MAP insertion point")
        sys.exit(1)

    # 3. Insert reference entry after the last numbered reference
    ref_entry = build_ref_entry(ref_num, info['paper_name'], info['year'], info['subtitle'], info['arxiv_id'])
    ref_section_start = blog_content.find('# 参考资料')
    script_start = blog_content.find('<script>', ref_section_start)
    ref_portion = blog_content[ref_section_start:script_start]
    last_ref_match = re.search(r'^' + str(last_ref) + r'\. \*\*[^\n]+', ref_portion, re.MULTILINE)
    if last_ref_match:
        abs_pos = ref_section_start + last_ref_match.end()
        blog_content = blog_content[:abs_pos] + f'\n{ref_entry}' + blog_content[abs_pos:]
    else:
        print(f"WARNING: Reference #{last_ref} not found; appending before <script>")
        blog_content = blog_content[:script_start] + f'{ref_entry}\n\n' + blog_content[script_start:]

    # 3b. Insert venue-table entry (published papers only; --venue overrides parsed 🏛️)
    venue = args.venue or info['venue']
    venue_row = venue_note = None
    if venue:
        row_key, suffix = classify_venue(venue)
        label = f'[{info["paper_name"]}](#{anchor}) {suffix}'
        blog_content, venue_row, venue_note = insert_venue_entry(blog_content, row_key, label)

    # 4. Insert leaderboard rows (optional, repeatable)。
    #    ①②③ 在主篇、④–⑧ 在扩展篇；表所在页不是论文所在页时，模型链接写成跨页形式。
    default_code = f"[是]({info['code_url']})" if info.get('code_url') else '否'
    other_path = None
    other_content = None
    rank_notes = []
    for spec in args.rank:
        rank = parse_rank_spec(spec, default_model=info['paper_name'], default_year=info['year'], default_code=default_code)
        table_post = TABLE_POST[rank['table']]
        if table_post == blog_path.name:
            blog_content, row, note = insert_rank_row(blog_content, rank, f'#{anchor}')
        else:
            if other_path is None:
                other_path = blog_path.with_name(table_post)
                other_content = other_path.read_text(encoding='utf-8')
            link = f'{POST_URL.get(blog_path.name, "/VLN-Papers/")}#{anchor}'
            other_content, row, note = insert_rank_row(other_content, rank, link)
            note += f"  （写入{other_path.name}）"
        rank_notes.append((row, rank, note))

    blog_path.write_text(blog_content, encoding='utf-8')
    if other_path is not None:
        other_path.write_text(other_content, encoding='utf-8')

    print(f"✓ Inserted   ## {entry_num}. {info['title_line']} {{#{anchor}}}")
    if n_img:
        note = f"（{n_nosize} 张未测到尺寸，无 aspect-ratio 占位）" if n_nosize else ""
        print(f"✓ 图片标记   {n_img} 张加上 lazy + 尺寸占位{note}")
    print(f"✓ TAG_MAP    {tag_entry.strip()}")
    print(f"✓ Reference  {ref_entry}")
    if venue_row:
        suffix_note = f"  ⚠ {venue_note}" if venue_note else ''
        print(f"✓ 已发表表   {venue_row.strip()}{suffix_note}")
    elif venue:
        print(f"⚠ 已发表表   venue '{venue}' given but {venue_note}")
    for row, rank, note in rank_notes:
        print(f"✓ 排行榜 表{CIRCLED[rank['table']]}  {row}{note}")
    if rank_notes:
        print("  （所在表的加粗已按「同基准、非灰色行取最优」规则重算）")
    # 表① SR ≥ 60 的行同时是「前列模型要素打勾矩阵」的收录范围，插入后矩阵就过期了
    matrix_rows = [row for row, rank, _ in rank_notes
                   if rank['table'] == 1 and (parse_sr(rank['SR']) or 0) >= 60]
    if matrix_rows:
        print(f"⚠ 前列矩阵   表① 新增 {len(matrix_rows)} 行 SR ≥ 60，"
              f"按 SKILL.md Step 5c 用 refresh_matrix.py 补打勾并重算统计")


if __name__ == '__main__':
    main()
