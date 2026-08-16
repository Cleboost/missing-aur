#!/usr/bin/env python3
"""Lint and auto-optimize package manifests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.git_changed import manifest_paths
from lib.issues import Issue
from lib.manifest_fix import apply_safe_fixes
from lib.manifest_io import load_manifest, normalized_pkgdesc
from lib.paths import HOISTABLE_VARIANT_FIELDS, REQUIRED_TOP_LEVEL


def _variant_dicts(data: dict) -> dict[str, dict]:
    variants = data.get("variants")
    if not isinstance(variants, dict) or not variants:
        return {}
    return {key: (value or {}) for key, value in variants.items()}


def check_manifest(path: Path) -> list[Issue]:
    issues: list[Issue] = []
    rel = path.relative_to(path.parents[2]).as_posix()
    app_name = path.parent.name

    try:
        data = load_manifest(path)
    except Exception as exc:
        return [Issue(rel, "parse-error", str(exc))]

    name = data.get("name")
    if not name:
        issues.append(Issue(rel, "missing-name", "`name` is required."))
    elif name != app_name:
        issues.append(
            Issue(
                rel,
                "name-mismatch",
                f"`name` is {name!r} but directory is {app_name!r}.",
            )
        )

    for field in REQUIRED_TOP_LEVEL:
        if field == "name":
            continue
        if field not in data or data[field] in (None, "", {}):
            issues.append(Issue(rel, f"missing-{field}", f"`{field}` is required."))

    variants = _variant_dicts(data)
    if not variants:
        return issues

    for key, variant in variants.items():
        if not isinstance(variant, dict):
            issues.append(Issue(rel, "invalid-variant", f"Variant {key!r} must be a mapping."))
            continue
        has_pkgver = "pkgver" in variant and variant["pkgver"] not in (None, "")
        has_pkgver_func = bool(variant.get("pkgver_func"))
        if not has_pkgver and not has_pkgver_func and not data.get("pkgver"):
            issues.append(
                Issue(
                    rel,
                    "missing-pkgver",
                    f"Variant {key!r} needs `pkgver` or `pkgver_func`.",
                )
            )

    for field in sorted(HOISTABLE_VARIANT_FIELDS):
        values = [variant.get(field) for variant in variants.values() if field in variant]
        if len(values) < 2:
            continue
        if len(values) != len(variants):
            continue
        if len({repr(value) for value in values}) == 1 and field not in data:
            issues.append(
                Issue(
                    rel,
                    "duplicate-field",
                    f"`{field}` is identical in every variant; hoist it to the top level.",
                    fixable=True,
                )
            )

    docs = data.get("docs") or {}
    if data.get("docs") is None and "docs" in data:
        docs = {}
    if docs.get("description"):
        pkgdesc = data.get("pkgdesc", "")
        if normalized_pkgdesc(docs["description"]) == normalized_pkgdesc(str(pkgdesc)):
            issues.append(
                Issue(
                    rel,
                    "redundant-docs-description",
                    "`docs.description` duplicates `pkgdesc`; remove it.",
                    fixable=True,
                )
            )

    if docs == {} and "docs" in data:
        issues.append(
            Issue(
                rel,
                "empty-docs",
                "`docs` block is empty; remove it.",
                fixable=True,
            )
        )

    external = docs.get("externalAur")
    if isinstance(external, list) and external != sorted(external):
        issues.append(
            Issue(
                rel,
                "unsorted-external-aur",
                "`docs.externalAur` should be sorted alphabetically.",
                fixable=True,
            )
        )

    return issues


def fix_manifest(path: Path) -> bool:
    return apply_safe_fixes(path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Lint and optimize package manifests")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("check", "fix"):
        parser = sub.add_parser(name, help=f"{name} manifests")
        parser.add_argument(
            "apps",
            nargs="*",
            help="Package app names under packages/ (default: all manifests)",
        )

    args = ap.parse_args()

    paths = manifest_paths(args.apps or None)
    if args.cmd == "check":
        issues: list[Issue] = []
        for path in paths:
            issues.extend(check_manifest(path))
        if issues:
            for issue in issues:
                print(issue.format_line(), file=sys.stderr)
            sys.exit(1)
        print(f"Checked {len(paths)} manifest(s): OK")
        return

    fixed = 0
    for path in paths:
        if fix_manifest(path):
            print(f"Optimized {path.relative_to(path.parents[2])}")
            fixed += 1
    print(f"Optimized {fixed} manifest(s).")


if __name__ == "__main__":
    main()
