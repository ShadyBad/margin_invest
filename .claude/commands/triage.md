---
description: "GSD Triage — Start every task here. Captures scope, selects Lite vs Full track, locks acceptance criteria, generates next actions. Required before /plan or /execute."
argument-hint: "<feature/change description>"
allowed-tools: Bash, Read, Write
---

# /triage — Intake & Track Selection

You are running Phase 1 of the GSD Workflow Engine.

## Step 1: Generate Run ID

Create a run ID in this format: `YYYYMMDD-HHMMSS-<slug>` where slug is a 3-word kebab-case summary of the work.

Create the run directory:
```
runs/<run_id>/intake/
runs/<run_id>/audit/
```

Write the first audit event:
```json
{"event": "run_started", "run_id": "<run_id>", "command": "triage", "input": "$ARGUMENTS", "timestamp": "<ISO8601>"}
```
to `runs/<run_id>/audit/events.jsonl`

## Step 2: Scope Capture

Using the input: **$ARGUMENTS**

Ask the following clarifying questions IF the input is ambiguous. If input is clear, use smart defaults and proceed.

**Clarifying questions (ask max 3, only if truly unclear):**
1. What is the expected outcome / user-facing behavior change?
2. What systems/files/APIs are definitely in scope?
3. Are there hard constraints (deadline, performance, compatibility)?

Write `runs/<run_id>/intake/scope.md`:
```markdown
# Scope: <title>

## Summary
<1-2 sentence plain English description>

## In Scope
- <explicit inclusions>

## Out of Scope  
- <explicit exclusions>

## Constraints
- <hard constraints>

## Run ID: <run_id>
## Locked: <timestamp>
```

## Step 3: Track Selection

Evaluate against FULL track triggers. Check each:

| Trigger | Present? |
|---|---|
| Auth / permissions touched | Yes / No |
| Payments / billing touched | Yes / No |
| User data handling / PII | Yes / No |
| Secrets / credentials | Yes / No |
| New external integrations | Yes / No |
| DB schema changes | Yes / No |
| Security-sensitive code paths | Yes / No |

**Decision:**
- 0 triggers → **LITE track**
- 1+ triggers → **FULL track**
- Ambiguous → **FULL track** (when in doubt, full)

Write `runs/<run_id>/intake/track_decision.json`:
```json
{
  "run_id": "<run_id>",
  "track": "LITE | FULL",
  "triggers_found": ["<list>"],
  "rationale": "<1 sentence>"
}
```

## Step 4: Acceptance Criteria

Write clear, testable acceptance criteria. Every criterion must be verifiable.

Format: Given / When / Then OR bullet checklist. No vague language ("works correctly", "looks good").

Write `runs/<run_id>/intake/acceptance_criteria.md`:
```markdown
# Acceptance Criteria: <title>

## Criteria

- [ ] <specific, testable criterion 1>
- [ ] <specific, testable criterion 2>
- [ ] <specific, testable criterion 3>

## Definition of Done
All criteria checked. Done Gate passes. No open blockers.
```

## Step 5: Next Actions

Write `runs/<run_id>/intake/next_actions.md` with:
- The track selected (LITE or FULL)
- Ordered phases to run
- Exact commands to run next
- Any pre-conditions or decisions needed before proceeding

## Step 6: Summary Output

Print to terminal:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRIAGE COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run ID:  <run_id>
Track:   LITE | FULL
Scope:   <1-line summary>

Acceptance Criteria: <N> defined

Next:    /plan <run_id>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Write final audit event:
```json
{"event": "triage_complete", "run_id": "<run_id>", "track": "<track>", "criteria_count": N, "timestamp": "<ISO8601>"}
```
