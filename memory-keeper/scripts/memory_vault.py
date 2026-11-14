#!/usr/bin/env python3
"""Memory Keeper vault helper. Standard library only.

Usage:
  python memory_vault.py suggest [--language zh|en]
  python memory_vault.py init  <vault_path> [--auto-save] [--language zh|en]
  python memory_vault.py index [<vault_path>]
  python memory_vault.py stats [<vault_path>]
  python memory_vault.py config

When <vault_path> is omitted, it is read from ~/.memory-keeper/config.json.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

SCHEMA = 1
CONFIG_PATH = Path.home() / ".memory-keeper" / "config.json"
SUBDIRS = ("memories", "people", "capsules")

# Make stdout UTF-8 on Windows consoles that default to a legacy code page.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


# ---------------------------------------------------------------- frontmatter

def parse_frontmatter(text: str) -> dict:
    """Parse the flat `key: value` / `key: [a, b]` frontmatter used by the vault."""
    text = text.lstrip("﻿")
    m = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*(\r?\n|$)", text, re.S)
    if not m:
        return {}
    data: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            data[key] = [v for v in items if v]
        else:
            data[key] = value.strip("'\"")
    return data


def read_entries(folder: Path) -> list[tuple[str, dict]]:
    entries = []
    if not folder.is_dir():
        return entries
    for path in sorted(folder.glob("*.md")):
        try:
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            print(f"warning: skip {path.name}: {exc}", file=sys.stderr)
            continue
        entries.append((path.stem, meta))
    return entries


def as_list(value) -> list[str]:
    if isinstance(value, list):
        return value
    return [value] if value else []


# --------------------------------------------------------------------- config

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def resolve_vault(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    vault = load_config().get("vault_path")
    if not vault:
        sys.exit(f"error: no vault path given and none configured in {CONFIG_PATH}")
    return Path(vault).expanduser()


# ----------------------------------------------------------------------- init

README_ZH = """# 我的记忆

这个文件夹由 Memory Keeper 管理，里面是你和家人的故事。

- `memories/`：一段记忆一个文件
- `people/`：人物档案
- `capsules/`：写给某人的信
- `INDEX.md`：总索引（自动生成）
- `profile.md`：关于你

所有文件都是普通 Markdown，你可以直接打开、修改、备份。
放进 iCloud / OneDrive 等同步盘可以在多台设备上使用。
"""

README_EN = """# My Memories

This folder is managed by Memory Keeper and holds your and your family's stories.

- `memories/`: one file per memory
- `people/`: one profile per person
- `capsules/`: letters to someone
- `INDEX.md`: generated index
- `profile.md`: about you

Everything is plain Markdown: open, edit and back it up freely.
"""


def cmd_init(args) -> None:
    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    for sub in SUBDIRS:
        (vault / sub).mkdir(exist_ok=True)

    zh = args.language == "zh"
    write_if_missing(vault / "README.md", README_ZH if zh else README_EN)
    write_if_missing(
        vault / "profile.md",
        f"---\nschema: {SCHEMA}\ntype: profile\nname:\n---\n\n"
        + ("## 关于我\n\n\n## 说话方式\n" if zh else "## About me\n\n\n## How I talk\n"),
    )

    config = load_config()
    config.update(
        {
            "schema": SCHEMA,
            "vault_path": vault.as_posix(),
            "auto_save": bool(args.auto_save or config.get("auto_save", False)),
            "language": args.language,
        }
    )
    config.setdefault("created", dt.date.today().isoformat())
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    build_index(vault)
    print(f"vault ready: {vault}")
    print(f"config written: {CONFIG_PATH}")


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------- index

def build_index(vault: Path) -> dict:
    memories = read_entries(vault / "memories")
    people = read_entries(vault / "people")
    capsules = read_entries(vault / "capsules")

    # Newest event first is hard with fuzzy dates; sort by record date, newest first.
    memories.sort(key=lambda e: (e[1].get("recorded", ""), e[0]), reverse=True)

    mention_count: dict[str, int] = {}
    for _, meta in memories:
        for person in as_list(meta.get("people")):
            mention_count[person] = mention_count.get(person, 0) + 1

    lines = [
        "# 记忆索引",
        "",
        "<!-- 由 memory_vault.py 自动生成，手动修改会在下次生成时被覆盖 -->",
        "",
        f"共 {len(memories)} 段记忆 · {len(people)} 位人物 · {len(capsules)} 封信",
        "",
        "## 记忆",
        "",
    ]
    for stem, meta in memories:
        parts = [meta.get("recorded", "?"), f"[[{stem}]]", f"讲述：{meta.get('narrator') or '我'}"]
        if meta.get("event_date"):
            parts.append(f"时间：{meta['event_date']}")
        if as_list(meta.get("people")):
            parts.append("、".join(as_list(meta.get("people"))))
        if meta.get("mood"):
            parts.append(meta["mood"])
        line = "- " + " · ".join(parts)
        if meta.get("summary"):
            line += f" — {meta['summary']}"
        lines.append(line)

    lines += ["", "## 人物", ""]
    for stem, meta in people:
        relation = meta.get("relation") or ""
        count = mention_count.get(stem, 0)
        lines.append(f"- [[{stem}]]" + (f" · {relation}" if relation else "") + f" · {count} 段记忆")

    lines += ["", "## 信件", ""]
    for stem, meta in capsules:
        deliver = " ".join(x for x in (meta.get("deliver_mode", ""), meta.get("deliver_value", "")) if x)
        lines.append(
            f"- [[{stem}]] · 给 {meta.get('to') or '?'}"
            + (f" · {deliver}" if deliver else "")
            + f" · {meta.get('status') or 'draft'}"
        )

    (vault / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"memories": memories, "people": people, "capsules": capsules, "mentions": mention_count}


def cmd_index(args) -> None:
    vault = resolve_vault(args.vault)
    require_vault(vault)
    result = build_index(vault)
    print(
        f"INDEX.md updated: {len(result['memories'])} memories, "
        f"{len(result['people'])} people, {len(result['capsules'])} capsules"
    )


# ---------------------------------------------------------------------- stats

def cmd_stats(args) -> None:
    vault = resolve_vault(args.vault)
    require_vault(vault)
    memories = read_entries(vault / "memories")
    people = read_entries(vault / "people")
    capsules = read_entries(vault / "capsules")

    narrators: dict[str, int] = {}
    mentions: dict[str, int] = {}
    for _, meta in memories:
        n = meta.get("narrator") or "我"
        narrators[n] = narrators.get(n, 0) + 1
        for p in as_list(meta.get("people")):
            mentions[p] = mentions.get(p, 0) + 1

    known = {stem for stem, _ in people}
    missing_people = sorted(p for p in mentions if p not in known)

    print(
        json.dumps(
            {
                "vault": vault.as_posix(),
                "memories": len(memories),
                "people": len(people),
                "capsules": len(capsules),
                "by_narrator": narrators,
                "most_mentioned": sorted(mentions.items(), key=lambda kv: -kv[1])[:5],
                "people_without_profile": missing_people,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def documents_dir() -> Path:
    """The user's real Documents folder (Windows may redirect it, e.g. to OneDrive)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_PERSONAL = 5 (Documents), SHGFP_TYPE_CURRENT = 0
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
                return Path(buf.value)
        except (OSError, AttributeError):
            pass
    docs = Path.home() / "Documents"
    return docs if docs.is_dir() else Path.home()


def cmd_suggest(args) -> None:
    name = "我的记忆" if args.language == "zh" else "My Memories"
    print((documents_dir() / name).as_posix())


def cmd_config(_args) -> None:
    config = load_config()
    print(json.dumps({"config_path": CONFIG_PATH.as_posix(), **config}, ensure_ascii=False, indent=2))


def require_vault(vault: Path) -> None:
    if not vault.is_dir():
        sys.exit(f"error: vault not found: {vault}")


# ----------------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser(description="Memory Keeper vault helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a vault and write the config")
    p_init.add_argument("vault")
    p_init.add_argument("--auto-save", action="store_true")
    p_init.add_argument("--language", choices=("zh", "en"), default="zh")
    p_init.set_defaults(func=cmd_init)

    for name, func, help_text in (
        ("index", cmd_index, "rebuild INDEX.md"),
        ("stats", cmd_stats, "print vault statistics as JSON"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("vault", nargs="?")
        p.set_defaults(func=func)

    p_suggest = sub.add_parser("suggest", help="print the recommended vault path")
    p_suggest.add_argument("--language", choices=("zh", "en"), default="zh")
    p_suggest.set_defaults(func=cmd_suggest)

    sub.add_parser("config", help="show the current config").set_defaults(func=cmd_config)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
