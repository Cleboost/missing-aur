"""Safe, line-oriented manifest edits (no full-file YAML rewrite)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .manifest_io import load_manifest, normalized_pkgdesc
from .paths import HOISTABLE_VARIANT_FIELDS


def _remove_line(lines: list[str], pattern: str) -> bool:
    regex = re.compile(pattern)
    kept: list[str] = []
    removed = False
    for line in lines:
        if not removed and regex.match(line):
            removed = True
            continue
        kept.append(line)
    lines[:] = kept
    return removed


def _remove_variant_field(lines: list[str], field: str) -> bool:
    pattern = re.compile(rf"^    {re.escape(field)}:.*(?:\n|$)")
    kept = [line for line in lines if not pattern.match(line)]
    changed = len(kept) != len(lines)
    lines[:] = kept
    return changed


def _first_variant_field_line(lines: list[str], field: str) -> str | None:
    pattern = re.compile(rf"^    {re.escape(field)}: (.*)$")
    for line in lines:
        match = pattern.match(line.rstrip("\n"))
        if match:
            return f"{field}: {match.group(1)}\n"
    return None


def _format_field_line(field: str, value) -> str:
    if isinstance(value, str):
        return f'{field}: "{value}"\n'
    if isinstance(value, list):
        rendered = yaml.dump(value, default_flow_style=True).strip()
        return f"{field}: {rendered}\n"
    return f"{field}: {value}\n"


def _insert_before_variants(lines: list[str], new_lines: list[str]) -> bool:
    for index, line in enumerate(lines):
        if line.startswith("variants:"):
            lines[index:index] = new_lines
            return True
    return False


def _hoist_duplicate_fields(lines: list[str], data: dict) -> bool:
    variants = data.get("variants") or {}
    if not isinstance(variants, dict) or len(variants) < 2:
        return False

    to_hoist: dict[str, object] = {}
    for field in sorted(HOISTABLE_VARIANT_FIELDS):
        if field in data:
            continue
        values = []
        for variant in variants.values():
            if not isinstance(variant, dict) or field not in variant:
                break
            values.append(variant[field])
        else:
            if len({repr(value) for value in values}) == 1:
                to_hoist[field] = values[0]

    if not to_hoist:
        return False

    insert_lines = []
    for field in to_hoist:
        line = _first_variant_field_line(lines, field) or _format_field_line(field, to_hoist[field])
        insert_lines.append(line)
    if not insert_lines[-1].endswith("\n\n"):
        insert_lines.append("\n")

    changed = _insert_before_variants(lines, insert_lines)
    for field in to_hoist:
        changed |= _remove_variant_field(lines, field)
    return changed


def _replace_external_aur(lines: list[str], packages: list[str]) -> bool:
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^  externalAur:\s*$", line):
            start = i
            break
    if start is None:
        return False

    end = start + 1
    while end < len(lines) and re.match(r"^    - ", lines[end]):
        end += 1

    new_block = ["  externalAur:\n"] + [f"    - {pkg}\n" for pkg in packages]
    if lines[start:end] == new_block:
        return False
    lines[start:end] = new_block
    return True


def apply_safe_fixes(path: Path) -> bool:
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    data = load_manifest(path)
    changed = False

    docs = data.get("docs")
    if docs is None:
        docs = {}

    pkgdesc = normalized_pkgdesc(str(data.get("pkgdesc", "")))
    if docs.get("description") and normalized_pkgdesc(str(docs["description"])) == pkgdesc:
        changed |= _remove_line(lines, r"^  description:.*$")

    if "docs" in data and not docs:
        changed |= _remove_line(lines, r"^docs:\s*$")

    external = docs.get("externalAur")
    if isinstance(external, list) and external != sorted(external):
        changed |= _replace_external_aur(lines, sorted(external))

    changed |= _hoist_duplicate_fields(lines, data)

    if changed:
        path.write_text("".join(lines))
    return changed
