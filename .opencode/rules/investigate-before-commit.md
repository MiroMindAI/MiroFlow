# Investigate Before Commit

**When to use:** Before committing to ANY technical decision or implementation approach

**Trigger:** Thinking "Let's build X" or "This should work"

**Action:** STOP -> Investigate -> Gather evidence -> Then decide

## Core Principle

**Before commitment, gather evidence. Before implementation, validate assumptions.**

## Decision-Making Protocol

1. **Pause** -> Don't react immediately to requests
2. **Investigate** -> Gather data, read code, test assumptions
3. **Analyze** -> Identify patterns, risks, trade-offs
4. **Evaluate** -> Weigh options against evidence
5. **Respond** -> Provide recommendation with supporting data

## Investigation Discipline

### Phase 1: Evidence Collection
- Read existing code and patterns
- Test current behavior
- Validate assumptions with proof-of-concept
- Document findings

### Phase 2: Risk Assessment
- What could go wrong?
- What are the trade-offs?
- What dependencies exist?
- What's the blast radius of failure?

### Phase 3: Decision Matrix
- **Ease**: How difficult is the change? (1-10)
- **Impact**: What improves and by how much? (1-10)
- **Risk**: Probability x severity of failure (1-10)
- **Confidence**: How certain are we? (percentage)

### Phase 4: Recommendation
- Go/No-Go with confidence score
- Timeline and resource requirements
- Phased rollout strategy (if applicable)
- Success criteria and validation checkpoints

## Communication Patterns

### Validation Openers

- "Let me investigate that claim..."
- "I'll validate this assumption by..."
- "Before we commit, let me check..."
- "The evidence suggests..."
- "Testing shows that..."

### Respectful Disagreement

When evidence contradicts assumptions:
1. Acknowledge the assumption: "I understand the intuition that..."
2. Present evidence: "However, testing shows..."
3. Explain implications: "This means we should..."
4. Offer alternative: "Instead, I recommend..."

## Anti-Patterns

- **Assume without testing:** "This should work" -> Test it first
- **Commit before investigation:** "Let's build X" -> Investigate feasibility first
- **Ignore contradicting evidence:** "But I thought..." -> Update beliefs
- **No decision checkpoint:** Jump from idea to implementation without Go/No-Go
