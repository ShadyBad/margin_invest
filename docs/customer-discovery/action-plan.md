# Margin Invest — Customer Discovery Action Plan v2

**Version**: 2.0 (pressure-tested 2026-04-27)
**Source spec**: [docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-design.md](../superpowers/specs/2026-04-27-customer-discovery-pressure-test-design.md)

**Scope tier (committed 2026-04-27)**: **FULL** — 15 interviews / 10 paid asks / 100+ pipeline target. Founder-hour budget: 40-60 hours over 21 days; minimum 30 hours. Calendar pre-block target: 18 slots.

**PII retention policy (committed 2026-04-27)**: **Option A** — delete all transcripts, scorecards, and disqualified-log entries 30 days after `decision.md` is committed. Cleanup procedure: `rm -rf docs/customer-discovery/transcripts/ docs/customer-discovery/scores/`; clear disqualified-log.md row data (keep header); commit a "post-decision PII cleanup" marker.

**Pre-flight status (2026-04-27)**: Artifacts complete. User gates pending — Phase 1 does NOT launch until PF.5 and PF.6 are checked off below.

Artifacts (agent-completed, committed):
- ✓ `beta-deliverable.md` (PF.1)
- ✓ `recruitment-channel-rules.md` (PF.2)
- ✓ `interview-guide.md` amendments (PF.3 — consent, anonymization, gift, probe)
- ✓ `disqualified-log.md` scaffold (PF.4)
- ✓ Scope tier (FULL) and PII retention policy (Option A) committed (Task 0.2 + PF.7, leading notes above)

Pending user gates (must complete before Phase 1 launches):
- ☐ **PF.5 Calendar pre-block**: 18 specific 45-min slots over 21 days. Suggested distribution: 4 slots Days 4-7, 8 slots Days 8-14, 6 slots Days 15-21. Each slot needs no engineering conflict, quiet location, working audio. Title each "INTERVIEW SLOT (placeholder)."
- ☐ **PF.6 Founder-hour commitment**: ≥30 hours blocked over 21 days; realistic estimate 42 hours. List specific blocks (e.g., "weekday evenings 7-9pm + Saturday mornings 9-12").

When PF.5 and PF.6 are complete: replace ☐ with ✓ above, commit with message `docs(discovery): pre-flight gates passed — ready for Phase 1`, then launch Phase 1 by pasting the Phase 1 prompt block from this file into a fresh Claude Code session.

If you cannot complete PF.5 or PF.6: rescope this sprint to HALF (8 interviews / 5 paid asks / ≥18 hours / 10 calendar slots) by editing the leading "Scope tier" note above before launching Phase 1.

> **Changes from v1**: amended thresholds, two-gate GO structure (charge + retention), consent/anonymization protocol, Day-35 deliverable doc requirement, refund-on-NO-GO procedure, realistic founder-hour budget, Day-7 yield gate, new pre-flight phase. See source spec for evidence behind each change.

---

## Objective, signals, deadlines (amended)

**Objective**: prove or disprove that a Spectrum Mark customer will pay $49+/month for Margin Invest, using Claude Code as the execution partner.

**Decision deadlines** (two-gate):

- **Charge gate**: 21 days from kickoff.
- **Retention gate**: 51 days from kickoff (30 days post-charge).

**Signals**:

| Outcome | Charge gate (Day 21) | Retention gate (Day 51) |
|---|---|---|
| **GO (committed)** | ≥4/10 paid AND dominant objection ≠ disinterest | ≥80% of charge-gate cohort retained through second billing cycle |
| **SOFT GO** | 2-3/10 paid | 60-79% retained — investigate churn |
| **NO-GO** | ≤1/10 paid OR ≥60% disinterest | ≤40% retained — demote to NO-GO |

Retention gate operational gloss: for charge-gate cohorts of 4-9 paid, lose ≤1 customer; for cohorts of 10+, lose ≤2.

**Charge-gate GO** unlocks *exploratory* Phase 5 only (1 week, scoped roadmap work). **Retention-gate GO** ratifies the GO and starts *committed* 90-day Phase 5.

**Founder-hour budget**: 40-60 hours over 51 days. **If you cannot block 30+ hours over the first 21 days, scope to 8 interviews / 5 paid asks instead of 15/10.**

---

## How to use this document

Each phase is a **self-contained Claude Code prompt**. Copy the block between the `===PROMPT===` fences into a fresh Claude Code session. The prompts explicitly invoke Superpowers skills so the harness drives the workflow.

The phases are gated — **do not advance to phase N+1 until the acceptance criteria for phase N are satisfied.** Gates are listed under each phase.

Artifacts live under `docs/customer-discovery/` so they're version-controlled alongside code decisions they'll influence.

**New artifacts required before Phase 1 launches**:

- `docs/customer-discovery/beta-deliverable.md` — Day-35 product scope
- `docs/customer-discovery/recruitment-channel-rules.md` — per-channel compliance
- `docs/customer-discovery/disqualified-log.md` — scaffolded for Phase 2

---

## Phase 0 — Kickoff & Scope Lock (locked, do not modify)

The four Phase 0 artifacts are scope-locked and committed:

- `docs/customer-discovery/icp.md`
- `docs/customer-discovery/interview-guide.md`
- `docs/customer-discovery/rubric.md`
- `docs/customer-discovery/preorder-test.md`

Phase 0 amendments from v2 land in Pre-flight (additions only — no rewrites of existing language).

---

## Pre-flight — Feasibility & Compliance Gates (NEW)

**Purpose**: ensure the sprint is feasible before you start spending founder-hours and prospect goodwill.

**Acceptance criteria**:

- 18 calendar slots pre-blocked over the next 21 days
- `docs/customer-discovery/beta-deliverable.md` committed (Day-35 product scope)
- `docs/customer-discovery/recruitment-channel-rules.md` committed (per-channel compliance)
- Founder-hour commitment: ≥30 hours blocked, OR sprint rescoped to 8/5
- Anonymization rules added to `interview-guide.md` (consent script, ticker pseudonyms, dollar buckets)
- $50 gift payout rule added to `interview-guide.md` (paid only after qualified completion OR disqualified-but-probed)
- `docs/customer-discovery/disqualified-log.md` scaffolded

### Prompt

```
===PROMPT===
Pre-flight for the Margin Invest customer discovery sprint. Do not advance to
Phase 1 until all gates pass.

Use /superpowers:writing-plans to produce these artifacts:

1. docs/customer-discovery/beta-deliverable.md
   - What does a paid customer get on Day 35?
   - Specific features, auth flow, ticker coverage, pages live
   - Explicit NOT-INCLUDED list
   - This file gets linked from the Stripe ask so the customer consents to scope

2. docs/customer-discovery/recruitment-channel-rules.md
   - Per-channel compliance findings (Reddit, Twitter/X, Substack, Discord)
   - ToS / wiki links per channel
   - Adjusted tactics: where DMs are OK, where comments-on-posts are required,
     where the $50 gift must be dropped
   - Account-history requirements per channel (no fresh accounts on Twitter)

3. Update docs/customer-discovery/interview-guide.md to add (additions only —
   do not rewrite existing scope-locked language):
   - Verbal consent script in the opening, before 5 questions, before
     disqualifier check: "I take notes that I store in a private code
     repository. I'll use a first name only and won't store your handle or
     specific holdings — is that OK?" Get verbal yes before the 5 questions.
   - Anonymization rules: first name only; tickers → $TICKER_A, $TICKER_B;
     dollar amounts → buckets ($1-5K, $5-20K, $20-100K, $100K+); AUM bucketed
     similarly; brokerages kept generic.
   - $50 gift payout rule: gift paid only after a qualified-and-completed call
     (disqualifier passed, ≥25 min, preorder ask delivered if eligible) OR a
     disqualified-but-probed call (5-min tools/wishes probe completed). State
     the rule in the recruitment DM AND in the interview opening.
   - 5-min disqualified-prospect probe: if disqualifier check fails, ask
     "What tools do you use, what do you wish existed?" Capture in
     disqualified-log.md.

4. Scaffold docs/customer-discovery/disqualified-log.md with column headers:
   date, source, why_disqualified, tools_used, wishes_for_existing_tools.

5. Confirm calendar capacity:
   - List your 18 pre-blocked 45-min interview slots over the next 21 days.
   - If you can't block 18, output: "INFEASIBLE — rescope to 8 interviews."

6. Confirm founder-hour budget:
   - List your 30+ blocked hours across the 21 days.
   - If <30 hours available, output: "INFEASIBLE — rescope to 8 interviews /
     5 paid asks."

7. Decide PII retention policy now:
   - Option A: delete transcripts 30 days after decision.md commits
   - Option B: move transcripts to encrypted local storage post-decision
   - Document choice in beta-deliverable.md or a new retention.md

Do not write product code. This phase is artifacts + scheduling only.
===PROMPT===
```

**Gate to Phase 1**: all seven items above complete; calendar and founder-hours confirmed; no INFEASIBLE flags.

---

## Phase 1 — Recruit Marks (amended)

**Purpose**: source real humans matching the ICP. Updated targets and yield gate.

**Acceptance criteria** (amended):

- `docs/customer-discovery/pipeline.csv` — **100+ qualified prospects** with source, handle, why-they-match
- **18 scheduled** 30-minute Zoom calls (target 15 completed)
- Zero prospects recruited via existing network
- Day-7 yield checkpoint passed

### Prompt

```
===PROMPT===
Using the ICP in docs/customer-discovery/icp.md and the channel rules in
docs/customer-discovery/recruitment-channel-rules.md, help me build a prospect
pipeline of 100+ qualified Marks, of whom I will schedule 18 interviews to land
15 completed.

Use /superpowers:executing-plans to drive this phase. Treat it as a structured
execution with checkpoints — stop after each batch of 10 prospects for my
review before continuing.

Pipeline math (amended from v1):
- 100+ qualified prospects in pipeline.csv
- 18 scheduled calls (assumes ~18% DM-to-scheduled conversion)
- 15 completed interviews (assumes ~83% schedule-to-complete conversion)
- Adjust upward if Day-7 yields are below trajectory

For each recruitment source in icp.md:

1. Generate 5-10 search queries I can run manually. Be specific — e.g.,
   "r/SecurityAnalysis top posters last 90 days with ≥3 posts mentioning
   Beneish, accruals, or ROIC."

2. Respect channel rules from recruitment-channel-rules.md — if a channel
   forbids paid outreach, draft DMs without the $50 gift offer for that
   channel.

3. For each prospect I surface and paste, draft a personalized DM (≤4 sentences)
   that:
   - References something specific they posted (not generic)
   - Asks for a 30-min call about how they research stocks
   - Does NOT mention Margin Invest, does NOT describe a product
   - Offers $50 thank-you for a qualified-and-completed call (paid AFTER —
     state explicitly so the prospect knows the rule)

4. Maintain pipeline.csv with columns:
   handle, source, url_to_post_that_qualified_them, why_qualified,
   dm_sent_date, response, scheduled_date, completed_date, gift_paid_date,
   status, notes

Day-7 yield gate (NEW):
- After 7 days of recruitment, count scheduled calls.
- If ≥8 scheduled: continue as planned.
- If <8 scheduled: pause and choose:
  (a) Expand channels (Twitter Lists, paid Discord servers, Substack
      comments on Bearcave/Hindenburg/Kerrisdale)
  (b) Raise gift to $75-100 and re-DM cold prospects with the bump
  (c) Accept reality and rescope sprint to 8 interviews / 5 paid asks
- Document the choice in pipeline.csv notes column. Do not just send harder.

Rules:
- Never recruit from existing network — bias risk.
- Flag prospects I paste who fail disqualifiers — tell me why to skip.
- Stop after each batch of 10 and ask if I want to continue — quality over
  speed.

What I do: run the searches you generate, paste prospect profiles back, send
the DMs you draft, schedule calls.

Start with the highest-yield source from icp.md.
===PROMPT===
```

**Gate to Phase 2**: 18 calls scheduled, pipeline.csv populated to 100+, zero network hires, Day-7 gate passed (or explicit rescope documented).

---

## Phase 2 — Run Interviews (amended)

**Purpose**: execute interviews cleanly without leading the witness or pitching. Anonymize PII as you capture.

**Acceptance criteria** (amended):

- 15 completed interviews (≥25 min each)
- 15 anonymized transcripts at `docs/customer-discovery/transcripts/NN-firstname.md`
- 15 scorecards at `docs/customer-discovery/scores/NN-firstname.md`
- Disqualified-prospect log populated for any disqualified-but-probed calls

### Prompt (run once per interview day)

```
===PROMPT===
I am about to run interview #[N] with [firstname] in [X] minutes. They were
recruited from [source] because [why_qualified from pipeline.csv].

Use /superpowers:executing-plans to prep me for this one call.

Do these four things:

1. Read docs/customer-discovery/interview-guide.md and remind me of the five
   questions verbatim AND the verbal consent script. I'll keep them on-screen
   during the call.

2. Generate a per-interview note template at
   docs/customer-discovery/transcripts/[NN]-[firstname].md with:
   - Header: date, source, qualification reason
   - Consent acknowledgment (verbal yes captured before questions)
   - Disqualifier checklist at the top (skip the five questions if any fire,
     run the 5-min probe instead)
   - Five question blocks with space for verbatim quotes and "tell me more"
     follow-up prompts
   - Closing-ask section (only if qualified): preorder wording from
     preorder-test.md, outcome, amount
   - Red-flag section: any moment I caught myself leading or pitching

3. Anonymization rules apply at capture time (do NOT clean up later):
   - First name only in transcript filename and content
   - Tickers: $TICKER_A, $TICKER_B, ... (assigned in order of mention)
   - Dollar amounts: bucket as ($1-5K), ($5-20K), ($20-100K), ($100K+)
   - AUM: bucket the same way
   - Brokerage names: keep generic ("major retail brokerage", "specialty broker")
   - Real handle stays in pipeline.csv only

4. Three-bullet pre-call reminder of Mom Test rules — what I must NOT do.
   Anti-pattern reminder: "Do not anchor [firstname]'s answers with what
   prior prospects said. Each interview starts blank."

After the call, I'll paste the verbatim notes (already anonymized) back into
this chat. Then use /superpowers:verification-before-completion to score the
transcript against docs/customer-discovery/rubric.md and write
docs/customer-discovery/scores/[NN]-[firstname].md.

Scoring must be evidence-based — every signal marked "strong" must quote the
prospect's exact words. If I do not have a quote, the signal is not strong.

If the disqualifier check fails:
- End the 5-question portion. Run the 5-min probe (tools used, wishes for
  existing tools). Capture in disqualified-log.md.
- Mark them in pipeline.csv as disqualified-but-probed.
- Pay the $50 gift (kept-promise rule).

If the prospect declines consent:
- End the call politely without proceeding.
- Mark in pipeline.csv as "consent declined." NO gift.

Gift payout tracking:
- After qualified-and-completed call: pay $50, mark gift_paid_date
- After disqualified-but-probed call: pay $50, mark gift_paid_date
- After early-termination (consent declined, ghosted, <25 min): NO gift,
  note reason in pipeline.csv
===PROMPT===
```

**Gate to Phase 3**: 15 anonymized transcripts + 15 scorecards exist. Disqualified-log captures any disqualified-but-probed calls. Any interview <20 min is discarded and replaced.

---

## Phase 3 — Paid Preorder Test (amended)

**Purpose**: convert interview qualification into paid Stripe subscriptions. Charge gate at Day 21.

**Acceptance criteria** (amended):

- Stripe Checkout live for "Margin Invest Founder Beta — $49, access in 14 days, cancel anytime, scope per `beta-deliverable.md`"
- 10 (or 15) pre-order asks sent
- 7+ responses logged
- **Charge-gate decision rule**: ≥4/10 paid → unlock exploratory Phase 5; ≤1/10 paid → NO-GO; 2-3/10 → SOFT GO

### Prompt

```
===PROMPT===
I completed 15 interviews. Anonymized scorecards in
docs/customer-discovery/scores/.

Use /superpowers:writing-plans then /superpowers:executing-plans to run the
paid preorder phase.

Step 1 — Identify the ask cohort:

   OPTION A (default): Identify top 10 strong-signal prospects (≥4/6 rubric).
   OPTION B (rubric-validation, RECOMMENDED if you can afford ~2 hr extra):
   Send the ask to ALL 15 interviewed prospects. Validates rubric vs paid
   conversion as the primary signal is collected.

   Output a ranked table; rank by composite signal strength, breaking ties by
   dollar-loss specificity and existing tool spend.

Step 2 — Set up Stripe Checkout:

   Walk me through creating a Stripe product + Checkout session for
   "Margin Invest Founder Beta" — $49/month subscription, trial = 0 days,
   charged today, first beta access in 14 days, cancel anytime from a
   self-serve portal. Use /stripe:stripe-best-practices.

   The Checkout MUST:
   - Collect email (for beta access delivery)
   - Work for buyers without a Stripe account
   - Link docs/customer-discovery/beta-deliverable.md so the customer consents
     to specific scope, not a vibe

Step 3 — Send the asks:

   For each prospect, draft a personalized follow-up referencing something
   specific from their interview (anonymized — quote their words, but if
   quoting a ticker swap to $TICKER_A). End with the preorder ask from
   preorder-test.md and the Stripe link.

   Maintain docs/customer-discovery/preorder-test-results.md with columns:
   prospect, ask_sent_date, response_date, outcome (paid / declined /
   no_response / objection), amount, objection_tag, objection_notes

Step 4 — Handle objections; tag every objection (NEW):

   Tag each non-payment with one of:
   - delivery-risk: would buy a working product
   - price-objection: $49 is too high
   - feature-gap: would buy if X existed
   - disinterest: don't have the problem

   Price objection: do NOT discount. Ask: "What number would feel like a
   no-brainer to you?" Capture answer.

   Timing/delivery objection: gently push: "What specifically would you need
   to see in the first beta for it to be worth $49?" Tag as feature-gap if
   they answer specifics, delivery-risk if generic.

Step 5 — Optional 2-arm price test (NEW):

   If running OPTION B above (15 asks): split 7 prospects asked at $49 / 8 at
   $29 (or $39). Track conversion per arm in preorder-test-results.md.

   If running OPTION A (10 asks): single price, accept the elasticity blind
   spot. Pre-commit a Phase 4 conclusion: "I will assume $49 is correct
   unless retention drops below X."

Step 6 — Optional rapport-vs-cold split (NEW):

   If statistical curiosity allows: 7 prospects get rapport-driven personalized
   follow-up; 3 get clean cold-template ask referencing only the public Stripe
   page. Compare conversion rates. Footnote in decision.md as a calibration
   finding (not a reason to halt).

Charge-gate decision rule (amended):
   - ≥4/10 paid (or ≥6/15) AND dominant objection ≠ disinterest →
     CHARGE GATE PASSED → proceed to exploratory Phase 5 (1 week scoped
     roadmap work). Phase 4 retention gate at Day 51 ratifies the GO.
   - 2-3/10 paid → SOFT GO. Tighten ICP, raise price, or re-ask.
   - ≤1/10 paid OR ≥60% disinterest → NO-GO. Refund any paid customers,
     then commit FROZEN.md.

Do not move to Phase 4 until 10 (or 15) asks sent AND 7+ responses logged.
===PROMPT===
```

**Gate to Phase 4 charge-gate evaluation**: ≥10 asks sent, ≥7 responses, decision rule data complete.

---

## Phase 4 — Go / No-Go Decision (amended, two-gate)

**Purpose**: make a binding decision with two-gate structure and refund-first-on-NO-GO.

**Acceptance criteria** (amended):

- `docs/customer-discovery/decision.md` committed with verdict + evidence trail
- If NO-GO: refunds issued **BEFORE** `FROZEN.md` commit
- If charge-gate GO: commitment held until retention gate (Day 51); exploratory Phase 5 unlocked

### Prompt — Charge gate (Day 21)

```
===PROMPT===
Phase 3 is complete. Preorder results in
docs/customer-discovery/preorder-test-results.md.

Use /superpowers:verification-before-completion to produce the charge-gate
decision. Evidence before assertions — every claim cites a specific transcript
quote or ledger entry.

Step 1 — Compute charge-gate outcome:
   1. Raw numbers: asks sent, responses, paid count, total $ collected,
      conversion rate. No spin.
   2. Objection-pattern analysis: count by tag (delivery-risk, price,
      feature-gap, disinterest). Surface dominant pattern.
   3. Verdict (charge gate):
      a) GO (charge): ≥4/10 paid AND dominant objection ≠ disinterest
         → unlock exploratory Phase 5. Schedule retention gate at Day 51.
      b) SOFT GO: 2-3/10 paid → tighten ICP further OR raise price and re-ask
         paid customers. Re-evaluate at Day 51.
      c) NO-GO: ≤1/10 paid OR ≥60% disinterest → halt feature work,
         refund-then-freeze (Step 2).

Step 2 — If NO-GO: REFUND BEFORE FREEZE (NEW):
   1. Issue Stripe refund within 48 hours of decision for every paid customer.
      Confirm refund in Stripe dashboard.
   2. Send personalized email to each paid customer:
      - Name the decision honestly
      - Thank them for their bet
      - Confirm refund issued, with refund timing
      - Optionally: offer to keep them informed if I pivot to a different
        product
   3. ONLY THEN draft FROZEN.md at repo root: "Feature work paused 2026-XX-XX
      pending new customer discovery. See docs/customer-discovery/decision.md."
   4. Read back top 3 alternative ICPs from
      docs/customer-discovery/disqualified-log.md (the 5-min probe data) —
      these are candidate pivots.
   5. Open fresh /superpowers:brainstorming on those.

Step 3 — If charge-gate GO: schedule retention gate:
   - Day 51 retention check: ≥4/5 retained through second billing cycle?
   - Add a calendar event for Day 51 to run the retention-gate prompt below.

Step 4 — decision.md content (charge-gate section):
   - Raw numbers
   - Verdict
   - What I learned about the product (cite quotes)
   - What I learned about my bias as a builder
   - Rubric validity (if Option B was run): conversion rate by rubric bucket
   - Price elasticity (if 2-arm test was run): conversion at $49 vs $29
   - Rapport-vs-cold conversion (if split was run): footnote calibration
   - Next step: exploratory Phase 5 (GO), retention monitoring (SOFT GO),
     or FROZEN (NO-GO)

If charge-gate NO-GO and refunds issued: do NOT proceed to retention gate.
===PROMPT===
```

### Prompt — Retention gate (Day 51)

```
===PROMPT===
30 days have passed since charge gate. Time for the retention gate.

Use /superpowers:verification-before-completion.

Step 1 — Count retained customers:
   - Pull Stripe subscription status for all charge-gate paid customers.
   - Count: how many retained through second billing cycle?

Step 2 — Verdict (retention gate):
   Compute retention rate = retained / charge-gate cohort.
   - GO (committed): ≥80% retained → ratify charge-gate GO. Start committed
     90-day Phase 5. (Operational: lose ≤1 for cohorts of 4-9; lose ≤2 for
     cohorts of 10+.)
   - SOFT GO: 60-79% retained → hold. Investigate churn reasons (cancellation
     reason via Stripe portal; optional follow-up email asking why). Decide
     within 1 week: continue committed Phase 5, scope down, or demote to
     NO-GO.
   - NO-GO (demoted): ≤40% retained → demote charge-gate GO to NO-GO.
     Refund remaining holdouts gracefully, commit FROZEN.md.

Step 3 — Append to decision.md:
   - Retention numbers
   - Churn reasons (if available)
   - Final verdict
   - 90-day commitment (committed GO) or formal pause (demoted NO-GO)
===PROMPT===
```

**Gate to Phase 5 (committed)**: retention-gate GO. (Charge-gate GO unlocks only the *exploratory* first week of Phase 5.)

---

## Phase 5 — Translate Evidence into Roadmap (amended)

**Purpose**: feed transcript evidence directly into the product roadmap. Exploratory work first, then committed work after retention gate.

### Prompt — Exploratory Phase 5 (Days 21-28, after charge-gate GO)

```
===PROMPT===
Charge-gate GO. Decision in docs/customer-discovery/decision.md.

This is exploratory Phase 5 — 1 week of scoped roadmap work, no full
commitment yet. Retention gate at Day 51 is what unlocks the 90-day commitment.

Use /flow:triage to translate the top three feature priorities from
decision.md into Gold Flow runs. For each:
- Cite the transcript quotes that justify the feature
- Lock acceptance criteria that a real interviewed prospect could verify
- Route to /flow:plan if complexity warrants or /flow:execute if MICRO

Update web/src/app/pricing (or wherever pricing lives) to reflect the revised
price from decision.md. Tests first, per CLAUDE.md TDD rule.

Do NOT generate features that were not explicitly asked for by interviewed
prospects. The rule this sprint just proved: no more imagining.

Do NOT start the committed 90-day work until retention gate passes at Day 51.
===PROMPT===
```

### Prompt — Committed Phase 5 (Day 51+, after retention-gate GO)

```
===PROMPT===
Retention-gate GO ratified. Committed 90-day Phase 5 starts now.

Use /flow:dev to drive the top-priority feature from decision.md to DONE.
Each feature must have a named prospect from transcripts who asked for it.

Pricing (if updated at Day 21) stays as-is unless retention data suggests a
change.
===PROMPT===
```

**Gate**: each feature has a named prospect who asked for it, with quoted evidence in the Gold Flow triage.

---

## Anti-patterns — things to not let Claude Code do

1. **Generating interview transcripts from "likely responses."** Only real quotes from real humans count.
2. **Auto-advancing phase gates.** Each gate is manual.
3. **Softening the preorder test into "would you pay" surveys.** The ask is a real payment.
4. **Inflating "strong signal" scores to reach 10 qualified prospects.** Padding corrupts the go/no-go decision.
5. **Starting committed Phase 5 before retention gate passes.** Charge-gate GO unlocks exploration only.
6. **Anchoring follow-on prospects with prior prospects' answers.** When 5 prospects have said X, you'll lead the 6th toward X. Re-read interview-guide.md before every call.
7. **Skipping refund step on NO-GO.** Refund first; freeze second. The order matters legally and reputationally.
8. **Storing un-anonymized transcripts in git.** Anonymize at capture time, not later.
9. **Treating the charge gate as the GO.** It unlocks exploration only. Retention gate is the real GO.
10. **Padding the founder-hour budget.** If you can't block 30+ hours in the first 21 days, rescope to 8/5.

---

## Total time budget (amended)

| Phase | Days | Claude Code time | Your time |
|---|---|---|---|
| 0. Scope lock | (done) | — | — |
| Pre-flight | 1 | ~2 hr | ~3 hr |
| 1. Recruit | 14 | ~30 min/day = 7 hr | ~1.5 hr/day = 21 hr |
| 2. Interviews | 10 (overlap with recruit) | ~15 min/call prep = 4 hr | 30-45 min/call × 15 = 12 hr |
| 3. Preorder test | 5 | ~1.5 hr Stripe + 1.5 hr asks = 3 hr | ~30 min/day chasing = 2.5 hr |
| 4a. Charge gate | 1 | ~1 hr | ~2 hr |
| 4b. Retention gate | (Day 51) | ~30 min | ~30 min |
| 4c. Refunds (NO-GO branch) | 1 | ~30 min | ~1 hr |
| **Total to charge gate** | **~21 days** | **~17 hr** | **~42 hr** |
| **Plus retention gate** | **+30 days** | **+30 min** | **+30 min** |

**42 founder-hours over 21 days, ~42.5 over 51 days.** If you cannot block 30+ hours over the first 21 days, scope to 8 interviews / 5 paid asks. Twenty-five hours wasn't enough; four-plus weeks of part-time founder energy is.

---

## Verification

Operational, not code:

- **Pre-flight done when** 7 items committed, calendar pre-blocked, ≥30 hours blocked.
- **Phase 1 done when** 18 calls scheduled, pipeline.csv has 100+, zero network hires, Day-7 gate passed.
- **Phase 2 done when** 15 anonymized transcripts + 15 scorecards exist. Disqualified-log captures probes.
- **Phase 3 done when** 7+ of 10 (or 15) asks have resolved. Objection tags applied.
- **Phase 4 charge gate done when** decision.md committed. Refunds first if NO-GO.
- **Phase 4 retention gate done (Day 51)** when ratified GO or demoted to NO-GO.
- **Success** = ≥80% of the charge-gate paid cohort (minimum ≥4 subscriptions) retained through second billing cycle, attached to real emails of real anonymized-in-git people whose transcripts you can re-read.

If at the end of 51 days you don't have that retained-revenue evidence, no number of additional features will fix it. Change the customer, or change the product.
