#!/usr/bin/env python3
"""Run PR checks and write a markdown report for the pull request comment."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.git_changed import changed_apps, manifest_paths
from lib.issues import Issue, format_pr_report, is_blocking
from lib.paths import ICON_SIZE
from fix_icon import check_icon
from lint_manifest import check_manifest


def run_generate_readme_check() -> list[Issue]:
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "generate-readme.py"), "check"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return []
    return [
        Issue(
            "README.md",
            "readme-out-of-date",
            "README package table is still out of date after auto-fix.",
            fixable=False,
        )
    ]


def commit_files(commit_sha: str) -> list[str]:
    if not commit_sha:
        return []
    result = subprocess.run(
        ["git", "show", "--name-only", "--pretty=format:", commit_sha],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def describe_auto_fixes(
    icon_commit: str,
    manifest_fixes: list[str],
    readme_commit: str,
) -> list[str]:
    fixes: list[str] = []

    icon_files = commit_files(icon_commit)
    if icon_files:
        paths = ", ".join(f"`{path}`" for path in icon_files)
        fixes.append(f"Resized package icons to {ICON_SIZE}×{ICON_SIZE}: {paths}")

    fixes.extend(manifest_fixes)

    readme_files = commit_files(readme_commit)
    if readme_files:
        paths = ", ".join(f"`{path}`" for path in readme_files)
        fixes.append(f"Regenerated README package table: {paths}")

    return fixes


def load_manifest_fixes(path: str) -> list[str]:
    if not path:
        return []
    report = Path(path)
    if not report.is_file():
        return []
    data = json.loads(report.read_text())
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def collect_issues(apps: list[str], base_ref: str) -> list[Issue]:
    issues: list[Issue] = []
    for path in manifest_paths(apps):
        issues.extend(check_manifest(path, base_ref=base_ref))
        issues.extend(check_icon(path.parent))
    issues.extend(run_generate_readme_check())
    return issues


def write_report(path: str, report: str) -> None:
    Path(path).write_text(report)
    print(report)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run PR checks and write report")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--output", default="pr-report.md")
    ap.add_argument(
        "--apps",
        nargs="*",
        default=None,
        help="Package app names to check (skips git diff detection)",
    )
    ap.add_argument("--icon-commit", default="", help="Commit SHA for icon auto-fix")
    ap.add_argument("--manifest-fixes", default="", help="JSON report from lint_manifest.py fix")
    ap.add_argument("--readme-commit", default="", help="Commit SHA for README auto-fix")
    args = ap.parse_args()

    try:
        apps = args.apps if args.apps is not None else changed_apps(args.base)
    except RuntimeError as exc:
        report = (
            "## Package check recap\n\n"
            f"Could not detect changed packages: {exc}\n\n"
            "See the workflow logs for details."
        )
        write_report(args.output, report)
        sys.exit(1)

    if not apps:
        report = "## Package check recap\n\nNo changes under `packages/` — skipped package checks."
        write_report(args.output, report)
        return

    auto_fixes = describe_auto_fixes(
        args.icon_commit,
        load_manifest_fixes(args.manifest_fixes),
        args.readme_commit,
    )
    issues = collect_issues(apps, args.base)
    blocking = [issue for issue in issues if is_blocking(issue)]
    suggestions = [issue for issue in issues if not is_blocking(issue)]

    report = format_pr_report(apps, auto_fixes, blocking, suggestions)
    write_report(args.output, report)

    if blocking:
        sys.exit(1)


if __name__ == "__main__":
    main()
