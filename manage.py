#!/usr/bin/env python3
"""missing-aur — generates PKGBUILDs from simple YAML manifests.

A manifest declares a `name` (the app) and one or more `variants`. The variant
key is appended to the name to form the pkgname (psst + bin -> psst-bin).
Fields declared at the top level are shared by all variants; a variant can
override any of them. There is no template magic: YAML keys map 1:1 to PKGBUILD
fields, and the build functions are written as plain bash.
"""

import sys
import re
import os
import subprocess
import shutil
import argparse
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pacman -S python-yaml", file=sys.stderr)
    sys.exit(1)

MAINTAINER  = "Cleboost <clement.balarot@gmail.com>"
CONTRIBUTOR = "missing-aur project <https://github.com/Cleboost/missing-aur>"
PACKAGES_DIR = Path("packages")

# Suffix automatically appended to pkgdesc based on the pkgname ending.
DESC_SUFFIX = {
    "-bin":      "(precompiled binary)",
    "-git":      "(git version)",
    "-appimage": "(AppImage)",
}


# ── Manifest loading ──────────────────────────────────────────────────────────

def load_packages(manifest_path: Path) -> list[tuple[str | None, dict]]:
    """Return (variant_key, resolved_pkg_dict) for each package in the manifest."""
    data     = yaml.safe_load(manifest_path.read_text())
    name     = data.pop("name", None)
    variants = data.pop("variants", None)
    shared   = data

    if not variants:
        # Flat single-package manifest (pkgname must be set explicitly).
        return [(None, shared)]

    packages = []
    for key, variant in variants.items():
        pkg = {**shared, **(variant or {})}
        pkg.setdefault("pkgname", f"{name}-{key}" if name else None)
        if not pkg.get("pkgname"):
            raise ValueError(f"{manifest_path}: variant {key!r} has no pkgname (set `name:` or `pkgname:`)")
        packages.append((key, pkg))
    return packages


def find_manifests() -> list[Path]:
    return sorted(PACKAGES_DIR.glob("*/manifest.yaml"))


# ── PKGBUILD generation ───────────────────────────────────────────────────────

SCALAR_UNQUOTED = ["pkgname", "pkgver", "pkgrel", "epoch"]
SCALAR_QUOTED   = ["pkgdesc", "url"]
ARRAY_FIELDS    = [
    "arch", "depends", "makedepends", "optdepends",
    "provides", "conflicts", "replaces", "options", "backup", "groups",
]


def _fmt_array(values) -> str:
    if isinstance(values, str):
        values = [values]
    return "(" + " ".join(f'"{v}"' for v in values) + ")"


def _write_func(body, name: str) -> str:
    lines = body.strip().splitlines() if isinstance(body, str) else [l for l in body if l is not None]
    result = []
    for line in lines:
        # Heredoc terminators must not be indented
        if line.strip() in ("EOF", "'EOF'", '"EOF"'):
            result.append(line.strip())
        else:
            result.append(f"  {line}")
    return f"{name}() {{\n" + "\n".join(result) + "\n}\n"


def _inject_desc_suffix(pkg: dict) -> None:
    desc = pkg.get("pkgdesc", "")
    if not desc or desc.endswith(")"):
        return
    pkgname = pkg.get("pkgname", "")
    for ending, suffix in DESC_SUFFIX.items():
        if pkgname.endswith(ending):
            pkg["pkgdesc"] = f"{desc} {suffix}"
            return


def generate_pkgbuild(pkg: dict, output_dir: Path) -> None:
    pkg = dict(pkg)
    _inject_desc_suffix(pkg)
    pkg.setdefault("pkgrel", 1)
    pkg.setdefault("pkgver", "0")
    pkg.setdefault("arch", ["x86_64"])

    lines = [
        f"# Maintainer: {MAINTAINER}",
        f"# Contributor: {CONTRIBUTOR}",
        "",
    ]

    for f in SCALAR_UNQUOTED:
        if (v := pkg.get(f)) is not None:
            lines.append(f"{f}={v}")
    for f in SCALAR_QUOTED:
        if v := pkg.get(f):
            lines.append(f'{f}="{v}"')
    for f in ARRAY_FIELDS:
        if v := pkg.get(f):
            lines.append(f"{f}={_fmt_array(v)}")
    if lic := pkg.get("license"):
        lines.append(f"license={_fmt_array(lic)}")

    lines.append("")

    src = pkg.get("source")
    if isinstance(src, dict):  # per-arch sources
        for arch, srcs in src.items():
            lines.append(f"source_{arch}={_fmt_array(srcs)}")
        for arch, srcs in src.items():
            sums = pkg.get("sha256sums", {}).get(arch, ["SKIP"] * len(srcs))
            lines.append(f"sha256sums_{arch}={_fmt_array(sums)}")
    elif isinstance(src, list):
        lines.append(f"source={_fmt_array(src)}")
        sums = pkg.get("sha256sums", ["SKIP"] * len(src))
        lines.append(f"sha256sums={_fmt_array(sums)}")

    lines.append("")

    for func_name, key in [
        ("pkgver",  "pkgver_func"),
        ("prepare", "prepare"),
        ("build",   "build"),
        ("package", "package"),
    ]:
        if body := pkg.get(key):
            lines.append(_write_func(body, func_name))

    (output_dir / "PKGBUILD").write_text("\n".join(lines) + "\n")


# ── Version checking & update ─────────────────────────────────────────────────

def check_version(pkg: dict, cwd: Path) -> str | None:
    checker = pkg.get("versionChecker")
    if not checker:
        return None
    result = subprocess.run(checker, shell=True, capture_output=True, text=True, cwd=cwd)
    ver = result.stdout.strip()
    return ver if ver and ver != str(pkg.get("pkgver", "")) else None


def update_manifest_version(manifest_path: Path, variant_key: str | None, new_ver: str) -> None:
    if variant_key is None:
        content = manifest_path.read_text()
        content = re.sub(r"^(pkgver:\s*).*$", f"\\g<1>{new_ver}", content, flags=re.MULTILINE)
        content = re.sub(r"^(pkgrel:\s*).*$", "\\g<1>1", content, flags=re.MULTILINE)
        manifest_path.write_text(content)
    else:
        data = yaml.safe_load(manifest_path.read_text())
        data["variants"][variant_key]["pkgver"] = new_ver
        data["variants"][variant_key]["pkgrel"] = 1
        manifest_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        )


# ── Processing ────────────────────────────────────────────────────────────────

def process_package(manifest_path: Path, variant_key: str | None, pkg: dict, force: bool) -> dict | None:
    app_dir = manifest_path.parent
    pkgname = pkg["pkgname"]
    out_dir = app_dir / pkgname
    out_dir.mkdir(exist_ok=True)

    new_ver = check_version(pkg, app_dir)
    changed = force or new_ver is not None or not (out_dir / "PKGBUILD").exists()

    if new_ver:
        print(f"  {pkgname}: {pkg.get('pkgver')} → {new_ver}")
        pkg = {**pkg, "pkgver": new_ver, "pkgrel": 1}
        update_manifest_version(manifest_path, variant_key, new_ver)
    elif not changed:
        print(f"  {pkgname}: up to date ({pkg.get('pkgver', 'N/A')})")
        return None

    print(f"  {pkgname}: generating PKGBUILD...")
    generate_pkgbuild(pkg, out_dir)

    # Copy local assets (everything in the app dir except the manifest).
    for asset in app_dir.iterdir():
        if asset.is_file() and asset.name != "manifest.yaml":
            shutil.copy2(asset, out_dir / asset.name)

    if shutil.which("updpkgsums"):
        subprocess.run(["updpkgsums"], cwd=out_dir, check=False)
    else:
        print("  Warning: updpkgsums not found, skipping checksum update.")

    if shutil.which("makepkg"):
        with open(out_dir / ".SRCINFO", "w") as f:
            subprocess.run(["makepkg", "--printsrcinfo"], cwd=out_dir, stdout=f, check=False)
    else:
        print("  Warning: makepkg not found, skipping .SRCINFO generation.")

    return {"dir": str(out_dir), "pkgname": pkgname, "pkgver": str(pkg.get("pkgver", ""))}


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_generate(args):
    path = Path(args.path)
    manifest = path / "manifest.yaml"
    filter_pkg = None
    if not manifest.exists():               # a variant dir was passed
        manifest = path.parent / "manifest.yaml"
        filter_pkg = path.name
    if not manifest.exists():
        print(f"No manifest.yaml found from {args.path}", file=sys.stderr)
        sys.exit(1)

    for key, pkg in load_packages(manifest):
        if filter_pkg and pkg["pkgname"] != filter_pkg:
            continue
        process_package(manifest, key, pkg, force=True)


def cmd_generate_all(args):
    for manifest in find_manifests():
        print(f"[{manifest.parent.name}]")
        for key, pkg in load_packages(manifest):
            process_package(manifest, key, pkg, force=args.force)


def cmd_check_updates(args):
    updated = []
    for manifest in find_manifests():
        for key, pkg in load_packages(manifest):
            if result := process_package(manifest, key, pkg, force=False):
                updated.append(result)

    if args.ci:
        out_json = json.dumps(updated)
        print(f"packages={out_json}")
        if gh_out := os.environ.get("GITHUB_OUTPUT"):
            with open(gh_out, "a") as f:
                f.write(f"packages={out_json}\n")


def cmd_clean(args):
    for app_dir in PACKAGES_DIR.iterdir():
        if not app_dir.is_dir():
            continue
        for variant_dir in app_dir.iterdir():
            if variant_dir.is_dir():        # variant dirs are 100% generated
                shutil.rmtree(variant_dir)
    print("Cleaned.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap  = argparse.ArgumentParser(description="missing-aur package manager")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("generate", help="Generate PKGBUILD(s) for one app or variant")
    p.add_argument("path", help="App dir (packages/foo) or variant dir (packages/foo/foo-bin)")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("generate-all", help="Generate all PKGBUILDs")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_generate_all)

    p = sub.add_parser("check-updates", help="Check for new versions and regenerate")
    p.add_argument("--ci", action="store_true", help="Emit GitHub Actions output")
    p.set_defaults(func=cmd_check_updates)

    p = sub.add_parser("clean", help="Remove all generated files")
    p.set_defaults(func=cmd_clean)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
