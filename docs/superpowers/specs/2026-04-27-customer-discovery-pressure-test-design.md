# Customer Discovery Sprint — Pressure-Test Findings

**Date**: 2026-04-27
**Status**: Approved findings, source for `docs/customer-discovery/action-plan.md` v2
**Author**: Brainstorming session, pressure-testing the chat-pasted Customer Discovery Action Plan v1
**Related**: `docs/customer-discovery/{icp,interview-guide,rubric,preorder-test}.md` (Phase 0 artifacts, scope-locked)

---

## Executive Summary

This spec captures 20 findings from a pressure-test of the Customer Discovery Action Plan v1, organized into four dimensions: Feasibility, Signal Validity, Threshold Calibration, and Ethics & Commitments. Each finding has a severity rating and a recommended amendment.

The plan is fundamentally sound — gate-based, evidence-driven, anti-pattern-aware, and properly skeptical of features-as-validation. The findings below are calibration adjustments, not redesigns. They concentrate in three areas:

1. The founder-time and recruitment math is 2-3× understated.
2. N=10 paid asks is too small for the threshold buckets as currently set.
3. Consent / anonymization / refund procedures are silent and need to be made explicit before Phase 1 launches.

### Top 5 must-do amendments

1. **Two-gate GO structure** (V2 + T3): split GO into a Day-21 charge gate (≥4/10 paid → exploratory roadmap) and a Day-51 retention gate (≥80% retained through second billing cycle → 90-day commitment). False-GO cost is too high to commit on first-charge alone.
2. **Re-anchored thresholds** (T1 + T2): GO at 4/10 (40%, top-third realistic outcome), SOFT at 2-3/10, NO-GO at ≤1/10. Current 5/10-or-bust is set above realistic best-case prosumer-SaaS preorder conversion.
3. **Realistic founder-hour budget** (F2): rebudget to 40-60 hours, not 25. If you cannot block 30+ hours over 21 days, scope sprint to 8 interviews / 5 paid asks.
4. **PII consent + anonymization** (E2): add consent script to interview opening; anonymize transcripts at capture (first name, `$TICKER_A`, dollar buckets); decide retention.
5. **Day-35 deliverable doc** (E1): pre-write `docs/customer-discovery/beta-deliverable.md` defining exactly what a paid customer gets on Day 35. Reference it from the Stripe ask.

### Severity counts

- **Critical** (6): F1, F2, V1, V2, E1, E2
- **High** (8): F4, F5, V3, V4, T1, T3, E3, E4
- **Medium** (6): F3, V5, T2, T4, T5, E5

---

## §1 Feasibility

### F1 — Recruitment math is 3-10× under-budgeted [Critical]

**Claim**: Plan v1's "30+ prospects → 15 scheduled calls" assumes pipeline:scheduled:completed at 2:1:1. Realistic ratios are closer to 7:1.2:1.

**Evidence**: Cold-DM response rates on Reddit/Twitter for stranger 30-min Zoom asks: 5-15% of personalized DMs convert to a reply expressing interest. Of those, ~70% schedule. Of scheduled, ~75% actually complete. End-to-end: completed/DM ≈ 3-8%. To complete 15 interviews → 200-500 DMs, 18-22 scheduled.

**Amendment**: Redefine pipeline.csv target as 100+ qualified prospects. Track three columns: `dm_sent`, `scheduled`, `completed`. Schedule-target 18 to land 15 completed. Pipeline-target 100+ to land 18 scheduled.

### F2 — Founder-hour budget is ~½ of reality [Critical]

**Claim**: Plan v1's 25 founder-hour budget across 21 days understates by 60-125%.

**Evidence**: Re-add (each line is realistic minimum):

| Activity | Time |
|---|---|
| Sourcing (read posts, qualify, paste to Claude) | 1-2 hr/day × 14 = 14-28 hr |
| DM personalization review + sending | 30 min/day × 14 = 7 hr |
| Calls + buffer | 15 × 45 min = 11 hr |
| Transcript-paste workflow | 20 min × 15 = 5 hr |
| Phase 3 chasing responses | 30 min/day × 5 = 2.5 hr |
| Phase 4 reflection + writing | 2 hr |
| **Total** | **41-56 hr** |

**Amendment**: Rebudget to 40-60 founder-hours. Add a doorstop in the new pre-flight phase: "If you cannot block 30+ hours over 21 days, scope to 8 interviews / 5 paid asks."

### F3 — Calendar capacity unaddressed [Medium]

**Claim**: 15 calls × ~45 min = ~11 hours of synchronous time. Plan v1 doesn't pre-block slots; recruitment can outrun calendar.

**Evidence**: Solo nights/weekends: ~2 evening slots/weekday × 10 days = 20 candidate slots. Business hours: collides with `/flow:dev` directly. No-shows + reschedules eat 20-30% of slots.

**Amendment**: Pre-block 18 specific calendar slots before Phase 1 starts. If 18 cannot be blocked, the sprint isn't actually feasible at this scope — rescope or extend the recruitment window.

### F4 — $50 gift creates moral-hazard vector [High]

**Claim**: Plan v1 doesn't specify when the $50 gift pays out. Pre-call or unconditional payment incentivizes faking qualification answers.

**Evidence**: A prospect who knows the gift is paid regardless will fake the disqualifier check (claim self-directed, claim $250K AUM) to collect. The disqualifier check at call start becomes adversarial.

**Amendment**: Gift pays out only after a *qualified-and-completed* call (disqualifier passed, ≥25 min, preorder ask delivered if eligible) OR a *disqualified-but-probed* call (5-min tools/wishes probe completed — preserves V3 pivot data). State this in the recruitment DM and in `interview-guide.md` opening. Reframes the gift from "pay for time" to "pay for completed signal."

### F5 — No fallback path for low yield [High]

**Claim**: Plan v1 has no mid-sprint checkpoint for "Day 7, 50 DMs sent, 4 responses, 1 scheduled." Implicit response is "send more DMs," but channel exhaustion is real.

**Evidence**: After ~50 personalized DMs in r/SecurityAnalysis, you've covered the top posters of the last 90 days. Adding more DMs hits diminishing-quality prospects.

**Amendment**: Insert a Day-7 yield gate. If <8 scheduled by Day 7, choose:

- (a) Expand channels (Twitter Lists, paid Discord servers like RoaringKitty/SuperInvestor, Substack comments on Bearcave/Hindenburg/Kerrisdale)
- (b) Raise gift to $75-100 and re-DM cold prospects with the bump
- (c) Accept reality and rescope sprint to 8 interviews / 5 paid asks

Pick one before continuing. Document in `pipeline.csv` notes column.

---

## §2 Signal Validity

### V1 — N=10 paid asks is statistically thin [Critical]

**Claim**: With 10 trials, the difference between GO (5/10) and SOFT GO (3-4/10) is one or two coin-flip outcomes. Wilson 95% CI on 5/10 is roughly 24%-76%; on 3/10 roughly 7%-65%.

**Evidence**: Standard binomial CI calculations. The CIs overlap so thoroughly that you cannot reliably distinguish a 30%-conversion market from a 50%-conversion market at this N.

**Amendment**: Either (a) raise N to 15 paid asks (all interviewed prospects, also serving V4 rubric validation) to tighten the CI, OR (b) reframe the metric as binary — "≥4/N = proceed and gather more evidence; ≤1/N = stop." Don't fool yourself with three buckets at N=10.

### V2 — Initial charge ≠ retained revenue [Critical]

**Claim**: Plan v1 defines GO as "5+ paid Stripe subscriptions live." A subscription cancelled on Day 28 reads identically to one retained through Year 1.

**Evidence**: Founder-led preorder cohorts often see 20-40% pre-second-charge churn. The "5 paid" number conflates "willing to try" with "willing to pay recurring."

**Amendment**: Two-gate structure.

- **Charge gate** (Day 21): ≥4/10 paid → unlock *exploratory* Phase 5 (1 week of scoped roadmap work, no full commitment).
- **Retention gate** (Day 51, 30 days post-charge): ≥80% of charge-gate cohort retained through second billing cycle → ratify GO and start *committed* 90-day Phase 5. Operational gloss: lose ≤1 customer for cohorts of 4-9; lose ≤2 for cohorts of 10+.
- 60-79% retained: hold; treat as SOFT GO; investigate churn reasons before commitment.
- ≤40% retained: demote to NO-GO.

### V3 — Disqualifier filter breaks Phase 4 NO-GO pivot logic [High]

**Claim**: Phase 4 NO-GO branch wants to identify "alternative ICPs from disqualifier patterns." But the disqualifier check filters those people out before they ever get to the 5 questions.

**Evidence**: A prospect who fails the disqualifier check (options trader, indexer, robo user) gets the call ended at minute 3. You don't capture their tools, wishes, or pain.

**Amendment**: After the disqualifier check fails, run a 5-minute probe: "What tools do you use, what do you wish existed?" Capture in `docs/customer-discovery/disqualified-log.md` (separate from the 15 main transcripts). Cheap, but rescues the NO-GO pivot path.

### V4 — Rubric is itself an untested instrument [High]

**Claim**: Strong-signal selection uses the 6-signal scorecard. The rubric's predictive validity for paid conversion is unknown.

**Evidence**: `rubric.md` was iterated based on hypothesis (1/0/-1 scoring, $30 threshold, kill override). It hasn't been validated against actual conversion data — there is none yet. Using it as a filter assumes the hypothesis is correct.

**Amendment**: Send the preorder ask to all 15 interviewed prospects, not just the top 10 strong-signal. Compare conversion rates across rubric buckets *post-hoc*. Validates (or invalidates) the rubric while collecting the primary signal. Cost: 5 extra Stripe asks, ~2 hours of objection handling.

### V5 — Single-price test gives zero elasticity signal [Medium]

**Claim**: $49/mo is the only price tested. Plan v1 has no way to learn whether $29 doubles conversion or $79 only halves it.

**Evidence**: The "what number would feel like a no-brainer" follow-up is verbal. Verbal stated WTP famously over-states behavioral WTP by 2-3×.

**Amendment**: Optional 2-arm test. 7 prospects asked at $49, 8 at $29 (or $39). Loses statistical power per arm but produces a slope. If declined, pre-commit a Phase 4 conclusion: "I will assume $49 is correct unless retention drops below X."

---

## §3 Threshold Calibration

### T1 — GO threshold (5/10 = 50%) above realistic best-case [High]

**Claim**: 50% conversion from "interview-strong-signal" to "paid" is top-decile for prosumer SaaS founder-led preorders. Using it as the minimum bar means most genuinely-viable markets fail.

**Evidence**: Published founder-led preorder conversion rates for prosumer SaaS land in the 20-40% range. 50% would be exceptional. Setting GO above realistic best-case calibrates the gate to optimism, not market reality.

**Amendment**: Drop GO to **4/10** (40%, defensible top-third). Keep SOFT GO at 2-3/10 (median realistic range). Move NO-GO to 0-1/10 (clearly broken).

### T2 — Kill threshold (≤2/10) at realistic floor [Medium]

**Claim**: 20% conversion is the realistic floor — *normal* for prosumer SaaS preorders, not abnormal. Killing on 2/10 risks killing a working market.

**Evidence**: See T1 base rate. 20% is "normal," not "broken."

**Amendment**: Pull kill bar down to ≤1/10. Anything in 2-3/10 is "needs more evidence," not "stop."

### T3 — Error costs are asymmetric; thresholds shouldn't be [High]

**Claim**: A false GO commits to 90 engineering days for ghosts (catastrophic). A false NO-GO costs 21 days re-running with refined ICP (recoverable). Thresholds should bias toward NO-GO; current symmetric thresholds don't.

**Evidence**: Plan v1's GO/SOFT/NO-GO bands are arithmetically symmetric: same evidence delta (3 vs 5 of 10) flips both directions. The downstream costs are not symmetric.

**Amendment**: Two-gate structure (see V2). Charge gate at 4/10 unlocks *exploratory* Phase 5 only; retention gate at 4/5 unlocks the full 90-day commitment. Costs you 1 week before commitment but converts the asymmetry into structure.

### T4 — 21-day budget is a hard threshold, but Phase 1 has all the slack risk [Medium]

**Claim**: Total budget = 21 days but Phase 1 (recruitment, 14 days) has the largest variance. If Phase 1 slips 4 days, Phase 2 quality drops or Phase 3 compresses.

**Evidence**: Plan v1 has no slack-allocation rule. Implicit assumption is Phase 1 finishes on time, which contradicts F1, F2, F5.

**Amendment**: Pre-commit slack allocation. "Phase 1 may extend to 18 days; if so, Phase 2 becomes interview-as-you-recruit (interview prospect N while still recruiting prospect N+5), and Phase 3 absorbs the remainder. The Day-21 charge-gate deadline is hard; Phase 1 is the only soft gate."

### T5 — No qualitative pattern threshold [Medium]

**Claim**: Plan v1 collapses all non-payment into one bucket. "1/10 paid, 8/10 said 'I'd buy after seeing it'" reads identically to "1/10 paid, 8/10 said 'I don't have this problem.'" The first is GO with delivery-risk amendment; the second is genuine NO-GO.

**Evidence**: Plan v1's verdict logic is pure paid-count.

**Amendment**: Add objection-pattern sub-rubric. Tag every objection: `delivery-risk`, `price-objection`, `feature-gap`, `disinterest`. Decision rule = paid-count + dominant objection pattern. ≥60% disinterest = NO-GO regardless of paid count. ≥60% delivery-risk = GO with shorter beta lead-time.

---

## §4 Ethics & Commitments

### E1 — Day-35 deliverable is undefined [Critical]

**Claim**: "Charged today, access in 14 days" means: charge Day 21, deliver Day 35. Plan v1 doesn't define what the customer receives on Day 35.

**Evidence**: No `beta-deliverable.md` file exists; `preorder-test.md` doesn't reference one. The Stripe ask sells a vibe.

**Amendment**: Pre-write `docs/customer-discovery/beta-deliverable.md` *before* Phase 3 launches. Define Day-35 surface explicitly: features included, auth flow, ticker coverage, pages live, what's NOT included. Link from the Stripe ask. Customer consents to a specific scope, not a vibe.

### E2 — PII in git has no consent / anonymization / retention plan [Critical]

**Claim**: Transcripts will contain real first names, AUM, ticker losses, brokerage names, dollar amounts, financial wounds — committed to GitHub. No consent script, no anonymization, no retention rule.

**Evidence**: Existing `transcripts/` and `scores/` directories are scaffolded. `interview-guide.md` doesn't include consent language. `preorder-test.md` doesn't address data handling.

**Amendment**: Three changes:

- **(a) Consent language** in interview opening, before 5 questions, before disqualifier check: "I take notes that I store in a private code repository. I'll use a first name only and won't store your handle or specific holdings — is that OK?" Get verbal yes before the 5 questions.
- **(b) Anonymization rules**: first name only; tickers → `$TICKER_A`, `$TICKER_B`, ...; dollar amounts → buckets (`$1-5K`, `$5-20K`, `$20-100K`, `$100K+`); AUM bucketed similarly; brokerages kept generic. Real handle stays in `pipeline.csv` only.
- **(c) Retention policy**: delete transcripts 30 days after `decision.md` is committed, OR move them outside git to encrypted local storage. Decide before Phase 2.

### E3 — NO-GO refund procedure silent [High]

**Claim**: If 4-5 paid → Day-21 NO-GO before delivery, you owe refunds plus an honest message. Plan v1 only addresses code freeze.

**Evidence**: Phase 4 NO-GO branch covers `FROZEN.md` commit but not customer refunds.

**Amendment**: Pre-write NO-GO refund script. Add as a step of Phase 4: "If verdict = NO-GO and any paid charges exist: (a) issue Stripe refund within 48 hours of decision, (b) send personalized email to each paid customer naming the decision and thanking them, (c) THEN commit `FROZEN.md`." Refunds first, freeze second.

### E4 — Recruitment channels may forbid the gift offer [High]

**Claim**: Many subs (r/SecurityAnalysis, r/investing) ban "compensated promotion" or "soliciting users." DM offering "$50 for a 30-min call" can trigger account bans mid-sprint.

**Evidence**: Reddit content-policy + most finance-sub wikis. Twitter has anti-spam triggers on volume DMing. Plan v1 assumes channels are unconstrained.

**Amendment**: Per-channel compliance check before Phase 1 launches. Read ToS/wiki of each recruitment source. For Reddit: prefer commenting on prospect's posts (lower violation risk) over cold DM. For Twitter: stagger DMs, use accounts with established posting history. Document findings in `docs/customer-discovery/recruitment-channel-rules.md`. If a channel forbids paid outreach, drop the gift offer for that channel and accept lower yield.

### E5 — Rapport-leveraged ask is ethically loaded [Medium]

**Claim**: Phase 3 ask uses sunk-cost (their 30 min) + reciprocity (your personalized message quoting their words). Effective. Also blends "demand for product" with "demand for relationship with founder." If you scale via cold acquisition, conversion will not generalize.

**Evidence**: Standard founder-sales tactic, well-documented effectiveness, well-documented over-prediction of cold-channel conversion.

**Amendment**: Optional split-cohort. 7 prospects get rapport-driven personalized follow-up; 3 get clean cold-template ask referencing only the public Stripe page. Compare conversion rates. If rapport-driven is 2× cold-template, footnote it in `decision.md` as a calibration finding. Not a reason to halt.

---

## Cross-cutting amendments

### Two-gate GO structure

Replace single Day-21 GO/NO-GO with:

- **Charge gate** (Day 21): ≥4/10 paid Stripe subscriptions → unlock 1-week exploratory Phase 5 (scoped roadmap work, no full commitment).
- **Retention gate** (Day 51, 30 days post-charge): ≥80% of charge-gate cohort retained through second billing cycle → ratify GO, start committed 90-day Phase 5. Operational gloss: lose ≤1 for cohorts of 4-9, ≤2 for cohorts of 10+.
- 60-79% retained: hold; treat as SOFT GO; investigate churn reasons before commitment.
- ≤40% retained: demote to NO-GO.

### Consent + anonymization protocol

- Verbal consent at interview opening, before 5 questions, before disqualifier check.
- Anonymize transcripts on capture: first name, `$TICKER_A` pseudonyms, dollar buckets, generic brokerage names.
- Real handle ↔ first-name mapping lives in `pipeline.csv` (encrypted local storage if possible) or is moved out post-decision.
- Delete or move-offline transcripts 30 days post-decision.

### Day-35 deliverable doc

- New file: `docs/customer-discovery/beta-deliverable.md`.
- Written and committed before Phase 3 launches.
- Defines: features included Day 35, auth flow, ticker coverage, pages live, what's explicitly NOT included.
- Linked from Stripe ask so customer consents to specific scope.

### Recruitment channel compliance

- New file: `docs/customer-discovery/recruitment-channel-rules.md`.
- Per-channel compliance findings + adjusted recruitment tactics.
- Written before Phase 1 launches.

### Disqualified-prospect log

- New file: `docs/customer-discovery/disqualified-log.md`.
- Captures 5-min probe results from disqualified prospects (V3).
- Source data for Phase 4 NO-GO pivot logic.

---

## Open questions

1. **Sprint scope tier (full vs. half)**: are you committing to 40-60 founder-hours over 21 days, or scoping to 8 interviews / 5 paid asks in ~25 hours? Decide before Phase 1.
2. **Beta deliverable scope**: what's the actual Day-35 surface? Depends on engine state, which depends on which other in-flight work (engine optimization Phase 5, design system) gets paused.
3. **PII retention choice**: delete transcripts 30 days post-decision, OR move offline? Affects how much of `docs/customer-discovery/` ends up in git long-term.
4. **Single-price vs. 2-arm**: are you running V5's split-price test or accepting single-point estimate?
5. **All-15 ask vs. top-10 ask**: are you running V4's all-15 cohort to validate the rubric, or sticking with top-10?
6. **Calendar pre-block feasibility**: can you actually pre-block 18 specific 45-min slots over the next 21 days, given engineering commitments?
