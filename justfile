default:
    just --list

# lint monorepo
[group('precommit')]
lint:
    uv tool run ruff@0.8.0 check --fix .

# format monorepo
[group('precommit')]
format:
    uv tool run ruff@0.8.0 format .

# run test in local package
[group('precommit')]
pytest:
    uv sync --directory {{invocation_directory()}} --group dev
    uv run --directory {{invocation_directory()}} pytest tests

# check license
[group('precommit')]
check-license:
    uv run reuse lint

# insert license for contributor
insert-license:
    # https://reuse.readthedocs.io/en/stable/scripts.html#add-headers-to-staged-files-based-on-git-settings
    git diff --name-only --cached | xargs -I {} reuse annotate -c "$(git config --get user.name) <$(git config --get user.email)>" "{}"

# run precommit before PR
[group('precommit')]
precommit: lint format pytest check-licence