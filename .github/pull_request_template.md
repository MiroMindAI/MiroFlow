# Describe this PR

<!-- Please provide a clear and concise description of what this PR does -->

## What changed?
<!-- Describe the changes made in this PR -->

## Why?
<!-- Explain the motivation behind these changes -->

## Related issues
<!-- Link any related issues using #issue_number -->


# Checklist for PR

- [ ] Write a descriptive PR title following the [Angular commit message format](https://github.com/angular/angular/blob/22b96b9/CONTRIBUTING.md#commit-message-format): `<type>(<scope>): <subject>`
  - **Examples:** `feat(agent): add pdf tool via mcp`, `perf: make llm client async`, `fix(utils): load custom config via importlib`
  - **Valid types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `revert`
  - The `check-pr-title` CI job will validate your title format
  - **Bad title examples and why they fail:**
    - `Update README` ❌ Missing type and colon
    - `feat add new feature` ❌ Missing colon after type
    - `Feature: add new tool` ❌ Invalid type (should be `feat`)
    - `feat(Agent): add tool` ❌ Scope should be lowercase
    - `feat(): add tool` ❌ Empty scope not allowed
    - `feat(my_scope): add tool` ❌ Underscores not allowed in scope
    - `feat(my space): add tool` ❌ Space not allowed in scope
    - `feat(scope):add tool` ❌ Missing space after colon
    - `feat(scope): ` ❌ Empty subject

- [ ] Run lint and format locally:
  - `uv tool run ruff@0.8.0 check --fix .`
  - `uv tool run ruff@0.8.0 format .`
  - CI job `lint` enforces ruff default format/lint rules on all new codes.