#!/usr/bin/env python3
"""从 OpenSpec 工作区收割进度，输出 JSON 供 claude-html 渲染成进度页。

用法：
    python harvest_openspec.py <项目根或 openspec 目录> [--days 7] [--out progress.json]

不带 --days 时输出全部 change；带 --days N 时只保留最近 N 天有文件改动的在途 change
和最近 N 天归档的 change（归档日期取目录名前缀 YYYY-MM-DD）。

输出结构见 references/progress.md。脚本不依赖 git（OpenSpec 工件常在版本控制之外），
一切判断走目录结构 + 文件 mtime。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

TASK_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s*(.+?)\s*$")
ARCHIVE_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[-_](.+)$")


def read_text(path: Path) -> str:
    """读文本，编码坏了也不炸——收割脚本不该因为一个乱码文件整体失败。"""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def find_openspec(start: Path) -> Path | None:
    """接受项目根或 openspec 目录本身；也往上找两层，方便在子目录里直接跑。"""
    if (start / "changes").is_dir():
        return start
    if (start / "openspec" / "changes").is_dir():
        return start / "openspec"
    for parent in list(start.parents)[:3]:
        if (parent / "openspec" / "changes").is_dir():
            return parent / "openspec"
    return None


def parse_tasks(path: Path) -> tuple[int, int, list[str]]:
    """返回 (已完成数, 总数, 未完成任务文本列表)。"""
    if not path.is_file():
        return 0, 0, []
    done = 0
    total = 0
    open_tasks: list[str] = []
    for line in read_text(path).splitlines():
        m = TASK_RE.match(line)
        if not m:
            continue
        total += 1
        if m.group(1).lower() == "x":
            done += 1
        else:
            open_tasks.append(m.group(2).strip())
    return done, total, open_tasks


def parse_section(text: str, heading: str) -> str:
    """取出 '## <heading>' 到下一个同级标题之间的正文。"""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def parse_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def newest_mtime(directory: Path) -> float:
    """目录下所有文件的最新 mtime；空目录返回目录自身的 mtime。"""
    times = [p.stat().st_mtime for p in directory.rglob("*") if p.is_file()]
    return max(times) if times else directory.stat().st_mtime


def collect_active(changes_dir: Path, cutoff: float | None) -> list[dict]:
    out: list[dict] = []
    for d in sorted(changes_dir.iterdir()):
        if not d.is_dir() or d.name == "archive":
            continue
        mtime = newest_mtime(d)
        if cutoff is not None and mtime < cutoff:
            continue
        proposal = read_text(d / "proposal.md")
        done, total, open_tasks = parse_tasks(d / "tasks.md")
        out.append(
            {
                "slug": d.name,
                "title": parse_title(proposal, d.name),
                "done": done,
                "total": total,
                "pct": round(done / total * 100) if total else 0,
                "status": "new" if done == 0 else ("ready" if done == total and total else "active"),
                "last_modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
                "why": parse_section(proposal, "Why"),
                "what": parse_section(proposal, "What Changes"),
                "open_tasks": open_tasks,
                "has_evidence": (d / "evidence").is_dir(),
            }
        )
    # 在途的排前面，同组按最后改动倒序
    out.sort(key=lambda c: (c["status"] == "new", c["last_modified"]), reverse=False)
    out.sort(key=lambda c: c["last_modified"], reverse=True)
    return out


def collect_archived(changes_dir: Path, cutoff_date: str | None) -> list[dict]:
    archive = changes_dir / "archive"
    if not archive.is_dir():
        return []
    out: list[dict] = []
    for d in sorted(archive.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        m = ARCHIVE_DATE_RE.match(d.name)
        date = m.group(1) if m else ""
        slug = m.group(2) if m else d.name
        if cutoff_date is not None and date and date < cutoff_date:
            continue
        proposal = read_text(d / "proposal.md")
        done, total, _ = parse_tasks(d / "tasks.md")
        out.append(
            {
                "slug": slug,
                "title": parse_title(proposal, slug),
                "date": date,
                "done": done,
                "total": total,
                "why": parse_section(proposal, "Why"),
            }
        )
    return out


def collect_specs(root: Path) -> list[str]:
    specs = root / "specs"
    if not specs.is_dir():
        return []
    return sorted(d.name for d in specs.iterdir() if d.is_dir())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="项目根目录，或 openspec 目录本身")
    ap.add_argument("--days", type=int, default=None, help="只保留最近 N 天有活动的条目")
    ap.add_argument("--out", help="写入文件（UTF-8）；不给则打印到 stdout")
    args = ap.parse_args()

    start = Path(args.path).expanduser().resolve()
    if not start.exists():
        print(f"路径不存在: {start}", file=sys.stderr)
        return 2

    root = find_openspec(start)
    if root is None:
        print(f"在 {start} 下没找到 openspec/changes 目录", file=sys.stderr)
        return 2

    cutoff = None
    cutoff_date = None
    if args.days is not None:
        cutoff_dt = datetime.now() - timedelta(days=args.days)
        cutoff = cutoff_dt.timestamp()
        cutoff_date = cutoff_dt.strftime("%Y-%m-%d")

    changes_dir = root / "changes"
    active = collect_active(changes_dir, cutoff)
    archived = collect_archived(changes_dir, cutoff_date)
    payload = {
        "root": str(root),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "window_days": args.days,
        "totals": {
            "active": len([c for c in active if c["status"] == "active"]),
            "new": len([c for c in active if c["status"] == "new"]),
            "ready": len([c for c in active if c["status"] == "ready"]),
            "archived": len(archived),
            "tasks_done": sum(c["done"] for c in active),
            "tasks_total": sum(c["total"] for c in active),
        },
        "active": active,
        "archived": archived,
        "specs": collect_specs(root),
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"已写入 {args.out}", file=sys.stderr)
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台默认 GBK，中文会炸
        except AttributeError:
            pass
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
