#!/usr/bin/env python3
"""Check and resize package icons for the README table."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.git_changed import manifest_paths
from lib.issues import Issue
from lib.paths import ICON_SIZE, icon_path

try:
    from PIL import Image
except ImportError:
    Image = None


def check_icon(app_dir: Path) -> list[Issue]:
    icon = icon_path(app_dir)
    rel = icon.relative_to(app_dir.parents[1]).as_posix()
    if not icon.is_file():
        return []

    if Image is None:
        return [
            Issue(
                rel,
                "missing-pillow",
                "Pillow is required to verify icon size.",
            )
        ]

    with Image.open(icon) as img:
        if img.size != (ICON_SIZE, ICON_SIZE):
            return [
                Issue(
                    rel,
                    "icon-size",
                    f"Icon must be {ICON_SIZE}x{ICON_SIZE}px (got {img.size[0]}x{img.size[1]}px).",
                    fixable=True,
                )
            ]
    return []


def fix_icon(app_dir: Path) -> bool:
    icon = icon_path(app_dir)
    if not icon.is_file() or Image is None:
        return False

    with Image.open(icon) as img:
        if img.size == (ICON_SIZE, ICON_SIZE):
            return False
        resized = img.convert("RGBA").resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
        resized.save(icon, format="PNG")
        return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Check and resize package icons")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("check", "fix"):
        parser = sub.add_parser(name, help=f"{name} package icons")
        parser.add_argument("apps", nargs="*", help="Package app names under packages/")

    args = ap.parse_args()

    app_dirs = [path.parent for path in manifest_paths(args.apps or None)]

    if args.cmd == "check":
        issues: list[Issue] = []
        for app_dir in app_dirs:
            issues.extend(check_icon(app_dir))
        if issues:
            for issue in issues:
                print(issue.format_line(), file=sys.stderr)
            sys.exit(1)
        print(f"Checked {len(app_dirs)} package icon(s): OK")
        return

    fixed = 0
    for app_dir in app_dirs:
        if fix_icon(app_dir):
            print(f"Resized {icon_path(app_dir).relative_to(app_dir.parents[1])}")
            fixed += 1
    print(f"Resized {fixed} icon(s).")


if __name__ == "__main__":
    main()
