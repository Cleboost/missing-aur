#!/usr/bin/env python3
"""Check or fix alphabetical order of packages in README.md table."""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

TABLE_START = "| | App | Packages |"
TABLE_SEP = "|:---:|:---|:---|"
TABLE_END_MARKER = "## How it works"

ROW_RE = re.compile(r"^\| !\[\]\(\./docs/icons/([^)]+)\.png\)")


def extract_name(row: str) -> str:
    match = re.search(r"\*\*\[([^\]]+)\]", row)
    if not match:
        raise ValueError(f"cannot parse package name from row: {row[:80]}...")
    return match.group(1)


def parse_readme(text: str) -> tuple[str, list[str], str]:
    start = text.index(TABLE_START)
    end = text.index(TABLE_END_MARKER, start)

    before = text[:start]
    table_block = text[start:end]
    after = text[end:]

    lines = table_block.splitlines()
    if len(lines) < 2 or lines[0] != TABLE_START or lines[1] != TABLE_SEP:
        raise ValueError("README package table header is not in expected format")

    rows = [line for line in lines[2:] if line.strip()]
    data_rows = []
    for line in rows:
        if not ROW_RE.match(line):
            raise ValueError(f"unexpected table row: {line[:80]}...")
        data_rows.append(line)

    return before, data_rows, after


def sorted_rows(rows: list[str]) -> list[str]:
    return sorted(rows, key=lambda row: extract_name(row).casefold())


def check(rows: list[str]) -> bool:
    names = [extract_name(row) for row in rows]
    expected = [extract_name(row) for row in sorted_rows(rows)]
    if names == expected:
        print("README package table is sorted alphabetically.")
        return True

    print("README package table is not sorted alphabetically:", file=sys.stderr)
    for i, (got, want) in enumerate(zip(names, expected)):
        if got != want:
            print(f"  position {i + 1}: got {got!r}, expected {want!r}", file=sys.stderr)
            break
    print(f"  expected order: {', '.join(expected)}", file=sys.stderr)
    return False


def fix(rows: list[str]) -> list[str]:
    ordered = sorted_rows(rows)
    if rows == ordered:
        print("README package table already sorted.")
        return rows

    old_names = [extract_name(row) for row in rows]
    new_names = [extract_name(row) for row in ordered]
    print("Reordered packages:")
    for name in new_names:
        old_idx = old_names.index(name)
        new_idx = new_names.index(name)
        if old_idx != new_idx:
            print(f"  {name}: {old_idx + 1} → {new_idx + 1}")
    return ordered


def write_readme(before: str, rows: list[str], after: str) -> None:
    table = "\n".join([TABLE_START, TABLE_SEP, *rows, ""])
    README.write_text(before + table + "\n" + after)


def main() -> None:
    ap = argparse.ArgumentParser(description="Check or fix README package table order")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Exit 1 if packages are not alphabetically sorted")
    sub.add_parser("fix", help="Sort packages alphabetically in README.md")

    args = ap.parse_args()
    text = README.read_text()
    before, rows, after = parse_readme(text)

    if args.cmd == "check":
        sys.exit(0 if check(rows) else 1)

    ordered = fix(rows)
    if ordered != rows:
        write_readme(before, ordered, after)
        print(f"Updated {README.relative_to(REPO_ROOT)}.")


if __name__ == "__main__":
    main()
