#!/usr/bin/env python3
"""Run PR checks and write a markdown report for the pull request comment."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.git_changed import changed_apps, manifest_paths
from lib.issues import Issue, format_pr_report, is_blocking
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
    manifest_commit: str,
    readme_commit: str,
) -> list[str]:
    fixes: list[str] = []

    icon_files = commit_files(icon_commit)
    if icon_files:
        paths = ", ".join(f"`{path}`" for path in icon_files)
        fixes.append(f"Resized package icons to 32×32: {paths}")

    manifest_files = commit_files(manifest_commit)
    if manifest_files:
        paths = ", ".join(f"`{path}`" for path in manifest_files)
        fixes.append(
            "Optimized manifests "
            "(hoisted shared variant fields, removed empty `docs`, redundant `docs.description`, "
            "sorted `externalAur`): "
            f"{paths}"
        )

    readme_files = commit_files(readme_commit)
    if readme_files:
        paths = ", ".join(f"`{path}`" for path in readme_files)
        fixes.append(f"Regenerated README package table: {paths}")

    return fixes


def collect_issues(apps: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for path in manifest_paths(apps):
        issues.extend(check_manifest(path))
        issues.extend(check_icon(path.parent))
    issues.extend(run_generate_readme_check())
    return issues


def main() -> None:
    ap = argparse.ArgumentParser(description="Run PR checks and write report")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--output", default="pr-report.md")
    ap.add_argument("--icon-commit", default="", help="Commit SHA for icon auto-fix")
    ap.add_argument("--manifest-commit", default="", help="Commit SHA for manifest auto-fix")
    ap.add_argument("--readme-commit", default="", help="Commit SHA for README auto-fix")
    args = ap.parse_args()

    apps = changed_apps(args.base)
    if not apps:
        report = "## Package check recap\n\nNo changes under `packages/` — skipped package checks."
        Path(args.output).write_text(report)
        print(report)
        return

    auto_fixes = describe_auto_fixes(
        args.icon_commit,
        args.manifest_commit,
        args.readme_commit,
    )
    issues = collect_issues(apps)
    blocking = [issue for issue in issues if is_blocking(issue)]
    suggestions = [issue for issue in issues if not is_blocking(issue)]

    report = format_pr_report(apps, auto_fixes, blocking, suggestions)
    Path(args.output).write_text(report)
    print(report)

    if blocking:
        sys.exit(1)


if __name__ == "__main__":
    main()
