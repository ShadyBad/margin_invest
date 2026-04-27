# Customer Discovery Pressure-Test v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the 7 amendments from the v2 pressure-test spec (`docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-v2-design.md`) into the customer-discovery sprint artifacts, producing `action-plan.md` v2.1 with PII protection holes plugged, runtime override visibility added, Stripe cancel-reason capture wired, and scope expectations realistic.

**Architecture:** Pure documentation patches across 5 markdown files in `docs/customer-discovery/`. No new files, no executable code, no test-suite impact. Phase 0 docs (`preorder-test.md`) are touched only via the additions-only banner pattern already established in v1. Edits are committed in 5 logical commits — one per modified file.

**Tech Stack:** Markdown-only. Verified via `grep` and `Read`. Each task uses the doc-edit analog of TDD: pre-check (grep should NOT find new text), apply Edit, post-check (grep SHOULD find new text).

---

## File Structure

| File | Edits | Spec finding(s) | Tasks |
|---|---|---|---|
| `docs/customer-discovery/action-plan.md` | 5 amendments | #1, #5, #6 (part 1), #7 (part 1), Amendment C | 1-5 |
| `docs/customer-discovery/preorder-test.md` | 1 amendment | #4 | 6 |
| `docs/customer-discovery/phase-3-prep.md` | 1 amendment | #3 | 7 |
| `docs/customer-discovery/phase-4-templates.md` | 2 amendments | #2, #6 (part 2) | 8-9 |
| `docs/customer-discovery/beta-deliverable.md` | 1 amendment | #7 (part 2) | 10 |

No new files. 11 tasks total (10 edits + 1 final verification). 5 commits total.

---

### Task 1: action-plan.md — Cleanup procedure block (Amendment A → finding #1)

**Files:**
- Modify: `docs/customer-discovery/action-plan.md` (line 8, leading "PII retention policy" paragraph)

**Background:** Spec finding #1 — current cleanup procedure deletes `transcripts/` and `scores/` and clears `disqualified-log.md` rows but does NOT touch `pipeline.csv`. The handle ↔ first-name bridge survives Day +30 indefinitely. Add explicit `pipeline.csv` data-row clearing to symmetrically protect the bridge.

- [ ] **Step 1.1: Pre-check — confirm new text is NOT present**

```bash
grep -c "head -1 docs/customer-discovery/pipeline.csv" docs/customer-discovery/action-plan.md
```

Expected: `0` (no matches yet).

- [ ] **Step 1.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/action-plan.md`.

`old_string`:
```
**PII retention policy (committed 2026-04-27)**: **Option A** — delete all transcripts, scorecards, and disqualified-log entries 30 days after `decision.md` is committed. Cleanup procedure: `rm -rf docs/customer-discovery/transcripts/ docs/customer-discovery/scores/`; clear disqualified-log.md row data (keep header); commit a "post-decision PII cleanup" marker.
```

`new_string`:
````
**PII retention policy (committed 2026-04-27)**: **Option A** — delete all transcripts, scorecards, `pipeline.csv` data rows, and disqualified-log entries 30 days after `decision.md` is committed.

Cleanup procedure (run AFTER `decision.md` Audit Appendix is appended; see `phase-4-templates.md`):

```bash
# 1. Delete transcripts and scorecards
rm -rf docs/customer-discovery/transcripts/
rm -rf docs/customer-discovery/scores/

# 2. Clear pipeline.csv data rows (preserve header)
head -1 docs/customer-discovery/pipeline.csv > /tmp/pipeline_header.csv
mv /tmp/pipeline_header.csv docs/customer-discovery/pipeline.csv

# 3. Manually clear data rows under the "## Log" table in disqualified-log.md
#    Keep all markdown structure and column headers; remove only data rows.
```

Then commit: `docs(discovery): post-decision PII cleanup (Day +30)`.
````

- [ ] **Step 1.3: Post-check — confirm new text IS present**

```bash
grep -c "head -1 docs/customer-discovery/pipeline.csv" docs/customer-discovery/action-plan.md
grep -c "Audit Appendix is appended" docs/customer-discovery/action-plan.md
```

Expected: both return `1` or higher.

(Do NOT commit yet — `action-plan.md` has more edits in Tasks 2-5; commit at end of Task 5.)

---

### Task 2: action-plan.md — Day-3 capacity checkpoint (finding #5)

**Files:**
- Modify: `docs/customer-discovery/action-plan.md` (insert before line 216, the "Day-7 yield gate (NEW):" section)

**Background:** Spec finding #5 — at ~18% DM-to-scheduled conversion, hitting 8 scheduled by Day 7 requires ~44 DMs sent, exceeding Reddit's 5/day cap (35 max in 7 days) and Twitter's 7-14 day pre-warmup window. The Day-7 gate as written conflates volume capacity with response yield. Add a Day-3 capacity checkpoint that distinguishes the two failure modes.

- [ ] **Step 2.1: Pre-check**

```bash
grep -c "Day-3 capacity checkpoint" docs/customer-discovery/action-plan.md
```

Expected: `0`.

- [ ] **Step 2.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/action-plan.md`.

`old_string`:
```
Day-7 yield gate (NEW):
- After 7 days of recruitment, count scheduled calls.
- If ≥8 scheduled: continue as planned.
- If <8 scheduled: pause and choose:
  (a) Expand channels (Twitter Lists, paid Discord servers, Substack
      comments on Bearcave/Hindenburg/Kerrisdale)
  (b) Raise gift to $75-100 and re-DM cold prospects with the bump
  (c) Accept reality and rescope sprint to 8 interviews / 5 paid asks
- Document the choice in pipeline.csv notes column. Do not just send harder.
```

`new_string`:
```
Day-3 capacity checkpoint (NEW):
- After 3 days of recruitment, count personalized DMs sent so far across all
  active channels.
- Target: ≥15 DMs sent by Day 3.
- If <15 DMs sent: bottleneck is volume, not yield. Solutions:
  (i)   Open additional channels (Substack comment-section outreach, Discord
        with mod permission)
  (ii)  Accept that the original 18-scheduled-by-Day-21 trajectory may need a
        different ratio
  (iii) Consider whether channel-rules constraints (recruitment-channel-rules.md)
        make FULL scope unreachable; rescope to HALF before more goodwill
        is spent
- If ≥15 DMs sent and yield is poor (<3 responses): bottleneck is conversion.
  The Day-7 gate logic below applies.
- Document the conclusion in pipeline.csv notes column.

Day-7 yield gate (NEW):
- After 7 days of recruitment, count scheduled calls.
- If ≥8 scheduled: continue as planned.
- If <8 scheduled AND Day-3 capacity check passed (≥15 DMs sent): bottleneck is
  conversion. Pause and choose:
  (a) Expand channels (Twitter Lists, paid Discord servers, Substack
      comments on Bearcave/Hindenburg/Kerrisdale)
  (b) Raise gift to $75-100 and re-DM cold prospects with the bump
  (c) Accept reality and rescope sprint to 8 interviews / 5 paid asks
- If <8 scheduled AND Day-3 capacity check failed: do NOT just send harder. The
  problem is structural — solve it via Day-3 remediation paths first.
- Document the choice in pipeline.csv notes column. Do not just send harder.
```

- [ ] **Step 2.3: Post-check**

```bash
grep -c "Day-3 capacity checkpoint" docs/customer-discovery/action-plan.md
grep -c "Day-7 yield gate" docs/customer-discovery/action-plan.md
```

Expected: both return `1` or higher.

(No commit yet.)

---

### Task 3: action-plan.md — Soften "top 3 alternative ICPs" (finding #6, part 1)

**Files:**
- Modify: `docs/customer-discovery/action-plan.md` (lines 470-473, Phase 4 NO-GO branch step 4)

**Background:** Spec finding #6 — Phase 4 NO-GO branch reads `disqualified-log.md` for "top 3 alternative ICPs," but realistic log yield from 15 interviews is 0-3 entries. The "top 3" phrasing assumes data that may not exist. Soften to acknowledge the data is anecdote-quality and feeds a fresh brainstorm rather than being a finished pivot recommendation.

- [ ] **Step 3.1: Pre-check**

```bash
grep -c "anecdote-quality" docs/customer-discovery/action-plan.md
```

Expected: `0`.

- [ ] **Step 3.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/action-plan.md`.

`old_string`:
```
   4. Read back top 3 alternative ICPs from
      docs/customer-discovery/disqualified-log.md (the 5-min probe data) —
      these are candidate pivots.
   5. Open fresh /superpowers:brainstorming on those.
```

`new_string`:
```
   4. Read back the disqualified-log.md probe data. Realistic yield from 15
      interviews where the goal was qualified prospects: 0-3 entries. Treat
      this as anecdote-quality input, NOT a finished pivot recommendation.
      With 1-3 entries: the log feeds a fresh brainstorm — do not skip the
      brainstorm and treat the log as already telling you which ICP to pivot
      to. With 0 entries: the absence of pivot data is itself a finding. The
      next sprint must explicitly recruit for alternative-ICP signal.
   5. Open fresh /superpowers:brainstorming on candidate pivot ICPs (with
      log data as raw input where available, or with no scaffolding if the
      log is empty).
```

- [ ] **Step 3.3: Post-check**

```bash
grep -c "anecdote-quality" docs/customer-discovery/action-plan.md
grep -c "absence of pivot data is itself a finding" docs/customer-discovery/action-plan.md
```

Expected: both return `1`.

(No commit yet.)

---

### Task 4: action-plan.md — Tighten Phase 5 exploratory throughput (finding #7, part 1)

**Files:**
- Modify: `docs/customer-discovery/action-plan.md` (lines 540-541, exploratory Phase 5 prompt block)

**Background:** Spec finding #7 — exploratory Phase 5 (Days 21-28) is described as "1 week of scoped roadmap work," reading like a feature ships at Day 28 ready for Day 35 launch. In a 35K-LOC codebase with strict TDD and ML/scoring approval gates, realistic Day-21→28 throughput is "design + scaffold + at most one MICRO change merged." Anything STANDARD or larger is queued for committed Phase 5. Add this throughput cap to the prompt.

- [ ] **Step 4.1: Pre-check**

```bash
grep -c "Realistic Day-21→28 throughput" docs/customer-discovery/action-plan.md
```

Expected: `0`.

- [ ] **Step 4.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/action-plan.md`.

`old_string`:
```
This is exploratory Phase 5 — 1 week of scoped roadmap work, no full
commitment yet. Retention gate at Day 51 is what unlocks the 90-day commitment.

Use /flow:triage to translate the top three feature priorities from
decision.md into Gold Flow runs. For each:
- Cite the transcript quotes that justify the feature
- Lock acceptance criteria that a real interviewed prospect could verify
- Route to /flow:plan if complexity warrants or /flow:execute if MICRO
```

`new_string`:
```
This is exploratory Phase 5 — 1 week of scoped roadmap work, no full
commitment yet. Retention gate at Day 51 is what unlocks the 90-day commitment.

Realistic Day-21→28 throughput in this codebase: design + scaffold + at most
one MICRO change merged. Anything classified STANDARD or larger by /flow:triage
is queued for committed Phase 5 (Day 51+), not promised in the founder beta.
The Day-35 customer deliverable (see beta-deliverable.md) reflects this cap.

Use /flow:triage to translate the top three feature priorities from
decision.md into Gold Flow runs. For each:
- Cite the transcript quotes that justify the feature
- Lock acceptance criteria that a real interviewed prospect could verify
- Route to /flow:plan if complexity warrants or /flow:execute if MICRO
- If /flow:triage classifies the priority as STANDARD or larger: queue for
  committed Phase 5 — do not attempt to ship inside the Day-21→28 window.
```

- [ ] **Step 4.3: Post-check**

```bash
grep -c "Realistic Day-21→28 throughput" docs/customer-discovery/action-plan.md
grep -c "queue for" docs/customer-discovery/action-plan.md
```

Expected: both return `1` or higher.

(No commit yet.)

---

### Task 5: action-plan.md — Add Pre-flight gates PF.8/PF.9/PF.10 (Amendment C)

**Files:**
- Modify: `docs/customer-discovery/action-plan.md` (lines 91-97, Pre-flight acceptance criteria bullet list)

**Background:** Spec Amendment block C — the pre-flight checklist needs three new gate items to operationalize findings #3 (Stripe cancellation reasons), #4 (preorder-test.md override banner), and #5 (Day-3 capacity checkpoint definition). Add these to the existing bullet list under "Acceptance criteria".

- [ ] **Step 5.1: Pre-check**

```bash
grep -c "PF.8\|PF.9\|PF.10" docs/customer-discovery/action-plan.md
```

Expected: `0`.

- [ ] **Step 5.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/action-plan.md`.

`old_string`:
```
**Acceptance criteria**:

- 18 calendar slots pre-blocked over the next 21 days
- `docs/customer-discovery/beta-deliverable.md` committed (Day-35 product scope)
- `docs/customer-discovery/recruitment-channel-rules.md` committed (per-channel compliance)
- Founder-hour commitment: ≥30 hours blocked, OR sprint rescoped to 8/5
- Anonymization rules added to `interview-guide.md` (consent script, ticker pseudonyms, dollar buckets)
- $50 gift payout rule added to `interview-guide.md` (paid only after qualified completion OR disqualified-but-probed)
- `docs/customer-discovery/disqualified-log.md` scaffolded
```

`new_string`:
```
**Acceptance criteria**:

- 18 calendar slots pre-blocked over the next 21 days
- `docs/customer-discovery/beta-deliverable.md` committed (Day-35 product scope)
- `docs/customer-discovery/recruitment-channel-rules.md` committed (per-channel compliance)
- Founder-hour commitment: ≥30 hours blocked, OR sprint rescoped to 8/5
- Anonymization rules added to `interview-guide.md` (consent script, ticker pseudonyms, dollar buckets)
- $50 gift payout rule added to `interview-guide.md` (paid only after qualified completion OR disqualified-but-probed)
- `docs/customer-discovery/disqualified-log.md` scaffolded
- **PF.8** Stripe Customer Portal cancellation reasons enabled (Stripe Dashboard → Settings → Billing → Customer Portal → Cancellation reasons), with reason options mapped to objection tags (delivery-risk / price-objection / feature-gap / disinterest / other). Capture screenshot or config-export reference in `phase-3-prep.md`.
- **PF.9** `preorder-test.md` override banner inserted at top of file pointing to `phase-3-prep.md` for v2 amendments (additions-only; body remains scope-locked).
- **PF.10** Day-3 capacity checkpoint defined in Phase 1 prompt (separate from Day-7 yield evaluation), so volume vs conversion failure modes are distinguished.
```

- [ ] **Step 5.3: Post-check**

```bash
grep -c "PF.8\|PF.9\|PF.10" docs/customer-discovery/action-plan.md
```

Expected: `3`.

- [ ] **Step 5.4: Commit all `action-plan.md` changes**

```bash
git add docs/customer-discovery/action-plan.md
git commit -m "$(cat <<'EOF'
docs(discovery): action-plan.md v2.1 — land 5 pressure-test v2 amendments

- Cleanup procedure now zeros pipeline.csv data rows (Amendment A → #1)
- Phase 1 prompt: Day-3 capacity checkpoint added before Day-7 yield gate (#5)
- Phase 4 NO-GO branch: alt-ICP language softened to anecdote-quality (#6)
- Phase 5 exploratory prompt: Day-21→28 throughput cap codified (#7)
- Pre-flight checklist: PF.8 (Stripe cancel reasons), PF.9 (preorder-test
  banner), PF.10 (Day-3 checkpoint) added (Amendment C)

Source: docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-v2-design.md
EOF
)"
```

Expected: 1 file changed, ~30 insertions / ~15 deletions.

---

### Task 6: preorder-test.md — Override banner (finding #4)

**Files:**
- Modify: `docs/customer-discovery/preorder-test.md` (insert at top, before line 1 `# Preorder Test`)

**Background:** Spec finding #4 — `action-plan.md` declares `preorder-test.md` "scope-locked, do not modify" but `phase-3-prep.md` overrides its thresholds and ask-cohort rules. A founder under runtime stress reading only `preorder-test.md` will use wrong thresholds. Add an additions-only override banner at the top of the file (matches the additions-only pattern already used in `interview-guide.md`).

- [ ] **Step 6.1: Pre-check**

```bash
head -3 docs/customer-discovery/preorder-test.md
```

Expected: file currently begins with `# Preorder Test — $49 Founder Beta`.

```bash
grep -c "v2 amendments live in" docs/customer-discovery/preorder-test.md
```

Expected: `0`.

- [ ] **Step 6.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/preorder-test.md`.

`old_string`:
```
# Preorder Test — $49 Founder Beta

## Overview
```

`new_string`:
```
# Preorder Test — $49 Founder Beta

> **v2 amendments live in `phase-3-prep.md`. Read `phase-3-prep.md` BEFORE running Phase 3** — thresholds, ask-cohort rules (Option A vs B), and price-arm rules are amended there. The body of this document is preserved as the scope-locked Phase 0 reference and is OVERRIDDEN where it conflicts with `phase-3-prep.md`.

## Overview
```

- [ ] **Step 6.3: Post-check**

```bash
grep -c "v2 amendments live in" docs/customer-discovery/preorder-test.md
head -5 docs/customer-discovery/preorder-test.md
```

Expected: grep returns `1`; the banner appears between the H1 and `## Overview`.

- [ ] **Step 6.4: Commit**

```bash
git add docs/customer-discovery/preorder-test.md
git commit -m "$(cat <<'EOF'
docs(discovery): preorder-test.md — override banner pointing to phase-3-prep

Spec finding #4 — runtime visibility risk. Body remains scope-locked; banner
is additions-only (matches the pattern used in interview-guide.md for consent
script, anonymization rules, and gift payout rule).

Source: docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-v2-design.md
EOF
)"
```

Expected: 1 file changed, 2 insertions(+).

---

### Task 7: phase-3-prep.md — Stripe cancellation-reasons bullet (finding #3)

**Files:**
- Modify: `docs/customer-discovery/phase-3-prep.md` (line 112-113, Checkout session configuration block — insert new bullet after "Customer portal: enabled for self-serve cancellation")

**Background:** Spec finding #3 — `action-plan.md` retention-gate prompt expects "cancellation reason via Stripe portal," but Stripe collects cancel reasons only if explicitly enabled at portal config. Currently the checklist doesn't include this step. Day-51 retention investigation runs blind without it. Add a bullet to the checklist.

- [ ] **Step 7.1: Pre-check**

```bash
grep -c "cancellation reasons" docs/customer-discovery/phase-3-prep.md
```

Expected: `0`.

- [ ] **Step 7.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/phase-3-prep.md`.

`old_string`:
```
- [ ] Customer portal: enabled for self-serve cancellation
- [ ] Session metadata template: `prospect_name`, `interview_number`, `source`, `strong_signals`, `price_arm` (if 2-arm)
```

`new_string`:
````
- [ ] Customer portal: enabled for self-serve cancellation
- [ ] **Customer portal cancellation reasons**: enabled in Stripe Dashboard (Settings → Billing → Customer Portal → Cancellation reasons → Configure: include 4-6 reason options + optional comment field). Reasons should map to objection tags:
  - `delivery-risk` → "Wasn't ready when expected"
  - `price-objection` → "Too expensive"
  - `feature-gap` → "Missing key feature"
  - `disinterest` → "Didn't fit my needs"
  - other (free-text comment)

  Without this enabled, the Day-51 retention investigation has no Stripe-side churn-reason data and falls back entirely to optional founder-side outreach.
- [ ] Session metadata template: `prospect_name`, `interview_number`, `source`, `strong_signals`, `price_arm` (if 2-arm)
````

- [ ] **Step 7.3: Post-check**

```bash
grep -c "cancellation reasons" docs/customer-discovery/phase-3-prep.md
grep -c "delivery-risk" docs/customer-discovery/phase-3-prep.md
```

Expected: grep returns `≥1` for both.

- [ ] **Step 7.4: Commit**

```bash
git add docs/customer-discovery/phase-3-prep.md
git commit -m "$(cat <<'EOF'
docs(discovery): phase-3-prep.md — wire Stripe cancel-reason capture

Spec finding #3 — the Day-51 retention investigation expects Stripe-collected
cancellation reasons, but the portal config bullet did not include enabling
them. Add the checklist item with reason options mapped to the objection-tag
schema used in Phase 3.

Source: docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-v2-design.md
EOF
)"
```

Expected: 1 file changed, ~9 insertions(+).

---

### Task 8: phase-4-templates.md — Audit Appendix template (Amendment B → finding #2)

**Files:**
- Modify: `docs/customer-discovery/phase-4-templates.md` (decision.md skeleton section — append new "## Audit Appendix" section to the skeleton template, after the existing skeleton body but before the `## decision.md` skeleton's closing or next major section)

**Background:** Spec finding #2 — the `decision.md` skeleton cites rubric-bucket conversion rates, dominant objection patterns, and anonymized transcript quotes. At Day +30, the source artifacts (`transcripts/`, `scores/`) are deleted by the cleanup procedure (now extended in Task 1 to also clear `pipeline.csv`). Post-cleanup the verdict's evidence trail is destroyed. Add a pre-cleanup audit-appendix section that captures de-identified aggregate evidence, run BEFORE the cleanup script.

- [ ] **Step 8.1: Pre-check**

```bash
grep -c "Audit Appendix" docs/customer-discovery/phase-4-templates.md
```

Expected: `0`.

The decision.md skeleton is wrapped in a ```` ```markdown ```` code block starting at line 14 and closing at line 202. The Audit Appendix lives INSIDE the skeleton (it's part of the template the user copies into a real decision.md). The last skeleton bullet is `**What I'd change in v3 of this playbook**: [...]`, immediately followed by the closing ```` ``` ```` fence on the next line.

- [ ] **Step 8.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/phase-4-templates.md`.

`old_string`:
```
- **What I'd change in v3 of this playbook**: [...]
```
```

`new_string`:
```
- **What I'd change in v3 of this playbook**: [...]

---

## Audit Appendix (de-identified aggregate evidence — preserved post-cleanup)

*Run BEFORE triggering the Day +30 cleanup. Once cleanup runs, the source artifacts (transcripts, scores, pipeline.csv data rows) are deleted; this appendix is the durable evidence trail.*

### Rubric-bucket conversion (Option B only)
[Duplicate the rubric-bucket conversion table from the main body for permanence.]

### Objection-tag distribution
| tag | count | % of non-payment |
|---|---|---|
| delivery-risk | | |
| price-objection | | |
| feature-gap | | |
| disinterest | | |

### Representative quotes per dominant objection tag
3-5 quotes per tag, fully de-identified (`$TICKER_X` intact, dollar buckets intact, no first names).

### Cohort sizes by source channel
| source | recruited | scheduled | completed | strong | paid | retained_d51 |
|---|---|---|---|---|---|---|
| Reddit | | | | | | |
| Twitter | | | | | | |
| Substack | | | | | | |

### Retention summary (Day 51)
- Charge cohort size: [N]
- Retained at Day 51: [N] ([X]%)
- Churn reasons by Stripe-portal tag: [counts]
- Churn reasons by founder follow-up email: [counts]
```
```

- [ ] **Step 8.3: Post-check**

```bash
grep -c "Audit Appendix" docs/customer-discovery/phase-4-templates.md
grep -c "preserved post-cleanup" docs/customer-discovery/phase-4-templates.md
```

Expected: both return `1` or higher.

(No commit yet — Task 9 also edits this file.)

---

### Task 9: phase-4-templates.md — Soften alt-ICP NO-GO step (finding #6, part 2)

**Files:**
- Modify: `docs/customer-discovery/phase-4-templates.md` (line 306, NO-GO sequence checklist step "Read disqualified-log.md, surface top-3 alternative ICPs in decision.md")

**Background:** Spec finding #6, second part — the NO-GO sequence checklist in `phase-4-templates.md` step 10 also assumes 3 alt-ICPs are findable. Align this with the softened action-plan.md language landed in Task 3.

- [ ] **Step 9.1: Pre-check**

```bash
grep -c "anecdote-quality" docs/customer-discovery/phase-4-templates.md
```

Expected: `0` (Task 8 added an Audit Appendix; this term isn't in it).

- [ ] **Step 9.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/phase-4-templates.md`.

`old_string`:
```
10. [ ] Read `disqualified-log.md`, surface top-3 alternative ICPs in `decision.md`
```

`new_string`:
```
10. [ ] Read `disqualified-log.md`, append the probe data to `decision.md` as anecdote-quality input. Realistic yield is 0-3 entries — do NOT pad to "top 3" if fewer exist. With 0 entries: note that absence of pivot data is itself a finding for the next sprint.
```

- [ ] **Step 9.3: Post-check**

```bash
grep -c "anecdote-quality" docs/customer-discovery/phase-4-templates.md
```

Expected: `1`.

- [ ] **Step 9.4: Commit all `phase-4-templates.md` changes**

```bash
git add docs/customer-discovery/phase-4-templates.md
git commit -m "$(cat <<'EOF'
docs(discovery): phase-4-templates.md — Audit Appendix + alt-ICP softening

- Audit Appendix template added to decision.md skeleton (Amendment B → #2):
  de-identified aggregate evidence preserved BEFORE Day +30 cleanup so the
  verdict's evidence trail survives the privacy procedure.
- NO-GO sequence step 10 softened to anecdote-quality framing (#6, part 2),
  matching the action-plan.md change landed in the prior commit.

Source: docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-v2-design.md
EOF
)"
```

Expected: 1 file changed, ~30 insertions / ~1 deletion.

---

### Task 10: beta-deliverable.md — Throughput cap append (finding #7, part 2)

**Files:**
- Modify: `docs/customer-discovery/beta-deliverable.md` (line 14, "Included on Day 35" lead paragraph)

**Background:** Spec finding #7, second part — the customer-facing scope doc says Day 35 includes "platform as it exists today plus any exploratory Phase 5 work (Days 21-28) committed before launch." Without a throughput cap, this language can imply features that won't actually ship in 7 days. Add the explicit cap so customer consent matches reality.

- [ ] **Step 10.1: Pre-check**

```bash
grep -c "Exploratory Phase 5 throughput cap" docs/customer-discovery/beta-deliverable.md
```

Expected: `0`.

- [ ] **Step 10.2: Apply the Edit**

Use the Edit tool on `docs/customer-discovery/beta-deliverable.md`.

`old_string`:
```
The Founder Beta is access to the running Margin Invest application. The build state at Day 35 reflects the platform as it exists today (2026-04-27) plus any exploratory Phase 5 work (Days 21-28) committed before launch.
```

`new_string`:
```
The Founder Beta is access to the running Margin Invest application. The build state at Day 35 reflects the platform as it exists today (2026-04-27) plus any exploratory Phase 5 work (Days 21-28) committed before launch.

**Exploratory Phase 5 throughput cap (Days 21-28)**: at most one MICRO change — a small UI surface, a bug-fix, or a minor data-wiring change — may land in time for Day 35. Larger features (new scoring factors, ML changes, new pages) will NOT ship in the founder-beta scope; they land post-retention-gate (Day 51+) under committed Phase 5. This cap exists because the codebase has strict TDD, sector-neutral scoring tests, ML approval gates, and circuit-breaker governance — 7 days is realistic for one MICRO change, not for a STANDARD feature.
```

- [ ] **Step 10.3: Post-check**

```bash
grep -c "Exploratory Phase 5 throughput cap" docs/customer-discovery/beta-deliverable.md
```

Expected: `1`.

- [ ] **Step 10.4: Commit**

```bash
git add docs/customer-discovery/beta-deliverable.md
git commit -m "$(cat <<'EOF'
docs(discovery): beta-deliverable.md — Day-35 exploratory throughput cap

Spec finding #7, customer-facing half — the Day-35 deliverable description
implicitly promised feature-shipping in 7 days. Add an explicit cap so
customer consent matches engineering reality. Pairs with the action-plan.md
exploratory Phase 5 prompt change landed earlier in this branch.

Source: docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-v2-design.md
EOF
)"
```

Expected: 1 file changed, 2 insertions(+).

---

### Task 11: Final verification — all 7 amendments present across 5 files

**Files:**
- Read-only verification across all 5 modified files.

**Background:** Confirm every amendment from the spec is present in the right file. This is the executable equivalent of the spec's Acceptance Criteria.

- [ ] **Step 11.1: Verify all 7 amendments**

Run each grep below. Each must return `1` or higher (the matched line is shown for confirmation):

```bash
# #1: pipeline.csv cleanup added to action-plan.md
grep -n "head -1 docs/customer-discovery/pipeline.csv" docs/customer-discovery/action-plan.md

# #2: Audit Appendix added to phase-4-templates.md
grep -n "Audit Appendix" docs/customer-discovery/phase-4-templates.md

# #3: Stripe cancel reasons added to phase-3-prep.md
grep -n "Customer portal cancellation reasons" docs/customer-discovery/phase-3-prep.md

# #4: Override banner added to preorder-test.md
grep -n "v2 amendments live in" docs/customer-discovery/preorder-test.md

# #5: Day-3 capacity checkpoint added to action-plan.md
grep -n "Day-3 capacity checkpoint" docs/customer-discovery/action-plan.md

# #6: alt-ICP softened in BOTH action-plan.md and phase-4-templates.md
grep -cn "anecdote-quality" docs/customer-discovery/action-plan.md
grep -cn "anecdote-quality" docs/customer-discovery/phase-4-templates.md

# #7: throughput cap in BOTH action-plan.md and beta-deliverable.md
grep -n "Realistic Day-21→28 throughput" docs/customer-discovery/action-plan.md
grep -n "Exploratory Phase 5 throughput cap" docs/customer-discovery/beta-deliverable.md

# Pre-flight gates
grep -n "PF.8\|PF.9\|PF.10" docs/customer-discovery/action-plan.md
```

Expected: every grep returns at least one match. Pre-flight grep should return 3 matches.

- [ ] **Step 11.2: Verify commit count and content**

```bash
git log --oneline f085e0e2..HEAD
```

Expected: 5 commits, in this order (newest first):
- `docs(discovery): beta-deliverable.md — Day-35 exploratory throughput cap`
- `docs(discovery): phase-4-templates.md — Audit Appendix + alt-ICP softening`
- `docs(discovery): phase-3-prep.md — wire Stripe cancel-reason capture`
- `docs(discovery): preorder-test.md — override banner pointing to phase-3-prep`
- `docs(discovery): action-plan.md v2.1 — land 5 pressure-test v2 amendments`

(Plus `4c6b556e feat(retention)` if the stray retention commit is still on the branch.)

- [ ] **Step 11.3: Confirm file diff totals match expectations**

```bash
git diff f085e0e2..HEAD -- docs/customer-discovery/ --stat
```

Expected: 5 files changed. Total insertion count should be in the ~70-90 line range; deletion count ~15-20.

If any verification fails, revisit the relevant Task and re-run its post-check.

---

## Self-Review

After writing this plan, I checked it against the spec:

- **Spec coverage**: every finding (#1-#7) and every cross-cutting amendment (A, B, C) maps to at least one task. Acceptance criteria from the spec ("To land all 7 amendments, the following files must change... 5 files") matches Tasks 1-10 exactly.
- **Placeholder scan**: every Edit has literal `old_string` and `new_string` content. The one task that includes a "read for unique anchor" instruction is Task 8 — necessary because the audit-appendix insertion point is at the closing fence of an embedded code block, which is a more dynamic location than the other tasks. The instruction includes the exact insertion content.
- **Type consistency**: there are no types — these are doc edits. Cross-task consistency: "anecdote-quality" appears in both Task 3 (action-plan.md) and Task 9 (phase-4-templates.md) — checked via Step 11.1 grep across both files.
- **Scope**: 11 tasks, 5 commits, no new files. Single implementation cycle.

---

## Next steps after plan execution

1. The branch `feature/customer-discovery-pressure-test-v2` will contain:
   - Commit `d3728f95` (the v2 spec, already landed)
   - 5 new commits from this plan (Tasks 1-10)
   - Possibly the stray `4c6b556e feat(retention)` from the concurrent-process collision (the user can drop it via interactive rebase if undesired)
2. Open a PR to `main` with title: `docs(discovery): customer-discovery sprint v2.1 — pressure-test v2 amendments` and the v2 spec linked in the PR body.
3. Once merged, the customer-discovery sprint Pre-flight gates PF.8/PF.9/PF.10 become user-actionable items alongside PF.5/PF.6.
