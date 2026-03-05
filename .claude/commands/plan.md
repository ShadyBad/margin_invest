---
description: "GSD Plan — Architecture, interfaces, phase IO schemas, error taxonomy. Run after /triage. Required before /execute."
argument-hint: "<run_id>"
allowed-tools: Bash, Read, Write
---

# /plan — Architecture & Interface Design

You are running Phase 2 of the GSD Workflow Engine.

Run ID: **$ARGUMENTS**

## Step 1: Load Context

Read these files:
- `runs/$ARGUMENTS/intake/scope.md`
- `runs/$ARGUMENTS/intake/acceptance_criteria.md`
- `runs/$ARGUMENTS/intake/track_decision.json`

If any are missing, stop and output:
```
BLOCKED: Run /triage <description> first.
```

Write audit event:
```json
{"event": "plan_started", "run_id": "$ARGUMENTS", "timestamp": "<ISO8601>"}
```

## Step 2: Architecture Design

Write `runs/$ARGUMENTS/plan/architecture.md`:

```markdown
# Architecture: <title>

## Approach
<Why this approach. What alternatives were considered and rejected.>

## Components Affected
| Component | Change Type | Notes |
|---|---|---|
| <file/module> | add/modify/delete | <why> |

## Data Flow
<ASCII diagram or numbered flow description>

## Dependencies
- New dependencies: <list or "none">
- Removed dependencies: <list or "none">

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| <risk> | H/M/L | <mitigation> |
```

## Step 3: Interface Definitions

Write `runs/$ARGUMENTS/plan/interfaces.md`:

Define all public interfaces, function signatures, API contracts, or data schemas that will change or be created.

Use concrete types. No hand-waving.

## Step 4: Error Taxonomy

Write `runs/$ARGUMENTS/plan/error_taxonomy.md`:

```markdown
# Error Taxonomy

| Error | Cause | User Impact | Recovery |
|---|---|---|---|
| <ErrorType> | <what causes it> | <what user sees> | <how to recover> |
```

Cover at minimum:
- Input validation failures
- External service failures  
- Timeout / rate limit scenarios
- Auth failures (FULL track)
- Data corruption scenarios (if data is written)

## Step 5: FULL Track — Security Pre-Assessment

If track is FULL, also write `runs/$ARGUMENTS/plan/security_surface.md`:

```markdown
# Security Surface

## Trust Boundaries Crossed
<list boundaries: user input → system, system → DB, system → external API, etc.>

## Data Sensitivity
<what data is touched, classification: public/internal/confidential/secret>

## Auth/AuthZ Points
<what permissions are required, where they're checked>

## Top 3 Attack Vectors to Threat Model
1. <vector>
2. <vector>  
3. <vector>
```

## Step 6: Implementation Checklist

Generate a concrete, ordered implementation checklist in `runs/$ARGUMENTS/plan/impl_checklist.md`.

This is the task list /execute will work through. Be specific. No "implement X" — write "Add `validateInput()` to `src/utils/validation.ts` that checks..."

## Step 7: Summary Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLAN COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run ID:  $ARGUMENTS
Files:   architecture.md, interfaces.md, error_taxonomy.md

<If FULL>:
         security_surface.md

Checklist: <N> implementation tasks

Next:    /execute $ARGUMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Write audit event:
```json
{"event": "plan_complete", "run_id": "$ARGUMENTS", "checklist_items": N, "timestamp": "<ISO8601>"}
```
