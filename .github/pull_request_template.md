# Describe this PR

# Checklist for PR
## Must Do
- [ ] Write a good PR title and description, i.e. `feat(agent): add pdf tool via mcp`, `perf: make llm client async` and `fix(utils): load custom config via importlib` etc. CI job `check-pr-title` enforces [Angular commit message format](https://github.com/angular/angular/blob/22b96b9/CONTRIBUTING.md#commit-message-format) to PR title.
- [ ] Run `make precommit` locally. CI job `lint` enforce ruff default format/lint rules on all new codes.
- [ ] Run `make pytest`. Check test summary (located at `report.html`) and coverage report (located at `htmlcov/index.html`) on new codes.

## Nice To Have

- [ ] (Optional) Write/update tests under `/tests` for `feat` and `test` PR.
- [ ] (Optional) Write/update docs under `/docs` for `docs` and `ci` PR.


