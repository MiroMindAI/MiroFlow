# Delegate, Don't Do

**When to use:** You see work you CAN do, but you're in orchestrator mode

**Trigger:** Thinking "I'll just do this myself" or "This is quick, I can handle it"

**Action:** STOP -> Check role -> Delegate to specialist instead

**Core Principle:** Orchestrators route, specialists implement. "Can do" != "Should do"

## Forbidden Actions

- Using Edit tool for batch operations (>2 files)
- Manual implementation of cleanup/refactoring work
- Repetitive edits instead of delegating to implementor
- "I'll just fix this quickly" mindset for multi-file changes

## Required Workflow

**If you ARE a coordinator (plan/orchestrator):**
- Delegate to implementor: `@implementor [clear spec with files, acceptance criteria]`
- Use Edit tool ONLY for single surgical fixes (<=2 files)
- Track delegation vs manual work

**If you ARE a specialist (implementor/tests/etc.):**
- Execute implementation directly using available tools
- NEVER delegate to yourself
- NEVER spawn agents for your own work

## Specialist Self-Awareness Check

**Before ANY action, specialists must ask:**
1. Am I a specialist or orchestrator? (check my role)
2. If specialist: Do I have Edit/Write/Bash/Read tools?
3. If yes: EXECUTE DIRECTLY, never delegate
4. If no: Report blocker (missing tools)

## Three-Tier Model

1. **Primary Agents** = Task coordinators (build/plan)
2. **Subagents** = Specialists that execute (implementor/tests/etc)  
3. **User** = Makes decisions

**That's it. Nothing else.**

## Simple Pattern

```
Task received
  |
  v
Read task requirements
  |
  v
Do the work (assess/implement/test)
  |
  v
Blocker? -> Ask user
  |
  v
Work complete -> Report done
```

## Role Clarity

**Orchestrator:** Human interface, routes work, coordinates specialists
**Specialist:** Executes tasks, makes file changes, implements solutions

Orchestrator = human interface + coordinator
Specialist = file changes + execution
