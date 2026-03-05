---
description: "GSD Execute — Implementation phase. Runs vertical slice first, gates on acceptance criteria. Run after /plan."
argument-hint: "<run_id>"
allowed-tools: Bash, Read, Write, Edit
---

# /execute — Implementation

You are running Phase 5 of the GSD Workflow Engine.

Run ID: **$ARGUMENTS**

## Step 1: Gate Check — Prerequisites

Read and verify ALL of these exist:
- `runs/$ARGUMENTS/intake/scope.md` ✓
- `runs/$ARGUMENTS/intake/acceptance_criteria.md` ✓
- `runs/$ARGUMENTS/plan/architecture.md` ✓
- `runs/$ARGUMENTS/plan/impl_checklist.md` ✓

If any missing → **BLOCKED. Run missing phases first.**

Check `capabilities.yaml` is present. You will operate within those bounds.

Write audit event:
```json
{"event": "execute_started", "run_id": "$ARGUMENTS", "timestamp": "<ISO8601>"}
```

## Step 2: Vertical Slice First

**Do not implement everything at once.**

Pick the single most critical path through the acceptance criteria. Implement just that. Make it work end-to-end before expanding.

Document the slice in `runs/$ARGUMENTS/execute/slice.md`:
```markdown
# Vertical Slice

## Slice: <what you're proving works first>
## Acceptance Criteria Covered: <which criteria this proves>
## Files to Touch: <list>
```

## Step 3: Implement

Work through `runs/$ARGUMENTS/plan/impl_checklist.md` in order.

**Rules during implementation:**
- Every file change gets written to the audit log
- If you hit a scope expansion, STOP and run `/scope-change <run_id> <description>` before proceeding
- If you discover a security issue, write it to `runs/$ARGUMENTS/execute/security_flags.md` immediately
- No secrets in code — use env var references only
- Redact any sensitive values in logs: replace with `[REDACTED:<type>]`

After each checklist item, append to `runs/$ARGUMENTS/execute/progress.md`:
```
- [x] <task> — completed <timestamp>
```

## Step 4: Incremental Verification

After the vertical slice is complete, run:
```bash
# Run whatever your project's test command is
npm test   # or pytest, cargo test, etc.
```

If tests fail: fix before continuing. Do not stack failures.

Write results to `runs/$ARGUMENTS/execute/interim_test_results.log`

## Step 5: Complete Checklist

Continue through remaining checklist items. After each logical group:
1. Run lint
2. Run type check  
3. Run affected tests

Fail fast. Fix in place. Don't defer failures.

## Step 6: FULL Track — Security Phase

If track is FULL, after implementation:

Run or simulate:
- Dependency vulnerability scan: `npm audit` / `pip-audit` / `cargo audit`
- Review against `runs/$ARGUMENTS/plan/security_surface.md`
- Check every trust boundary is validated
- Confirm no secrets in code (`git grep -i "api_key\|password\|secret\|token" src/`)

Write `runs/$ARGUMENTS/security/scan_results.json`:
```json
{
  "run_id": "$ARGUMENTS",
  "timestamp": "<ISO8601>",
  "critical_findings": [],
  "high_findings": [],
  "medium_findings": [],
  "mitigations_applied": []
}
```

Write `runs/$ARGUMENTS/security/threat_model.md` covering the attack vectors identified in planning.

## Step 7: Acceptance Criteria Check

Go through every criterion in `runs/$ARGUMENTS/intake/acceptance_criteria.md`.

For each one: Is it verifiably met? Mark with evidence.

Write `runs/$ARGUMENTS/execute/criteria_status.md`:
```markdown
# Criteria Status

- [x] <criterion 1> — evidence: <test name / log line / behavior>
- [x] <criterion 2> — evidence: <...>
- [ ] <criterion 3> — NOT MET — blocker: <what's needed>
```

If any criterion NOT MET → don't proceed to /verify. Fix first.

## Step 8: Summary Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTE COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run ID:     $ARGUMENTS
Checklist:  <N>/<N> tasks complete
Criteria:   <N>/<N> met

<If any unmet criteria, list them here as BLOCKERS>

Next:       /verify $ARGUMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Write audit event:
```json
{"event": "execute_complete", "run_id": "$ARGUMENTS", "criteria_met": N, "criteria_total": N, "timestamp": "<ISO8601>"}
```
