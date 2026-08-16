from dataclasses import dataclass


@dataclass
class Issue:
    file: str
    rule: str
    message: str
    fixable: bool = False

    def format_line(self) -> str:
        return f"- **`{self.rule}`** (`{self.file}`): {self.message}"


def format_pr_report(
    apps: list[str],
    auto_fixes: list[str],
    blocking: list[Issue],
    suggestions: list[Issue],
) -> str:
    lines = ["## Package check recap", ""]

    if apps:
        joined = ", ".join(f"`{app}`" for app in apps)
        lines.append(f"Checked packages: {joined}")
        lines.append("")

    lines.append("### Auto-fixes committed")
    if auto_fixes:
        lines.extend(f"- {item}" for item in auto_fixes)
    else:
        lines.append("- Nothing needed automatic fixes.")
    lines.append("")

    if blocking:
        lines.append("### Blocking issues")
        lines.extend(issue.format_line() for issue in blocking)
        lines.append("")
        lines.append(
            "Please fix the items above and push again. "
            "Pull the latest branch commits first if auto-fixes were applied."
        )
        return "\n".join(lines)

    lines.append("### Status")
    lines.append("All checks passed. Nothing blocking.")

    if suggestions:
        lines.append("")
        lines.append("### Suggestions (optional)")
        lines.extend(issue.format_line() for issue in suggestions)
        lines.append("")
        lines.append("These are style optimizations — the PR can merge without them.")

    return "\n".join(lines)


def is_blocking(issue: Issue) -> bool:
    if issue.rule.startswith("missing-"):
        return True
    return issue.rule in {
        "parse-error",
        "name-mismatch",
        "invalid-variant",
        "icon-size",
        "readme-out-of-date",
        "missing-pillow",
    }
