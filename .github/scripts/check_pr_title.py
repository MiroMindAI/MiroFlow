# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
import argparse
import dataclasses
import os
import re
import string
import sys

VALID_TYPES = {
    "revert",
    "build",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "style",
    "test",
}

MARKDOWN_TEMPLATE = string.Template(
    """### Result

| PR title | expected format | status | message |
|---|---|---|---|
| `${title}` | `<type>(<scope>): <subject>` | `${status}` | `${message}` |
"""
)


@dataclasses.dataclass
class CheckResult:
    title: str
    status: bool
    message: str

    def to_markdown(self) -> str:
        emoji = "PASSED ✅" if self.status else "FAILED ❌"
        return MARKDOWN_TEMPLATE.substitute(
            title=self.title, status=emoji, message=self.message
        ).strip()


def check_pr_title(title: str) -> CheckResult:
    """Validate PR title follows format: <type>(<scope>): <subject>"""
    type_pattern = rf"^({'|'.join(sorted(VALID_TYPES))})"
    scope_pattern = r"\([a-z0-9-]+\)"
    subject_pattern = r": .+"

    # Check type
    type_match = re.match(type_pattern, title)
    if not type_match:
        return CheckResult(
            title=title,
            status=False,
            message=f"<type> must be one of: {', '.join(sorted(VALID_TYPES))}",
        )

    remaining = title[type_match.end() :]

    # Check scope (optional)
    if remaining.startswith("("):
        scope_match = re.match(scope_pattern, remaining)
        if not scope_match:
            return CheckResult(
                title=title,
                status=False,
                message="<scope> must contain only lowercase letters, numbers, or hyphens",
            )
        remaining = remaining[scope_match.end() :]

    # Check subject
    if not re.match(subject_pattern, remaining):
        return CheckResult(
            title=title,
            status=False,
            message="<subject> must start with ': ' and contain a description",
        )

    return CheckResult(title=title, status=True, message="Valid PR title format")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate PR title following Angular commit convention"
    )
    parser.add_argument(
        "title", help="PR title to validate (format: <type>(<scope>): <subject>)"
    )

    args = parser.parse_args()
    result = check_pr_title(args.title)

    print(result)

    # Write to GitHub step summary if available
    if step_summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(step_summary, "a") as f:
            f.write(result.to_markdown())

    sys.exit(0 if result.status else 1)


if __name__ == "__main__":
    main()
