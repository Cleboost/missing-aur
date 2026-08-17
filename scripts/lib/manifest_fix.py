"""Safe, line-oriented manifest edits (no full-file YAML rewrite)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .manifest_io import load_manifest, normalized_pkgdesc
from .paths import HOISTABLE_VARIANT_FIELDS, REPO_ROOT
from .variant_relations import (
    as_string_list,
    expected_auto_conflicts,
    provides_base_enabled,
    redundant_provides_value,
)


def is_git_variant(variant_key: str, variant: dict) -> bool:
    return variant_key == "git" or bool(variant.get("pkgver_func"))


def effective_pkgver(data: dict, variant: dict) -> str | None:
    own = variant.get("pkgver")
    if own not in (None, ""):
        return str(own)
    shared = data.get("pkgver")
    if shared not in (None, ""):
        return str(shared)
    return None


def _manifest_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def _remove_pkgrel_fields(lines: list[str]) -> bool:
    kept = [
        line
        for line in lines
        if not re.match(r"^pkgrel:\s*", line) and not re.match(r"^    pkgrel:\s*", line)
    ]
    changed = len(kept) != len(lines)
    lines[:] = kept
    return changed


def _replace_top_level_field(lines: list[str], field: str, value: str) -> bool:
    pattern = re.compile(rf"^{re.escape(field)}:\s*.*$")
    replacement = f'{field}: "{value}"\n'
    for index, line in enumerate(lines):
        if pattern.match(line.rstrip("\n")):
            if line == replacement:
                return False
            lines[index] = replacement
            return True
    return False


def _replace_variant_field(lines: list[str], variant_key: str, field: str, value: str) -> bool:
    in_variant = False
    replacement = f'    {field}: "{value}"\n'
    for index, line in enumerate(lines):
        if re.match(rf"^  {re.escape(variant_key)}:\s*$", line.rstrip("\n")):
            in_variant = True
            continue
        if in_variant:
            if re.match(r"^  \w+:\s*$", line.rstrip("\n")):
                break
            if re.match(rf"^    {re.escape(field)}:\s*", line.rstrip("\n")):
                if line == replacement:
                    return False
                lines[index] = replacement
                return True
    return False


def _fix_new_package_pkgver(lines: list[str], data: dict) -> list[str]:
    variants = data.get("variants") or {}
    if not isinstance(variants, dict):
        return []

    changed_variants: list[str] = []
    non_git = {
        key: (variant or {})
        for key, variant in variants.items()
        if isinstance(variant, dict) and not is_git_variant(key, variant)
    }

    for key, variant in non_git.items():
        own = variant.get("pkgver")
        if own not in (None, "") and str(own) != "0":
            if _replace_variant_field(lines, key, "pkgver", "0"):
                changed_variants.append(key)

    top = data.get("pkgver")
    if top not in (None, "") and str(top) != "0":
        inheritors = [key for key, variant in non_git.items() if variant.get("pkgver") in (None, "")]
        if inheritors and _replace_top_level_field(lines, "pkgver", "0"):
            changed_variants.extend(inheritors)

    return sorted(set(changed_variants))


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


def _hoist_duplicate_fields(lines: list[str], data: dict) -> list[str]:
    variants = data.get("variants") or {}
    if not isinstance(variants, dict) or len(variants) < 2:
        return []

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
        return []

    insert_lines = []
    for field in to_hoist:
        line = _first_variant_field_line(lines, field) or _format_field_line(field, to_hoist[field])
        insert_lines.append(line)
    if not insert_lines[-1].endswith("\n\n"):
        insert_lines.append("\n")

    _insert_before_variants(lines, insert_lines)
    for field in to_hoist:
        _remove_variant_field(lines, field)
    return sorted(to_hoist)


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


def _remove_top_level_field(lines: list[str], field: str) -> bool:
    pattern = re.compile(rf"^{re.escape(field)}:.*(?:\n|$)")
    kept = [line for line in lines if not pattern.match(line)]
    changed = len(kept) != len(lines)
    lines[:] = kept
    return changed


def _remove_variant_field_for_key(lines: list[str], variant_key: str, field: str) -> bool:
    in_variant = False
    kept: list[str] = []
    removed = False
    field_pattern = re.compile(rf"^    {re.escape(field)}:.*$")

    for line in lines:
        if re.match(rf"^  {re.escape(variant_key)}:\s*$", line.rstrip("\n")):
            in_variant = True
            kept.append(line)
            continue
        if in_variant:
            if re.match(r"^  \w+:\s*$", line.rstrip("\n")):
                in_variant = False
            elif field_pattern.match(line.rstrip("\n")):
                removed = True
                continue
        kept.append(line)

    changed = removed
    lines[:] = kept
    return changed


def _replace_variant_conflicts(lines: list[str], variant_key: str, conflicts: list[str]) -> bool:
    in_variant = False
    replacement = f"    conflicts: {yaml.dump(conflicts, default_flow_style=True).strip()}\n"
    for index, line in enumerate(lines):
        if re.match(rf"^  {re.escape(variant_key)}:\s*$", line.rstrip("\n")):
            in_variant = True
            continue
        if in_variant:
            if re.match(r"^  \w+:\s*$", line.rstrip("\n")):
                break
            if re.match(r"^    conflicts:\s*", line.rstrip("\n")):
                if line == replacement:
                    return False
                lines[index] = replacement
                return True
    return False


def _fix_redundant_variant_relations(lines: list[str], data: dict) -> list[str]:
    if not provides_base_enabled(data):
        return []

    fixes: list[str] = []
    name = data.get("name")
    variants = data.get("variants") or {}
    if not name or not isinstance(variants, dict):
        return fixes

    if redundant_provides_value(data, data.get("provides")):
        if _remove_top_level_field(lines, "provides"):
            fixes.append("provides")

    for key, variant in variants.items():
        if not isinstance(variant, dict):
            continue
        if redundant_provides_value(data, variant.get("provides")):
            if _remove_variant_field_for_key(lines, key, "provides"):
                fixes.append(f"provides:{key}")

        manual_conflicts = set(as_string_list(variant.get("conflicts")))
        auto_conflicts = expected_auto_conflicts(data, key, variant)
        if not manual_conflicts:
            continue
        if manual_conflicts <= auto_conflicts:
            if _remove_variant_field_for_key(lines, key, "conflicts"):
                fixes.append(f"conflicts:{key}")
        else:
            extra = sorted(manual_conflicts - auto_conflicts)
            if extra != sorted(manual_conflicts):
                if _replace_variant_conflicts(lines, key, extra):
                    fixes.append(f"conflicts:{key}")

    return fixes


def apply_safe_fixes(path: Path, base_ref: str | None = None) -> list[str]:
    rel = _manifest_rel(path)
    fixes: list[str] = []
    lines = path.read_text().splitlines(keepends=True)
    data = load_manifest(path)
    changed = False

    if _remove_pkgrel_fields(lines):
        changed = True
        fixes.append(
            f"Removed `pkgrel` from `{rel}` (`1` is added automatically in generated PKGBUILDs)"
        )

    if base_ref:
        from .git_changed import is_new_manifest

        if is_new_manifest(base_ref, path):
            pkgver_variants = _fix_new_package_pkgver(lines, data)
            if pkgver_variants:
                changed = True
                variant_list = ", ".join(f"`{key}`" for key in pkgver_variants)
                fixes.append(
                    f"Set `pkgver` to `0` in `{rel}` for variant(s) {variant_list} "
                    "(initial AUR push — bumped by the update action after merge)"
                )

    if changed:
        path.write_text("".join(lines))
        data = load_manifest(path)
        lines = path.read_text().splitlines(keepends=True)

    docs = data.get("docs")
    if docs is None:
        docs = {}

    pkgdesc = normalized_pkgdesc(str(data.get("pkgdesc", "")))
    if docs.get("description") and normalized_pkgdesc(str(docs["description"])) == pkgdesc:
        if _remove_line(lines, r"^  description:.*$"):
            changed = True
            fixes.append(f"Removed redundant `docs.description` from `{rel}`")

    if "docs" in data and not docs:
        if _remove_line(lines, r"^docs:\s*$"):
            changed = True
            fixes.append(f"Removed empty `docs` block from `{rel}`")

    external = docs.get("externalAur")
    if isinstance(external, list) and external != sorted(external):
        if _replace_external_aur(lines, sorted(external)):
            changed = True
            fixes.append(f"Sorted `docs.externalAur` in `{rel}`")

    hoisted = _hoist_duplicate_fields(lines, data)
    if hoisted:
        changed = True
        for field in hoisted:
            fixes.append(f"Hoisted `{field}` to the top level in `{rel}`")

    relation_fixes = _fix_redundant_variant_relations(lines, data)
    if relation_fixes:
        changed = True
        for item in relation_fixes:
            if item.startswith("provides:"):
                variant = item.split(":", 1)[1]
                fixes.append(
                    f"Removed redundant `provides` from variant `{variant}` in `{rel}` "
                    "(injected automatically at PKGBUILD generation)"
                )
            elif item.startswith("conflicts:"):
                variant = item.split(":", 1)[1]
                fixes.append(
                    f"Removed redundant `conflicts` from variant `{variant}` in `{rel}` "
                    "(injected automatically at PKGBUILD generation)"
                )
            elif item == "provides":
                fixes.append(
                    f"Removed redundant top-level `provides` from `{rel}` "
                    "(injected automatically at PKGBUILD generation)"
                )

    if changed:
        path.write_text("".join(lines))
    return fixes
