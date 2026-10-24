#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper Insert Tool
自动化将论文总结插入到对应的综述文章中。
支持 VLA、VLM、World Models、Spatial Intelligence 主题。
"""

import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime

# 设置标准输出为 UTF-8 编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 博客仓库根目录：优先读环境变量 BLOG_ROOT，否则用当前目录
BLOG_ROOT = Path(os.environ.get('BLOG_ROOT') or Path.cwd())
POSTS = BLOG_ROOT / '_posts' / 'research'

MAP = {
    'vla': {
        'file': str(POSTS / '2026-01-24-VLA-Survey.md'),
        'heading': '# 5. 经典论文深度解析',
        'prefix': '5'
    },
    'vlm': {
        'file': str(POSTS / '2026-03-05-VLM-Survey.md'),
        'heading': '# 8. 经典方法与代表性工作',
        'prefix': '8'
    },
    'wm': {
        'file': str(POSTS / '2026-04-16-World-Models-Survey.md'),
        'heading': '# 5. 经典代表性工作',
        'prefix': '5'
    },
    'world-models': {
        'file': str(POSTS / '2026-04-16-World-Models-Survey.md'),
        'heading': '# 5. 经典代表性工作',
        'prefix': '5'
    },
    'si': {
        'file': str(POSTS / '2026-04-29-Spatial-Intelligence-Survey.md'),
        'heading': '# 6. 经典论文深度解析',
        'prefix': '6'
    },
    'spatial-intelligence': {
        'file': str(POSTS / '2026-04-29-Spatial-Intelligence-Survey.md'),
        'heading': '# 6. 经典论文深度解析',
        'prefix': '6'
    }
}


def parse_summary(summary_path):
    """解析总结 MD 文件，提取标题、副标题、Paper链接和五段式内容"""
    if not os.path.exists(summary_path):
        print(f"Error: 总结文件不存在: {summary_path}")
        sys.exit(1)

    with open(summary_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 提取标题
    title_match = re.search(r"^## (.*)$", content, re.MULTILINE)
    if not title_match:
        print("Error: 未找到标题 (以 ## 开头的行)")
        sys.exit(1)
    full_title = re.sub(r"[\[\]]", "", title_match.group(1).strip())

    # 从标题中提取 Paper 名字和年份
    year_match = re.search(r"\((\d{4})\)$", full_title)
    year = year_match.group(1) if year_match else datetime.now().strftime("%Y")
    
    # 移除年份
    title_no_year = re.sub(r"\(\d{4}\)$", "", full_title).strip()
    # 提取冒号前的短名字
    if ":" in title_no_year:
        paper_name = title_no_year.split(":")[0].strip()
    elif "——" in title_no_year:
        paper_name = title_no_year.split("——")[0].strip()
    else:
        paper_name = title_no_year

    # 2. 提取副标题
    sub_match = re.search(r"^[—–]{2,3}(.*)$", content, re.MULTILINE)
    subtitle = sub_match.group(1).strip() if sub_match else ""

    # 3. 提取 Paper 链接行
    paper_link_match = re.search(r"^📄 \*\*Paper\*\*: (.*)$", content, re.MULTILINE)
    paper_link = paper_link_match.group(1).strip() if paper_link_match else ""
    # 如果链接是 markdown 格式 [arXiv:2607.04988](url)，则提取 url 变成纯 url
    url_match = re.search(r"\((https?://\S+)\)", paper_link)
    if url_match:
        paper_url = url_match.group(1)
    else:
        paper_url = paper_link

    # 4. 提取主体内容（保留从第一个 "### 精华" 到末尾的所有内容）
    body_start_match = re.search(r"### 精华", content)
    if not body_start_match:
        print("Error: 未找到 '### 精华' 部分")
        sys.exit(1)
    
    body = content[body_start_match.start():]
    
    return {
        'paper_name': paper_name,
        'year': year,
        'subtitle': subtitle,
        'paper_url': paper_url,
        'body': body.strip()
    }


def insert_into_post(topic, parsed_data, after_paper=None):
    """将解析的论文数据插入到对应的 Survey 博客中"""
    config = MAP.get(topic.lower())
    if not config:
        print(f"Error: 不支持的主题: {topic}。可用主题: {list(MAP.keys())}")
        sys.exit(1)

    post_path = config['file']
    target_heading = config['heading']
    prefix = config['prefix']

    if not os.path.exists(post_path):
        print(f"Error: Survey 文件不存在: {post_path}")
        sys.exit(1)

    print(f"打开 Survey 文件: {post_path}")
    with open(post_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 1. 更新 front matter 中的 date 字段
    date_pattern = re.compile(r"^date:\s+\d{4}-\d{2}-\d{2}")
    date_updated = False
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    for idx, line in enumerate(lines[:15]):
        if date_pattern.match(line):
            lines[idx] = f"date:  {current_date_str}\n"
            print(f"✓ 已将博客更新日期设为 {current_date_str} (第 {idx+1} 行)")
            date_updated = True
            break
    if not date_updated:
        print("⚠ 警告: 未能在 Front Matter 中找到 date 字段")

    # 2. 定位大章节的起始和结束范围
    section_start_idx = -1
    section_end_idx = -1
    for idx, line in enumerate(lines):
        if line.strip() == target_heading:
            section_start_idx = idx
            break

    if section_start_idx == -1:
        print(f"Error: 未能在 Survey 中找到目标标题 '{target_heading}'")
        sys.exit(1)

    # 寻找大章节的结束（下一个一级标题 #，且不在代码块中）
    in_code_block = False
    for idx in range(section_start_idx + 1, len(lines)):
        if lines[idx].strip().startswith('```'):
            in_code_block = not in_code_block
        if not in_code_block and lines[idx].startswith('# '):
            section_end_idx = idx
            break
    if section_end_idx == -1:
        section_end_idx = len(lines)

    print(f"目标大章节范围: 第 {section_start_idx+1} 行 到第 {section_end_idx+1} 行")

    # 3. 收集这一大章节里所有现有的二级标题 ## X.Y
    heading_regex = re.compile(r"^## " + prefix + r"\.(\d+)\s+(.*?)(?:\s+\{#(.*?)\})?$")
    existing_headings = []  # tuple of (index, number, paper_name, anchor)
    for idx in range(section_start_idx + 1, section_end_idx):
        match = heading_regex.match(lines[idx])
        if match:
            num = int(match.group(1))
            full_title = match.group(2).strip()
            # 从 title 中清理掉年份
            paper_name = re.sub(r"\(\d{4}\)$", "", full_title).strip()
            anchor = match.group(3) if match.group(3) else ""
            existing_headings.append({
                'index': idx,
                'number': num,
                'paper_name': paper_name,
                'anchor': anchor,
                'line': lines[idx]
            })

    print(f"已发现大章节内有 {len(existing_headings)} 篇现有论文")

    # 4. 确定插入点
    insert_at_idx = -1
    new_number = -1

    if after_paper:
        # 在指定论文后插入
        matched_idx = -1
        for i, h in enumerate(existing_headings):
            if after_paper.lower() in h['paper_name'].lower():
                matched_idx = i
                break
        
        if matched_idx == -1:
            print(f"Error: 未能在现有论文列表中匹配到 '--after' 指定的论文: '{after_paper}'")
            print("现有论文包括:")
            for h in existing_headings:
                print(f"  - {h['paper_name']}")
            sys.exit(1)
        
        target_h = existing_headings[matched_idx]
        new_number = target_h['number'] + 1
        
        # 寻找 target_h 之后的下一个二级标题 ## 或是这一大章节结束
        if matched_idx + 1 < len(existing_headings):
            insert_at_idx = existing_headings[matched_idx + 1]['index']
        else:
            insert_at_idx = section_end_idx
        
        # 寻找 insert_at_idx 之前的一个空行或分割线作为插入位置
        while insert_at_idx > target_h['index'] and lines[insert_at_idx - 1].strip() in ['', '---']:
            insert_at_idx -= 1
            
        print(f"✓ 将在论文 '{target_h['paper_name']}' 之后插入新章节，新序号为 {prefix}.{new_number} (第 {insert_at_idx+1} 行)")
        
        # 递增后续所有二级标题的序号 (从 new_number 开始)
        for h in existing_headings[matched_idx + 1:]:
            curr_line = lines[h['index']]
            curr_num = h['number']
            new_num = curr_num + 1
            updated_line = re.sub(r"^## " + prefix + r"\.\d+", f"## {prefix}.{new_num}", curr_line)
            lines[h['index']] = updated_line
            print(f"  - 递增后续论文: '{h['paper_name']}' -> {prefix}.{new_num}")
    else:
        # 默认追加到该大章节的最后一部份
        if existing_headings:
            last_h = existing_headings[-1]
            new_number = last_h['number'] + 1
        else:
            new_number = 1
        
        insert_at_idx = section_end_idx
        # 回退，在下一个大标题之前插入
        while insert_at_idx > section_start_idx and lines[insert_at_idx - 1].strip() in ['', '---']:
            insert_at_idx -= 1
            
        print(f"✓ 默认将新章节追加到大章节末尾，序号为 {prefix}.{new_number} (第 {insert_at_idx+1} 行)")

    # 5. 组装要插入的 Markdown 块
    slug = parsed_data['paper_name'].lower().replace(" ", "-").replace(".", "")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    anchor_id = f"{prefix}-{new_number}-{slug}"
    
    subtitle_line = f"——{parsed_data['subtitle']}\n\n" if parsed_data['subtitle'] else ""
    
    inserted_text = f"""## {prefix}.{new_number} {parsed_data['paper_name']} ({parsed_data['year']}) {{#{anchor_id}}}
{subtitle_line}📄 **Paper**: {parsed_data['paper_url']}

{parsed_data['body']}

---

"""
    # 插入到行列表中
    lines.insert(insert_at_idx, inserted_text)
    
    # 6. 写回文件
    with open(post_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    print(f"✓ 成功将 '{parsed_data['paper_name']}' 插入到 {post_path}")
    print(f"✓ 锚点 ID: #{anchor_id}")


def main():
    parser = argparse.ArgumentParser(description="将论文总结插入到对应的 Survey 博客文章中")
    parser.add_argument("summary_file", help="论文总结 MD 文件的路径")
    parser.add_argument("--topic", required=True, help="论文所属主题 (vla, vlm, wm/world-models, si/spatial-intelligence, vln)")
    parser.add_argument("--after", help="可选：指定插入在某篇已存在的论文名字之后 (模糊匹配)")
    parser.add_argument("--tags", help="VLN 标签 (仅用于 vln 主题)")
    parser.add_argument("--rank", action="append", help="VLN 排行榜 Spec (仅用于 vln 主题)")
    
    args, unknown = parser.parse_known_args()
    
    if args.topic.lower() in ['vln', 'vln-papers', 'vln-survey']:
        import subprocess
        vln_script = str(Path(__file__).resolve().parents[2] / 'vln-paper-insert' / 'scripts' / 'insert_paper.py')
        cmd = [sys.executable, vln_script, args.summary_file]
        if args.tags:
            cmd.extend(["--tags", args.tags])
        else:
            cmd.extend(["--tags", "连续环境"])
        if args.rank:
            for r in args.rank:
                cmd.extend(["--rank", r])
        cmd.extend(unknown)
        res = subprocess.run(cmd)
        sys.exit(res.returncode)

    parsed_data = parse_summary(args.summary_file)
    insert_into_post(args.topic, parsed_data, args.after)


if __name__ == '__main__':
    main()
