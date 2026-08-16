#!/usr/bin/env python3
"""Generate the README package table from manifests in packages/."""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import yaml
except ImportError:
    print("PyYAML required: pacman -S python-yaml", file=sys.stderr)
    sys.exit(1)

from lib.paths import (
    BASE_VARIANT_KEYS,
    ICON_FILENAME,
    PACKAGES_DIR,
    README,
    REPO_ROOT,
    pkgname,
)

TABLE_START = "| | App | Packages |"
TABLE_SEP = "|:---:|:---|:---|"
TABLE_END_MARKER = "## How it works"


def load_app(manifest_path: Path) -> dict:
    data = yaml.safe_load(manifest_path.read_text()) or {}
    docs = data.get("docs") or {}
    app_dir = manifest_path.parent
    name = data["name"]
    url = data.get("url", "")
    variants = data.get("variants") or {}

    maintained = sorted(pkgname(name, key) for key in variants)
    # docs.description is optional; fall back to top-level pkgdesc.
    description = docs.get("description") or data.get("pkgdesc", "")
    if description.endswith(")"):
        description = re.sub(r"\s+\([^)]+\)$", "", description)

    return {
        "name": name,
        "url": url,
        "description": description,
        "app_dir": app_dir,
        "maintained": maintained,
        "externalAur": sorted(docs.get("externalAur") or []),
    }


def icon_cell(app_dir: Path) -> str:
    icon = app_dir / ICON_FILENAME
    if icon.is_file():
        rel = icon.relative_to(REPO_ROOT).as_posix()
        return f"![](./{rel})"
    return "-"


def badge(pkgname: str, *, external: bool = False) -> str:
    color = "&color=purple" if external else ""
    return (
        f"[![{pkgname}](https://img.shields.io/aur/version/{pkgname}"
        f"?style=flat-square&label={pkgname}{color})]"
        f"(https://aur.archlinux.org/packages/{pkgname})"
    )


def render_row(app: dict) -> str:
    badges = [badge(p) for p in app["maintained"]]
    badges.extend(badge(p, external=True) for p in app["externalAur"])
    badge_cell = " ".join(badges)

    return (
        f"| {icon_cell(app['app_dir'])} "
        f"| **[{app['name']}]({app['url']})**<br>{app['description']} "
        f"| {badge_cell} |"
    )


def generate_rows() -> list[str]:
    apps = []
    for manifest in sorted(PACKAGES_DIR.glob("*/manifest.yaml")):
        apps.append(load_app(manifest))
    apps.sort(key=lambda app: app["name"].casefold())
    return [render_row(app) for app in apps]


def parse_readme_table(text: str) -> tuple[str, list[str], str]:
    start = text.index(TABLE_START)
    end = text.index(TABLE_END_MARKER, start)
    before = text[:start]
    after = text[end:]
    lines = text[start:end].splitlines()
    if lines[:2] != [TABLE_START, TABLE_SEP]:
        raise ValueError("README package table header is not in expected format")
    rows = [line for line in lines[2:] if line.strip()]
    return before, rows, after


def write_readme(before: str, rows: list[str], after: str) -> None:
    table = "\n".join([TABLE_START, TABLE_SEP, *rows, ""])
    README.write_text(before + table + "\n" + after)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate README package table from manifests")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="Exit 1 if README table does not match manifests")
    sub.add_parser("fix", help="Regenerate README package table from manifests")
    args = ap.parse_args()

    expected = generate_rows()
    text = README.read_text()
    before, current, after = parse_readme_table(text)

    if args.cmd == "check":
        if current == expected:
            print("README package table matches manifests.")
            sys.exit(0)
        print("README package table is out of date:", file=sys.stderr)
        for i, (got, want) in enumerate(zip(current, expected)):
            if got != want:
                print(f"  first mismatch at row {i + 1}", file=sys.stderr)
                break
        if len(current) != len(expected):
            print(f"  row count: got {len(current)}, expected {len(expected)}", file=sys.stderr)
        sys.exit(1)

    if current == expected:
        print("README package table already up to date.")
        return

    write_readme(before, expected, after)
    print(f"Updated {README.relative_to(REPO_ROOT)} ({len(expected)} packages).")


if __name__ == "__main__":
    main()
