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

# we follow angular convention:
# https://github.com/angular/angular/blob/22b96b9/CONTRIBUTING.md#type
VALID_TYPES = {
    "revert",  # Revert a previous commit
    "build",  # Changes that affect build system or dependencies
    "ci",  # Changes to CI configuration files and scripts
    "docs",  # Documentation only changes
    "feat",  # A new feature
    "fix",  # A bug fix
    "perf",  # Performance improvements
    "refactor",  # Code changes that neither fix bugs nor add features
    "style",  # Code style changes (formatting, etc)
    "test",  # Adding or fixing tests
}

# this helps user debug messages
# see: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions#adding-a-job-summary
MARKDOWN_SUMMARY = string.Template(
    """
### Result

| PR title | expected format | status | message |
|---|---|---|---|
| `${title}` | `<type>(<scope>): <subject>` | `${status}` | `${message}` |


### Useful Links
- how to write a good PR. link coming!
- [why we do `check-pr-title`](https://github.com/MiroMindAsia/OpenDeepResearch-GAIA/blob/main/docs/contribute.md#why-use-check-pr-title-error)
- [how to fix `check-pr-title` error](https://github.com/MiroMindAsia/OpenDeepResearch-GAIA/blob/main/docs/contribute.md#how-to-fix-check-pr-title-error)
"""
)


@dataclasses.dataclass
class CheckResult:
    title: str
    status: bool
    message: str

    def to_markdown(self) -> str:
        emoji = "PASSED ✅" if self.status else "FAILED ❌"
        return MARKDOWN_SUMMARY.substitute(
            title=self.title,
            status=emoji,
            message=self.message,
        ).strip()


def check_pr_title(title: str) -> CheckResult:
    """
    Validate if PR title follows the format: <type>(<scope>): <subject>
    """
    # Split patterns for detailed error checking
    type_pattern = rf"^({'|'.join(sorted(VALID_TYPES))})"
    scope_pattern = r"\([a-z0-9-]+\)"
    subject_pattern = r": .+"

    # Check type
    type_match = re.match(type_pattern, title)
    if not type_match:
        return CheckResult(
            title=title,
            status=False,
            message="<type> must be one of: " + ", ".join(sorted(VALID_TYPES)),
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

    return CheckResult(
        title=title,
        status=True,
        message="Valid PR title format",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate PR title following Angular commit convention"
    )
    parser.add_argument(
        "title",
        type=str,
        help="PR title to validate (format: <type>(<scope>): <subject>)",
    )

    args = parser.parse_args()
    result = check_pr_title(args.title)

    step_summary_path = os.environ.get("GITHUB_STEP_SUMMARY", None)
    # print(f"GITHUB_STEP_SUMMARY: {step_summary_path}")
    # print("github step summary is:", result.to_markdown())
    if step_summary_path is not None:
        with open(step_summary_path, "a") as f:
            f.write(result.to_markdown())

    if not result.status:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
