---
description: "GSD Weekly Review (Phase R) — Prune dead artifacts, add golden cases from failures, close security exceptions, cut cost creep. Run weekly or after every 5 completed runs."
allowed-tools: Bash, Read, Write
---

# /review — Weekly Phase R

You are running Phase R of the GSD Workflow Engine.

## Step 1: Inventory Runs

List all runs in `runs/` directory:
```bash
ls -la runs/ | sort
```

Count:
- Total runs
- Completed (have `final/done_gate.json` with `"status": "DONE"`)
- Failed / abandoned (no done_gate or `"status": "NOT_DONE"`)

## Step 2: Failure Analysis

For every NOT_DONE run, read `runs/<id>/final/done_gate.json`.

Aggregate: Which gates fail most often?

Write `runs/review-<timestamp>/failure_patterns.md`:
```markdown
# Failure Patterns

| Gate | Failure Count | Runs |
|---|---|---|
| <gate_name> | N | <run_ids> |

## Root Causes
<analysis of why these gates are failing repeatedly>

## Systemic Fixes
<what to change in CLAUDE.md, hooks, or workflow to prevent recurrence>
```

## Step 3: Golden Cases

For every failure pattern, create a golden test case.

Write to `evals/golden_cases.jsonl` (append):
```jsonl
{"id": "gc-<timestamp>-001", "input": "<what triggered the failure>", "expected_behavior": "<what should have happened>", "gate": "<which gate failed>", "source_run": "<run_id>"}
```

## Step 4: Security Exception Review

Scan for open security findings:
```bash
grep -r "FINDING\|TODO\|FIXME\|HACK\|security" runs/*/security/ --include="*.md" --include="*.json" 2>/dev/null | head -50
```

For each open finding:
- Still relevant? → Keep, schedule fix
- Mitigated? → Close with evidence
- False positive? → Document and close

Write `runs/review-<timestamp>/security_exceptions.md` with status of each.

## Step 5: Cost Creep Audit

Count agent spawns across recent runs:
```bash
grep '"event": "agent_spawn"' runs/*/audit/events.jsonl 2>/dev/null | wc -l
```

Flag any run that spawned >5 agents. Assess if they were necessary.

Identify: Which phases are producing the most artifact bloat?

Write `runs/review-<timestamp>/cost_analysis.md`:
```markdown
# Cost Analysis

## Agent Spawn Count (last N runs): <total>
## Avg agents per run: <N>
## High-spawn runs: <list>

## Artifact Size
<du -sh runs/* output>

## Recommendations
<what to cut, what to optimize>
```

## Step 6: CLAUDE.md Health Check

Review current `CLAUDE.md`. Ask:
1. Are the key project commands still accurate?
2. Are there new patterns or conventions to add?
3. Is the redaction list complete?
4. Are any sections outdated?

If updates needed: edit `CLAUDE.md` directly and note changes.

## Step 7: Cleanup

Archive or delete abandoned runs older than 30 days:
```bash
# List candidates
find runs/ -maxdepth 1 -type d -mtime +30 | head -20
```

Do NOT delete runs with `"status": "DONE"` unless explicitly requested.

## Step 8: Summary Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEEKLY REVIEW COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs Analyzed:    <N>
  DONE:           <N>
  NOT_DONE:       <N>
  Abandoned:      <N>

Golden Cases Added: <N>
Security Exceptions: <N> open / <N> closed
CLAUDE.md Updates: <N> changes

Top Failure Gate: <gate_name> (<N> failures)
Top Fix: <what to do>

Report: runs/review-<timestamp>/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
