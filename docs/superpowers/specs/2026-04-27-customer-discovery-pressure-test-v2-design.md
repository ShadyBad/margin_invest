# Customer Discovery Sprint — Pressure-Test v2 Findings

**Date**: 2026-04-27
**Status**: Draft (for-approval)
**Author**: Brainstorming session, post-prep-doc-review pressure-test of `action-plan.md` v2
**Related**:
- `docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-design.md` (v1 pressure-test, source for `action-plan.md` v2)
- `docs/customer-discovery/action-plan.md` (target document for amendments)
- `docs/customer-discovery/{icp,interview-guide,rubric,preorder-test}.md` (Phase 0, scope-locked)
- `docs/customer-discovery/{phase-1-prep,phase-3-prep,phase-4-templates}.md` (v2 overlay docs)
- `docs/customer-discovery/{beta-deliverable,recruitment-channel-rules,disqualified-log}.md` (pre-flight artifacts)

---

## Executive Summary

The v1 pressure-test produced 20 findings that were operationalized into `action-plan.md` v2 plus the `phase-N-prep` companion docs. After a complete read-through of the resulting artifact set, this v2 pressure-test surfaces **7 findings that slipped through the v1 → action-plan-v2 translation**. They cluster in three areas:

1. **PII protection has structural gaps** that defeat the Day-30 cleanup promise.
2. **Operational runtime gaps** — Stripe configs not wired, override-doc visibility unflagged, channel-volume math not stress-tested.
3. **Scope-promise calibration** — disqualified-log dependency is fragile; Day-21→28 exploratory window over-promises engineering throughput.

The plan is fundamentally sound. These are calibration adjustments to a working frame, not redesigns. All 7 amendments are additive or in-place edits — no new documents required.

### Top 3 must-do amendments

1. **PII cleanup script must zero `pipeline.csv` data rows** (#1) — without this, the handle ↔ first-name bridge survives Day +30, defeating the privacy guarantee that anonymization rules were designed to provide.
2. **`decision.md` must capture a pre-cleanup audit appendix** (#2) — fully de-identified aggregate evidence preserved before transcripts/scores are deleted, so the verdict's evidence trail isn't destroyed by the privacy procedure itself.
3. **Stripe Customer Portal must enable cancellation reasons** (#3) — without opt-in at portal config, the Day-51 retention investigation runs blind on the Stripe side.

### Severity counts

- **Critical** (3): #1, #2, #3
- **High** (4): #4, #5, #6, #7

---

## §1 PII & Audit Integrity

### #1 — `pipeline.csv` survives the cleanup procedure [Critical]

**Claim**: The `action-plan.md` v2 cleanup procedure is `rm -rf docs/customer-discovery/transcripts/ docs/customer-discovery/scores/; clear disqualified-log.md row data (keep header)`. It does NOT touch `pipeline.csv`. But `pipeline.csv` stores the real handle in column 1 alongside first-name-tied data rows, status, and `gift_paid_date`. The handle ↔ first-name bridge — exactly the PII the anonymization rules were designed to break — survives the cleanup indefinitely.

**Evidence**:
- `pipeline.csv` columns: `handle, source, url_to_post_that_qualified_them, why_qualified, dm_sent_date, response, scheduled_date, completed_date, gift_paid_date, status, notes`.
- `interview-guide.md` Anonymization Rules: "Real handle stays in `pipeline.csv` only."
- `action-plan.md` PII retention block: cleanup procedure does not include `pipeline.csv`.

**Amendment**: Extend the cleanup procedure with one of:

- (a) **Clear `pipeline.csv` data rows at Day +30, preserving column header only** — symmetrical with `disqualified-log.md` treatment.
- (b) Pre-cleanup, replace the `handle` column with hashed values (SHA-256 with random salt; salt destroyed after hashing) — preserves row-count auditability but breaks re-identification.
- (c) Document that `pipeline.csv` is intentionally retained for audit and adjust the anonymization promise accordingly.

**Recommend (a)** for symmetry and minimum complexity. The cleanup line in `action-plan.md` becomes: `rm -rf transcripts/ scores/; clear pipeline.csv and disqualified-log.md data rows (keep headers)`.

---

### #2 — `decision.md` citations become unverifiable post-cleanup [Critical]

**Claim**: The `phase-4-templates.md` `decision.md` skeleton cites rubric-bucket conversion rates, dominant objection patterns, anonymized transcript quotes, and per-prospect outcome tables. At Day +30 the source artifacts (`transcripts/`, `scores/`) are deleted. Post-cleanup, no one — including the founder later — can re-verify "did the rubric actually predict conversion?" or "what was the verbatim disinterest quote?" The privacy procedure destroys the evidence trail behind the GO/NO-GO verdict.

**Evidence**:
- `phase-4-templates.md` `decision.md` skeleton references:
  - Rubric-bucket conversion table (sourced from `scores/`)
  - Verbatim quote citations ("cite anonymized transcript quotes")
  - Per-prospect outcome table referencing `interview_#` (sourced from `transcripts/` filenames)
- `action-plan.md` cleanup procedure deletes `transcripts/` and `scores/` directories at Day +30.

**Amendment**: Insert a pre-cleanup audit-appendix step into the `decision.md` template:

> Before triggering Day +30 cleanup, append `## Audit Appendix (de-identified aggregate evidence — preserved post-cleanup)` to `decision.md` containing:
>
> - Rubric-bucket conversion table (duplicate from main body for permanence)
> - Objection-tag count distribution (counts only, no names)
> - 3-5 representative quotes per dominant objection tag, fully de-identified (no first names; `$TICKER_X` intact; dollar buckets intact)
> - Cohort sizes by source channel
> - Retention summary at Day 51 (cohort size, retained, churn reasons by Stripe-portal tag and founder follow-up tag)

`phase-4-templates.md` should explicitly say: **"Run the audit appendix BEFORE the cleanup script."**

This preserves the audit trail in a form that survives the privacy cleanup. The de-identified aggregate evidence is sufficient to defend the verdict to a co-founder, investor, or future-self review without resurrecting raw PII.

---

## §2 Operational Runtime Gaps

### #3 — Stripe Customer Portal cancellation-reason capture not enabled [Critical]

**Claim**: `action-plan.md` retention-gate prompt says "investigate churn reasons (cancellation reason via Stripe portal; optional follow-up email asking why)." Stripe Customer Portal collects cancellation reasons only if you opt in at portal config. `phase-3-prep.md` Stripe pre-go-live checklist enables the customer portal but does NOT include enabling cancellation reasons. The Day-51 retention investigation will run blind on the Stripe side, falling back to optional founder-side outreach (which has its own response-rate problem at retention).

**Evidence**:
- `action-plan.md` retention-gate prompt expects "cancellation reason via Stripe portal."
- `phase-3-prep.md` Customer Portal config bullet: "Customer portal: enabled for self-serve cancellation" — no mention of cancellation reasons.
- Stripe Dashboard: cancellation reasons are configured at Settings → Billing → Customer Portal → Cancellation reasons (off by default).

**Amendment**: Add a new bullet to the `phase-3-prep.md` Stripe pre-go-live checklist under "Checkout session configuration":

> - [ ] **Customer portal cancellation reasons**: enabled in Stripe Dashboard (Settings → Billing → Customer Portal → Cancellation reasons → Configure: include 4-6 reason options + optional comment field). Reasons should map to objection tags:
>   - `delivery-risk` → "Wasn't ready when expected"
>   - `price-objection` → "Too expensive"
>   - `feature-gap` → "Missing key feature"
>   - `disinterest` → "Didn't fit my needs"
>   - other (free-text comment)

This wires the Day-51 retention investigation to actual Stripe-collected churn signals, mirroring the objection-tag schema used in Phase 3.

---

### #4 — Two-source-of-truth runtime visibility risk [High]

**Claim**: `action-plan.md` v2 declares `preorder-test.md` "scope-locked, do not modify" and amends thresholds in `phase-3-prep.md` instead. At Phase 3 runtime (Day 21, founder under deadline pressure), reading only `preorder-test.md` produces wrong-threshold execution. There is no in-document override banner pointing the reader to the prep doc.

**Evidence**:
- `preorder-test.md` Go/No-Go section: "GO (5+ of 10 paid)... NO-GO (2 or fewer of 10 paid)."
- `phase-3-prep.md` v2 threshold override block: "GO = ≥4/10... NO-GO = ≤1/10 OR ≥60% disinterest."
- `action-plan.md` Phase 0 block: "[preorder-test.md is] scope-locked, do not modify."
- Nothing in `preorder-test.md` itself flags the override.

**Amendment**: Add an additions-only "Override Banner" at the top of `preorder-test.md` (top of file, before Overview):

> **v2 amendments live in `phase-3-prep.md`. Read `phase-3-prep.md` BEFORE running Phase 3 — thresholds, ask-cohort rules (Option A vs B), and price-arm rules are amended there. The body of this document is preserved as the scope-locked Phase 0 reference and is OVERRIDDEN where it conflicts with `phase-3-prep.md`.**

The additions-only constraint is preserved (no body edits, just a banner). The runtime risk is mitigated because anyone reading `preorder-test.md` is forced to see the pointer before reaching the scope-locked content. `interview-guide.md` already uses this pattern (consent script, anonymization rules, gift payout rule were added at the top under section headers).

---

### #5 — Day-7 yield gate vs channel volume math [High]

**Claim**: `action-plan.md` Phase 1 expects 8 scheduled calls by Day 7 (Day-7 yield gate). At ~18% DM-to-scheduled conversion, this requires ~44 personalized DMs in the first 7 days. `recruitment-channel-rules.md` caps Reddit at 5 DMs/day = 35 DMs maximum across 7 days. Twitter caps at 10/day but requires 7-14 day account warm-up before DMing, often consuming most of the first week. The math forces a Day-7 fail purely on volume capacity, not on market interest. A founder hits the gate, picks remediation (b) or (c), and may rescope to HALF when the actual problem is bandwidth, not demand.

**Evidence**:
- `action-plan.md` Phase 1 yield gate: "If <8 scheduled: pause and choose..."
- `recruitment-channel-rules.md` Reddit volume cap: "≤5 DMs per day per account. ≤25 per week."
- `recruitment-channel-rules.md` Twitter requirement: "Build context. Follow the prospect for 7-14 days before DMing."
- Math: 8 scheduled at 18% conversion ≈ 44 DMs sent → exceeds 7-day Reddit cap (35) and exceeds Twitter's pre-warmup window for cold DMs.

**Amendment**: Add a Day-3 capacity checkpoint to Phase 1 that audits *send capacity* before Day-7 evaluates *response yield*:

> **Day-3 capacity checkpoint**: count personalized DMs sent so far. Target: 15+ DMs across all active channels by Day 3.
> - **If <15 DMs sent**: bottleneck is volume, not yield. Solutions: open additional channels (Substack comment-section outreach, Discord with mod permission), accept that the original 18-scheduled-by-Day-21 trajectory may need a different ratio, OR consider whether the channels-rules constraints make FULL scope unreachable.
> - **If 15+ DMs sent and yield is poor (<3 responses)**: bottleneck is conversion. Day-7 gate logic applies — the existing remediation menu (a)/(b)/(c) is appropriate.

This separates "we can't send enough" from "what we sent isn't landing." Both demand different fixes; the Day-7 gate as currently written conflates them.

---

## §3 Scope & Promise Calibration

### #6 — `disqualified-log.md` → NO-GO pivot data fragility [High]

**Claim**: `action-plan.md` Phase 4 NO-GO branch reads `disqualified-log.md` to identify "top 3 alternative ICPs" for pivot brainstorming. The log is populated only when a disqualified prospect (1) consents to the 5-min probe pivot AFTER being told they don't qualify, AND (2) actually answers the 3-question probe with substance. Realistic yield from 15 interviews where the goal is qualified prospects: 0-3 disqualified-and-probed entries. "Top 3 alternative ICPs" as written assumes data that may not exist. A founder hitting NO-GO with an empty log has nowhere to pivot.

**Evidence**:
- `action-plan.md` Phase 4 NO-GO branch step 4: "Read back top 3 alternative ICPs from `docs/customer-discovery/disqualified-log.md` (the 5-min probe data)."
- `interview-guide.md` 5-min probe: requires prospect consent after disqualifier-fail, plus willingness to answer 3 questions.
- Pre-flight assumes prospects are pre-qualified before scheduling — most disqualifiers fire during the disqualifier-check at minute 3 of the call. Of those, many will end the call rather than continue to a probe.
- Realistic disqualifier fire rate: ~15-30% of qualified-looking prospects turn out to be Mark-shaped from posts but not Mark behaviorally → 2-5 disqualified calls in 18 scheduled. Of those, probe-completion rate is maybe 50-70%.
- Net log yield: **1-3 entries, often 0**.

**Amendment**: Soften the Phase 4 NO-GO branch language. Replace "top 3 alternative ICPs" with:

> Read back the `disqualified-log.md` probe data. With 1-3 entries this is anecdote-quality, not data. Treat as raw input for a fresh `/superpowers:brainstorming` session on alternative ICPs — do NOT skip the brainstorm and treat the log as a finished pivot recommendation.
>
> If the log has 0 entries: the NO-GO branch defaults to a fresh brainstorm without alt-ICP scaffolding. The absence of pivot data is itself a finding ("we could not even gather alternative-ICP signal during this sprint, so the next sprint must explicitly recruit for that data").

This sets correct expectations for what the log can and cannot deliver.

---

### #7 — Day-21→28 exploratory engineering window over-promises [High]

**Claim**: `action-plan.md` exploratory Phase 5 (Days 21-28, after charge-gate GO) is described as "1 week of scoped roadmap work." `beta-deliverable.md` Day-35 deliverable is "platform as it exists today (2026-04-27) plus any exploratory Phase 5 work (Days 21-28) committed before launch."

In a 35K-LOC codebase with strict TDD (engine ≥95% coverage, api ≥90%), sector-neutral scoring tests, ML approval gates, and circuit-breaker governance — 7 days for any non-trivial feature is aspirational. The doc reads like a feature ships at Day 28 ready for Day 35 launch. Reality: Day-28 scope is "design + scaffold + maybe a UI surface," not "feature live in beta."

**Evidence**:
- `action-plan.md` exploratory Phase 5 prompt: "Use /flow:triage to translate the top three feature priorities... route to /flow:plan if complexity warrants or /flow:execute if MICRO."
- `CLAUDE.md` TDD requirement: "Write failing test first, then implement. No scoring formula ships without a golden-value test."
- `CLAUDE.md` governance: "scores and ML models require approval" via "staged → approved → published pipeline."
- Recent feature-ship cadence in git log: features land in 5-15 days from triage to merge for moderate-complexity work; risk-diffing pipeline was multi-week.

**Amendment**: Tighten `beta-deliverable.md` Day-35 deliverable language and align `action-plan.md` exploratory Phase 5 expectations:

- `beta-deliverable.md` Included section gets an appended note:

  > **Exploratory Phase 5 throughput cap (Days 21-28)**: at most one MICRO change — a small UI surface, a bug-fix, or a minor data-wiring change — may land in time for Day 35. Larger features (new scoring factors, ML changes, new pages) will NOT ship in the founder-beta scope; they land post-retention-gate (Day 51+) under committed Phase 5.

- `action-plan.md` exploratory Phase 5 prompt gets an appended note:

  > Realistic Day-21→28 throughput in this codebase: design + scaffold + at most one MICRO change merged. Anything classified STANDARD or larger by `/flow:triage` is queued for committed Phase 5 (Day 51+), not promised in the founder beta.

This sets honest expectations with the customer (who consents to scope via `beta-deliverable.md`) and prevents the founder from over-promising at Day 21 only to under-deliver at Day 35.

---

## Cross-cutting amendments

### Amendment block A — Cleanup script v2

`action-plan.md` "PII retention policy" section gets a revised cleanup procedure (resolves #1 and chains with #2):

> **Cleanup procedure** (run AFTER `decision.md` audit appendix is appended; see Amendment block B):
>
> ```bash
> # 1. Delete transcripts and scorecards
> rm -rf docs/customer-discovery/transcripts/
> rm -rf docs/customer-discovery/scores/
>
> # 2. Clear pipeline.csv data rows (preserve header)
> head -1 docs/customer-discovery/pipeline.csv > /tmp/pipeline_header.csv
> mv /tmp/pipeline_header.csv docs/customer-discovery/pipeline.csv
>
> # 3. Manually clear data rows under the "## Log" table in disqualified-log.md
> #    Keep all markdown structure and column headers; remove only data rows.
> ```
>
> Then commit: `docs(discovery): post-decision PII cleanup (Day +30)`.

### Amendment block B — Audit appendix template

`phase-4-templates.md` `decision.md` skeleton gets a new mandatory section to be filled BEFORE cleanup (resolves #2):

> ## Audit Appendix (de-identified aggregate evidence — preserved post-cleanup)
>
> *Run before triggering the Day +30 cleanup. Once cleanup runs, the source artifacts (transcripts, scores) are deleted; this appendix is the durable evidence trail.*
>
> ### Rubric-bucket conversion (Option B only)
> [Duplicate the rubric-bucket conversion table from main body for permanence.]
>
> ### Objection-tag distribution
> | tag | count | % of non-payment |
> |---|---|---|
> | delivery-risk | | |
> | price-objection | | |
> | feature-gap | | |
> | disinterest | | |
>
> ### Representative quotes per dominant objection tag
> 3-5 quotes per tag, fully de-identified (`$TICKER_X` intact, dollar buckets intact, no first names).
>
> ### Cohort sizes by source channel
> | source | recruited | scheduled | completed | strong | paid | retained_d51 |
> |---|---|---|---|---|---|---|
> | Reddit | | | | | | |
> | Twitter | | | | | | |
> | Substack | | | | | | |
>
> ### Retention summary (Day 51)
> - Charge cohort size: [N]
> - Retained at Day 51: [N] ([X]%)
> - Churn reasons by Stripe-portal tag: [counts]
> - Churn reasons by founder follow-up email: [counts]

### Amendment block C — Pre-flight v2 additions

`action-plan.md` Pre-flight checklist gets three new gate items (resolves #3, #4, #5):

- ☐ **PF.8 Stripe Customer Portal cancellation reasons enabled**: configured in Stripe Dashboard with reason options mapped to objection tags. Capture screenshot or config-export reference in `phase-3-prep.md`.
- ☐ **PF.9 `preorder-test.md` override banner inserted**: additions-only banner at top of `preorder-test.md` pointing to `phase-3-prep.md`. (Delete this gate item once the banner is committed.)
- ☐ **PF.10 Day-3 capacity checkpoint defined**: `action-plan.md` Phase 1 prompt amended to include the Day-3 send-capacity check separately from the Day-7 yield evaluation.

---

## Acceptance criteria for `action-plan.md` v2.1

To land all 7 amendments, the following files must change:

1. **`docs/customer-discovery/action-plan.md`**
   - PII retention block: extend cleanup procedure (Amendment A → #1)
   - Phase 1 prompt: insert Day-3 capacity checkpoint (#5)
   - Phase 4 NO-GO branch language: soften "top 3 alternative ICPs" (#6)
   - Phase 5 exploratory prompt: tighten throughput expectations (#7)
   - Pre-flight checklist: add PF.8 / PF.9 / PF.10 (Amendment C)

2. **`docs/customer-discovery/preorder-test.md`**
   - Top-of-file additions-only override banner pointing to `phase-3-prep.md` (#4)

3. **`docs/customer-discovery/phase-3-prep.md`**
   - Stripe pre-go-live checklist: add cancellation-reasons bullet (#3)

4. **`docs/customer-discovery/phase-4-templates.md`**
   - `decision.md` skeleton: add Audit Appendix section (Amendment B → #2)
   - NO-GO branch template: soften alt-ICP language to match `action-plan.md` change (#6)

5. **`docs/customer-discovery/beta-deliverable.md`**
   - Day-35 deliverable Included section: append exploratory Phase 5 throughput cap (#7)

No new documents required. All amendments are additive or in-place edits to existing artifacts. Phase 0 docs (`icp.md`, `interview-guide.md`, `rubric.md`, `preorder-test.md`) are touched only via additions-only patterns already established in v1.

---

## What this spec does NOT cover

- v1 pressure-test findings (already operationalized in v1 spec → action-plan v2)
- Phase 0 doc body edits (Phase 0 body remains scope-locked; only additions-only banners and headers used)
- Sprint scope-tier change (FULL stays FULL unless founder-hour budget renegotiates separately)
- Implementation order — see `/superpowers:writing-plans` output for sequencing
- Verification steps — operational checklist lives in `action-plan.md` after amendments land
