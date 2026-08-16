from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"
README = REPO_ROOT / "README.md"

ICON_FILENAME = "icon.png"
ICON_SIZE = 64

BASE_VARIANT_KEYS = {"base", "stable", "release"}

REQUIRED_TOP_LEVEL = ("name", "url", "license", "variants")

HOISTABLE_VARIANT_FIELDS = {
    "arch",
    "depends",
    "makedepends",
    "optdepends",
    "provides",
    "conflicts",
    "replaces",
    "options",
    "backup",
    "groups",
    "pkgdesc",
    "versionChecker",
    "pkgver",
}

VARIANT_ONLY_FIELDS = {
    "source",
    "sha256sums",
    "prepare",
    "build",
    "package",
    "pkgver_func",
}


def find_manifests() -> list[Path]:
    return sorted(PACKAGES_DIR.glob("*/manifest.yaml"))


def pkgname(name: str, variant_key: str) -> str:
    if variant_key in BASE_VARIANT_KEYS:
        return name
    return f"{name}-{variant_key}"


def icon_path(app_dir: Path) -> Path:
    return app_dir / ICON_FILENAME
