"""Auto provides/conflicts for interchangeable package variants."""

from __future__ import annotations

from pathlib import Path

import yaml

from .paths import BASE_VARIANT_KEYS

_MANIFEST_RESERVED = frozenset({"docs", "providesBase"})


def as_string_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def variant_pkgname(name: str | None, variant_key: str) -> str | None:
    if not name:
        return None
    if variant_key in BASE_VARIANT_KEYS:
        return name
    return f"{name}-{variant_key}"


def provides_base_enabled(data: dict) -> bool:
    return data.get("providesBase", True) is not False


def external_aur_packages(data: dict) -> list[str]:
    docs = data.get("docs") or {}
    external = docs.get("externalAur") or []
    return sorted(set(as_string_list(external)))


def auto_provides(name: str, pkg: dict) -> list[str]:
    provides = list(as_string_list(pkg.get("provides")))
    if name not in provides:
        provides.insert(0, name)
    return provides


def auto_conflicts(
    name: str,
    pkgname: str,
    all_pkgnames: list[str],
    external_aur: list[str],
) -> list[str]:
    conflicts = {name, *all_pkgnames, *external_aur}
    conflicts.discard(pkgname)
    return sorted(conflicts)


def apply_variant_relations(
    pkg: dict,
    *,
    name: str,
    all_pkgnames: list[str],
    external_aur: list[str],
) -> dict:
    pkg = dict(pkg)
    pkgname = pkg["pkgname"]
    pkg["provides"] = auto_provides(name, pkg)
    manual_conflicts = set(as_string_list(pkg.get("conflicts")))
    pkg["conflicts"] = sorted(
        manual_conflicts | set(auto_conflicts(name, pkgname, all_pkgnames, external_aur))
    )
    return pkg


def load_packages(manifest_path: Path) -> list[tuple[str | None, dict]]:
    """Return (variant_key, resolved_pkg_dict) for each package in the manifest."""
    data = yaml.safe_load(manifest_path.read_text()) or {}
    provides_base = provides_base_enabled(data)
    external_aur = external_aur_packages(data)

    name = data.get("name")
    variants = data.get("variants")
    shared = {key: value for key, value in data.items() if key not in _MANIFEST_RESERVED | {"name", "variants"}}

    if not variants:
        return [(None, shared)]

    raw: list[tuple[str, dict]] = []
    for key, variant in variants.items():
        pkg = {**shared, **(variant or {})}
        pkg.setdefault("pkgname", variant_pkgname(name, key))
        if not pkg.get("pkgname"):
            raise ValueError(f"{manifest_path}: variant {key!r} has no pkgname (set `name:` or `pkgname:`)")
        raw.append((key, pkg))

    if not provides_base or not name:
        return raw

    all_pkgnames = [pkg["pkgname"] for _, pkg in raw]
    return [
        (key, apply_variant_relations(pkg, name=name, all_pkgnames=all_pkgnames, external_aur=external_aur))
        for key, pkg in raw
    ]


def expected_auto_conflicts(
    data: dict,
    variant_key: str,
    variant: dict,
) -> set[str]:
    name = data.get("name")
    if not name or not provides_base_enabled(data):
        return set()

    variants = data.get("variants") or {}
    all_pkgnames = [
        variant_pkgname(name, key)
        for key in variants
        if variant_pkgname(name, key)
    ]
    pkgname = variant_pkgname(name, variant_key)
    if not pkgname:
        return set()
    return set(auto_conflicts(name, pkgname, all_pkgnames, external_aur_packages(data)))


def redundant_provides_value(data: dict, value) -> bool:
    name = data.get("name")
    if not name or not provides_base_enabled(data):
        return False
    return set(as_string_list(value)) == {name}
