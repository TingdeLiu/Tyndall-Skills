# -*- coding: utf-8 -*-
"""按随包默认上限检查长度（UTF-16 code unit，多数 emoji 计 2）。
实际发布限制以平台当前提示为准。

用法:
    python count.py body.txt
    python count.py body.txt title.txt
    echo "文本" | python count.py -
超限时返回退出码 1，便于在循环里自检。
"""
import sys

BODY_LIMIT = 1000
TITLE_LIMIT = 20


def count(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def main() -> int:
    args = sys.argv[1:] or ["-"]
    bad = False
    for i, path in enumerate(args):
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        text = text.strip("\n")
        n = count(text)
        limit = TITLE_LIMIT if (len(args) > 1 and i == 1) else BODY_LIMIT
        flag = "OK " if n <= limit else "OVER"
        if n > limit:
            bad = True
        print(f"{flag} {n}/{limit}  {path}  (超出 {max(0, n - limit)})")
    return 1 if bad else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
