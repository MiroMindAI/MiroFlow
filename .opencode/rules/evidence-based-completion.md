# Evidence-Based Todo Completion

## Core Principle

**"Unknown" is more honest than "completed" when evidence is missing.**

Never mark work "completed" without verifiable evidence.

## The Anti-Pattern

**Wrong Completion:**
1. Attempt task (run command, make change)
2. No clear success/failure signal
3. Mark as "completed" anyway (optimistic assumption)
4. Move on without verification
5. User discovers work incomplete

**Correct Completion:**
1. Attempt task
2. Check for evidence of success
3. If evidence exists -> mark "completed"
4. If confirmed failure -> mark "failed" with reason
5. If uncertain -> mark "unknown" and create verification task

## Evidence Requirements

### Before Marking "Completed"

**Checklist:**
- [ ] Can I see the result? (file exists, output visible)
- [ ] Can I prove it worked? (test pass, command output)
- [ ] Would another agent see this work? (persistent, visible)
- [ ] Can the user act on this? (file accessible, PR created)

**If ANY checkbox fails -> Do NOT mark "completed"**

### Evidence Types

**Filesystem Evidence:**
```bash
# File was created
ls -l path/to/file
```

**Test Evidence:**
```bash
# Tests pass
pytest tests/ -v
```

**Git Evidence:**
```bash
# Commit was made
git log --oneline -1
```

## Task States

### Standard States

- **completed** - Evidence of success exists
- **in_progress** - Work is actively happening
- **pending** - Not yet started

### Extended States (For Uncertain Outcomes)

- **blocked** - Cannot proceed, documented blocker
- **failed** - Attempted, confirmed failure, documented
- **unknown** - Attempted, no evidence either way, needs verification

## Verification Protocol

### When Verification Fails

1. **Document uncertainty:**
```markdown
Status: unknown
Reason: Command returned no output
Attempted: [what was tried]
Follow-up: [how to verify]
```

2. **Create verification task**
3. **Investigate systematically**
4. **Update status with findings**

## Success Criteria

**This protocol is working when:**
- Todo list reflects reality (no false completions)
- User can trust todo status (completed = actually done)
- Blockers are visible (not hidden as "completed")
- Failures are documented (not optimistically completed)
- Uncertainty is acknowledged (unknown state used)
