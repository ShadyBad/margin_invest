---
description: "GSD Scope Change — Documents and approves any mid-work scope change. Blocks implementation until change is recorded. Run whenever scope drifts from original triage."
argument-hint: "<run_id> <change description>"
allowed-tools: Bash, Read, Write
---

# /scope-change — Change Control

You are running Phase 9 of the GSD Workflow Engine.

Arguments: **$ARGUMENTS**
(Expected format: `<run_id> <change description>`)

## Step 1: Parse Input

Extract:
- `run_id` = first word of $ARGUMENTS
- `change_description` = rest of $ARGUMENTS

## Step 2: Load Original Scope

Read `runs/<run_id>/intake/scope.md`

If missing → output:
```
ERROR: No scope found for run <run_id>. Run /triage first.
```

## Step 3: Document the Change

Create `docs/scope-changes/` if it doesn't exist.

Generate change ID: `SC-<YYYYMMDD-HHMMSS>`

Write `docs/scope-changes/<SC-ID>.md`:
```markdown
# Scope Change: <SC-ID>

## Run ID: <run_id>
## Timestamp: <ISO8601>
## Status: APPROVED (self-approved) | PENDING_REVIEW

## Original Scope Summary
<paste 1-2 lines from original scope.md>

## Change Requested
<change_description>

## Impact Assessment

### Files Added/Modified Beyond Original Scope
- <list>

### Acceptance Criteria Changes Required
- <new criteria or modifications>

### Risk Delta
| New Risk | Severity | Mitigation |
|---|---|---|
| <risk> | H/M/L | <mitigation> |

### Track Re-evaluation
- Original track: LITE | FULL
- Change requires FULL track upgrade? Yes / No
- Reason: <if yes, explain>

### Effort Delta
- Original estimate: <from plan>
- Added work: <estimate>

## Decision
APPROVED — proceeding with updated scope.

## Updated Next Actions
1. <what to do now>
```

## Step 4: Update Scope File

Append to `runs/<run_id>/intake/scope.md`:
```markdown

---
## Scope Change: <SC-ID>
**Date:** <timestamp>
**Change:** <change_description>
**Impact:** <1-line summary>
```

## Step 5: Track Upgrade Check

If the scope change introduces any FULL track triggers (auth, payments, secrets, new integrations, etc.):

Update `runs/<run_id>/intake/track_decision.json` to FULL track.

Output warning:
```
⚠️  TRACK UPGRADED TO FULL
This change introduces <trigger>. Full track gates now apply.
Run /plan <run_id> to update architecture and security surface.
```

## Step 6: Summary Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE CHANGE RECORDED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Change ID:  <SC-ID>
Run ID:     <run_id>
Logged:     docs/scope-changes/<SC-ID>.md

<If track upgraded>:
⚠️  Track upgraded to FULL. Re-run /plan.

Resume:     /execute <run_id>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Write audit event:
```json
{"event": "scope_change", "run_id": "<run_id>", "change_id": "<SC-ID>", "track_upgraded": false, "timestamp": "<ISO8601>"}
```
