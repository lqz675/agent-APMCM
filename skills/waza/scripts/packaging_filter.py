#!/usr/bin/env python3
"""Filter stdin paths through packaging.allowlist. Default-deny."""

import fnmatch
import re
import sys
from pathlib import Path

EXCLUDE_RE = re.compile(
    r"(^skills/[^/]+/SKILL\.md$"
    r"|(^|/)__pycache__/"
    r"|\.pyc$"
    r"|(^|/)\.DS_Store$)"
)


def load_patterns(path: Path) -> list[str]:
    patterns = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def allowed(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat.endswith("/**"):
            prefix = pat[:-3]
            if path == prefix or path.startswith(prefix + "/"):
                return True
        elif fnmatch.fnmatch(path, pat):
            return True
    return False


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: packaging_filter.py <allowlist-path>", file=sys.stderr)
        return 2
    patterns = load_patterns(Path(sys.argv[1]))
    for line in sys.stdin:
        path = line.rstrip("\n")
        if not path:
            continue
        if EXCLUDE_RE.search(path):
            continue
        if allowed(path, patterns):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
