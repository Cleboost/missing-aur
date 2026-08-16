import subprocess
import sys
from pathlib import Path

from .paths import PACKAGES_DIR, REPO_ROOT


def changed_apps(base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    apps: set[str] = set()
    for line in result.stdout.splitlines():
        parts = Path(line).parts
        if len(parts) >= 2 and parts[0] == "packages":
            apps.add(parts[1])
    return sorted(apps)


def manifest_paths(apps: list[str] | None = None) -> list[Path]:
    if not apps:
        return sorted(PACKAGES_DIR.glob("*/manifest.yaml"))
    paths = []
    for app in apps:
        manifest = PACKAGES_DIR / app / "manifest.yaml"
        if manifest.is_file():
            paths.append(manifest)
    return paths


def is_new_manifest(base_ref: str, path: Path) -> bool:
    rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{base_ref}:{rel}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode != 0
