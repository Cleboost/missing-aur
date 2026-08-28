"""Resolve pkgver for -git packages via makepkg and compare with the AUR."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def is_git_pkg(pkg: dict) -> bool:
    return bool(pkg.get("pkgver_func"))


def read_pkgbuild_pkgver(out_dir: Path) -> str | None:
    pkgbuild = out_dir / "PKGBUILD"
    if not pkgbuild.exists():
        return None
    match = re.search(r"^pkgver=(.+)$", pkgbuild.read_text(), re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def resolve_git_pkgver(out_dir: Path) -> str | None:
    """Fetch sources (if needed) and run pkgver() via makepkg --nobuild."""
    if subprocess.run(["makepkg", "--nobuild"], cwd=out_dir, check=False).returncode != 0:
        return None
    ver = read_pkgbuild_pkgver(out_dir)
    if not ver or ver == "0":
        return None
    return ver


def aur_pkgver(pkgname: str) -> str | None:
    result = subprocess.run(
        [
            "curl",
            "-sf",
            f"https://aur.archlinux.org/rpc?v=5&type=info&arg={pkgname}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    results = data.get("results") or []
    if not results:
        return None
    version = results[0].get("Version", "")
    return version.split("-")[0] if version else None
