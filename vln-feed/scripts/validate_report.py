#!/usr/bin/env python3
"""Validate the structure and image-free policy of a generated VLN report."""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


REQUIRED_HEADINGS = (
    "## 一、本期结论",
    "## 二、优先阅读清单",
    "## 三、重点工作分析",
    "## 四、可迁移方法",
    "## 五、分类速览",
    "## 六、趋势判断与行动建议",
)

FORBIDDEN_PATTERNS = (
    (re.compile(r"!\[[^\]]*\]\([^)]+\)", re.IGNORECASE), "Markdown 图片"),
    (re.compile(r"<\s*img\b", re.IGNORECASE), "HTML <img>"),
    (re.compile(r"<\s*/?\s*figure\b", re.IGNORECASE), "HTML <figure>"),
    (re.compile(r"(?:https?:)?//mmbiz\.qpic\.cn", re.IGNORECASE), "微信图片链接"),
)


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    if not re.search(r"^# 具身导航周报", text, re.MULTILINE):
        errors.append("缺少以“# 具身导航周报”开头的报告标题")

    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"缺少核心章节：{heading}")

    positions = [text.find(heading) for heading in REQUIRED_HEADINGS]
    existing_positions = [position for position in positions if position >= 0]
    if existing_positions != sorted(existing_positions):
        errors.append("核心章节顺序不符合模板")

    for pattern, label in FORBIDDEN_PATTERNS:
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"第 {line} 行包含禁止内容：{label}")

    # 2026-09-27 起全篇禁用表格：博客在手机上打开时宽表格要左右滑，读者反馈
    # 很难读。结构化信息一律改写成列表或「**标签。** 段落」，见 report-format.md。
    table_sep = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", re.MULTILINE)
    match = table_sep.search(text)
    if match:
        line = text.count("\n", 0, match.start())  # 分隔行的上一行即表头
        errors.append(f"第 {line} 行起是 Markdown 表格；全篇禁用表格，请改成列表")

    start = text.find("## 二、优先阅读清单")
    end = text.find("## 三、重点工作分析")
    if start >= 0 and end > start and not re.search(
            r"^\d+\. \*\*\[", text[start:end], re.MULTILINE):
        errors.append("“优先阅读清单”应为编号列表，每项以 **[工作名](链接)** 开头")

    if re.search(r"https?://[^\s|)]+(?:\s*\|\s*项目页：)?\s*https?://", text):
        errors.append("发现疑似连续裸链接；请改为有标签的 Markdown 链接并核验归属")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python scripts/validate_report.py <report.md>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"报告不存在: {path}", file=sys.stderr)
        return 2

    errors = validate(path)
    if errors:
        print(f"报告校验失败（{len(errors)} 项）:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"报告校验通过: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
