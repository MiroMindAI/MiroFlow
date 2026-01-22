# Routing Decision Matrix

Route work to appropriate specialists based on task type.

## Agent Invocation Architecture

### Tier Structure

**Tier 1: Primary Agents (coordinate)**
- build, plan
- Route work to specialists
- NEVER implement directly (unless <=2 files)

**Tier 2: Subagents (execute)**
- implementor, tests, debug, refactor, etc.
- Execute directly using tools
- NEVER delegate to other agents

## Decision Flowchart

```
User Intent Detected
  |
  +-- STRATEGIC/PLANNING? (ambiguous, high-risk)
  |   -> @oracle for analysis/advice
  |   -> Return: Architecture review, risks, decision
  |
  +-- IMPLEMENTATION? (code/feature/fix)
  |   -> @implementor for execution
  |   -> Return: Files modified, tests pass
  |
  +-- TESTING? (tests, QA, validation)
  |   -> @tests for test work
  |   -> Return: Test results, coverage
  |
  +-- GIT/GITHUB? (PR, issue, commit)
  |   -> @git-ops for git operations
  |   -> Return: GitHub ops complete
  |
  +-- DEBUGGING? (bug investigation)
  |   -> @debug for investigation
  |   -> Return: Root cause, fix recommendation
  |
  +-- DOCUMENTATION? (docs, README)
  |   -> @document-writer for docs
  |   -> Return: Documentation created
  |
  +-- SECURITY? (audit, vulnerabilities)
  |   -> @security-audit for review
  |   -> Return: Security findings
  |
  +-- CODE REVIEW? (PR review, quality)
  |   -> @code-review for review
  |   -> Return: Review feedback
  |
  +-- REFACTORING? (improve structure)
  |   -> @refactor for changes
  |   -> Return: Refactored code
  |
  +-- SIMPLE TASK? (quick question, small edit)
      -> Answer directly, no delegation needed
```

## Agent Selection Matrix

| Intent | Agent | Trigger Words | Output |
|--------|-------|---------------|--------|
| Strategy | oracle | "architecture", "risk", "should we" | Analysis, recommendation |
| Implementation | implementor | "build", "implement", "add feature" | Modified files, tests |
| Testing | tests | "test", "coverage", "verify" | Test results |
| Git | git-ops | "commit", "PR", "branch" | Git operations |
| Debug | debug | "bug", "failing", "investigate" | Root cause, fix |
| Docs | document-writer | "document", "README", "API docs" | Documentation |
| Security | security-audit | "security", "vulnerability", "audit" | Security report |
| Review | code-review | "review", "feedback", "quality" | Review feedback |
| Refactor | refactor | "refactor", "improve", "clean up" | Refactored code |

## Critical Rules

### Teaching Moments

When user teaches new pattern or corrects behavior:
- Document the learning
- Update relevant rules if needed
- Confirm understanding

### Role Clarity

I am: Primary agent (build/plan), coordinator
My job: Route, coordinate, synthesize
NOT my job: Implement directly (for complex tasks)

### When to Execute Directly

- Simple edits (<=2 files, <=50 lines)
- Obvious answers, no ambiguity
- User explicitly says "do it yourself"
- Setup/admin tasks

### When to Delegate

- Multi-file changes
- Complex tasks
- Specialist needed
- Quality/security matters
