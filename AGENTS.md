# MiroFlow Project Agents

This document describes the AI agent configuration for the MiroFlow project.

## Project Overview

MiroFlow is a Python project for Miro board automation and workflows. The codebase uses:
- Python 3.x with uv for package management
- Source code in `src/` directory
- Configuration in `config/` directory
- Utility modules in `utils/` directory

## Agent Architecture

### Primary Agents

| Agent | Mode | Purpose |
|-------|------|---------|
| **build** | Primary | Full development with all tools. Default for implementation work. |
| **plan** | Primary | Analysis and planning without code changes. Read-only. |

### Specialist Subagents

| Agent | Purpose | Tools |
|-------|---------|-------|
| **@oracle** | Technical advisor for architecture decisions and strategic guidance | Read-only |
| **@implementor** | End-to-end feature implementation with TDD | Full access |
| **@tests** | Test strategy, generation, and repair | Full access |
| **@debug** | Bug investigation and root cause analysis | Read + Bash |
| **@refactor** | Staged code refactoring with verification | Full access |
| **@git-ops** | Git operations, commits, PRs | Git/GH only |
| **@code-review** | Code review and quality validation | Read-only |
| **@security-audit** | Security vulnerability assessment | Read-only |
| **@document-writer** | Technical documentation | Write docs only |
| **@pixel-perfect** | Visual QA comparing UI with Figma designs | Read + Figma MCP |

## Behavioral Protocols

Located in `.opencode/rules/`:

### Core Protocols

1. **delegate-dont-do.md** - Orchestrators route, specialists implement
2. **investigate-before-commit.md** - Gather evidence before decisions
3. **evidence-based-completion.md** - Only mark complete with evidence
4. **error-investigation-protocol.md** - Investigate errors before panicking
5. **task-breakdown.md** - Structure tasks as Discovery -> Implementation -> Verification
6. **routing-decision-matrix.md** - Route to appropriate specialists

## Task Breakdown Structure

All complex tasks should follow:

```
<task_breakdown>
1. [Discovery] Understand scope, dependencies, risks
2. [Implementation] Make changes in order with rollback points
3. [Verification] Validate against success criteria
</task_breakdown>
```

## Success Criteria Format

```
## Success Criteria
- All tests pass
- No hardcoded values
- Code follows existing patterns

## Never Do
- Skip test verification
- Commit secrets
- Leave TODO comments
```

## Project-Specific Notes

### Python Conventions
- Use type hints for function signatures
- Follow existing patterns in codebase
- Run tests with `pytest`
- Format code with existing formatter

### File Structure
```
MiroFlow/
├── src/           # Source code
├── config/        # Configuration files
├── utils/         # Utility modules
├── scripts/       # Helper scripts
├── data/          # Data files
├── logs/          # Log files
└── tests/         # Test files (if present)
```

### Commands
```bash
# Run the main application
python main.py

# Install dependencies
uv pip install -r requirements.txt

# Run tests (if configured)
pytest
```

## Configuration

Agent configuration is in:
- `opencode.json` - Main config with agent definitions
- `.opencode/agents/` - Detailed agent prompts
- `.opencode/rules/` - Behavioral protocols
