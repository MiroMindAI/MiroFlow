# Error Investigation Protocol

**When to use:** Agent tool shows error but unclear if real failure

**Trigger:** Seeing "unreachable" / "failed" / "error" messages

**Action:** INVESTIGATE -> VERIFY -> DECIDE (never panic and bypass)

## The Anti-Pattern (NEVER DO THIS)

```
See error message
  |
  v
Assume system is broken
  |
  v
Try to do work directly
  |
  v
Create redundant sessions
  |
  v
Bypass delegation
  |
  v
Create chaos and lose work
```

## The Correct Pattern (ALWAYS DO THIS)

```
See error message
  |
  v
INVESTIGATE with monitoring tools
  |
  v
Check actual system state
  |
  v
Verify agent/process is running
  |
  v
Trust delegation if state is healthy
  |
  v
Wait with patience
  |
  v
Check results when complete
```

## Investigation Toolkit

### When Tools Show Errors

1. **Check connectivity** - Can other tools work?
2. **Check process** - Is the operation actually running?
3. **Check output** - Are there results despite the error?
4. **Check logs** - What do logs say?

### Decision Tree

```
Error message appears
    |
    v
Check if operation succeeded anyway
    |
    +-- Works -> Ignore error message, trust results
    |
    +-- Fails -> Investigate further
            |
            v
        Check process/service status
            |
            +-- Running -> Wait, operation in progress
            |
            +-- Not running -> Real failure, report blocker
```

## Trust But Verify Protocol

### Trust
- Agent sessions continue running even when view shows errors
- Tools execute tasks even when CLI shows errors
- System is more robust than display suggests

### Verify
- Use monitoring tools to check actual state
- Check process list to confirm execution
- Wait for completion before assuming failure

### Never
- Bypass delegation due to display bugs
- Create redundant sessions without investigating
- Attempt direct execution when agents are working
- Panic and lose uncommitted work

## Common Display Bugs vs Real Failures

### Display Bug Symptoms
- Error shown but operation succeeded
- "unreachable" but results are there
- Timeout but work completed

### Real Failure Symptoms
- No output or results
- Process not running
- Consistent errors across multiple checks

## Monitoring Best Practices

### Patience Over Polling

**Wrong:**
```bash
while true; do
  check_status
  sleep 1  # Polling every second
done
```

**Correct:**
```bash
check_status
sleep 30  # Be patient
check_status
```

### Progressive Intervals

First check: Immediate
Second check: 30 seconds later
Third check: 60 seconds later
Ongoing: 60-120 second intervals

**Why:** Reduce system load, avoid spam, respect execution time
