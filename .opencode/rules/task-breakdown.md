# Task Breakdown Structure

Break complex tasks into trackable phases for clarity and progress monitoring.

## Standard Task Structure

```
<task_breakdown>
1. [Discovery] What to investigate
   - Identify affected components
   - Map dependencies
   - Document current state
   
2. [Implementation] What to change
   - Specific modifications
   - Order of operations
   - Rollback points
   
3. [Verification] What to validate
   - Success criteria
   - Test coverage
   - Performance metrics
</task_breakdown>
```

## Phase Definitions

### Discovery Phase
- Read relevant code and documentation
- Understand current behavior
- Identify dependencies and risks
- Document findings before proceeding

**Output:** Clear understanding of scope and impact

### Implementation Phase  
- Make changes in logical order
- Keep changes minimal and focused
- Create rollback points (commits)
- Run tests after each significant change

**Output:** Code changes that pass tests

### Verification Phase
- Validate against success criteria
- Run full test suite
- Check for regressions
- Document what was done

**Output:** Evidence that work is complete

## Auto-Context Loading

Use @ symbols to automatically trigger file reading:

```
[TASK]
Update authentication system
@src/auth/middleware.py
@src/auth/config.json
@tests/test_auth.py
```

Benefits:
- Agents automatically read files before starting
- No need for "first read X, then Y" instructions
- Ensures complete context from the start

## Success/Failure Boundaries

```
## Success Criteria
- All tests pass
- No hardcoded values
- Environment variables used consistently
- No debug/print statements in production

## Never Do
- Skip test coverage
- Commit secrets or credentials
- Use absolute file paths
- Leave TODO comments
- Accept partial completion as done
```

## Concrete Examples Over Descriptions

**INSTEAD OF:**
```
"Ensure proper error handling"
```

**USE:**
```python
try:
    result = await operation()
    return {"success": True, "data": result}
except Exception as error:
    logger.error(f"Operation failed: {error}")
    return {"success": False, "error": str(error)}
```

Concrete examples:
- Show exact implementation patterns
- Remove interpretation ambiguity
- Provide copy-paste templates
- Demonstrate best practices directly
