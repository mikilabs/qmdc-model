#!/usr/bin/env python3
"""Bump the qmdc-model version in pyproject.toml (the single source of truth).

Usage:
    python3 scripts/bump_version.py patch   # 0.3.0 -> 0.3.1
    python3 scripts/bump_version.py minor   # 0.3.0 -> 0.4.0
    python3 scripts/bump_version.py major   # 0.3.0 -> 1.0.0

The package reads its own version from installed metadata, so nothing else needs
editing. Run `uv lock` afterwards so uv.lock records the new version.
"""

import re
import sys
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
VERSION_LINE = re.compile(r'^version = "(\d+)\.(\d+)\.(\d+)"$', re.MULTILINE)


def main(argv: list[str]) -> int:
    part = argv[0] if argv else "patch"
    if part not in ("major", "minor", "patch"):
        print(__doc__, file=sys.stderr)
        return 2

    text = PYPROJECT.read_text(encoding="utf-8")
    matches = VERSION_LINE.findall(text)
    if len(matches) != 1:
        print(f"expected exactly one 'version = \"X.Y.Z\"' line in {PYPROJECT}, "
              f"found {len(matches)}", file=sys.stderr)
        return 1

    major, minor, patch = map(int, matches[0])
    old = f"{major}.{minor}.{patch}"
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new = f"{major}.{minor}.{patch}"

    PYPROJECT.write_text(VERSION_LINE.sub(f'version = "{new}"', text), encoding="utf-8")
    print(f"qmdc-model {old} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
