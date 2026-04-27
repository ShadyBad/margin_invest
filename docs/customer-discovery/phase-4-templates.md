# Phase 4 Templates — Decision, Refunds, Freeze

**Drafted**: 2026-04-27 (during Pre-flight)
**Status**: Pre-drafted templates for Phase 4 charge-gate and retention-gate decisions. Use as starting drafts; personalize per actual data.

> **Critical sequence**: on NO-GO, refunds are issued and customers notified BEFORE `FROZEN.md` is committed. Do not reverse this order. Refund-then-freeze, not freeze-then-refund.

---

## decision.md skeleton

Save as `docs/customer-discovery/decision.md` when Phase 4 charge gate is reached. Append retention-gate section at Day 51.

```markdown
# Customer Discovery Sprint Decision

**Sprint period**: 2026-XX-XX (kickoff) to 2026-XX-XX (charge gate, Day 21)
**Retention-gate evaluation date**: 2026-XX-XX (Day 51)
**Verdict (charge gate)**: [GO / SOFT GO / NO-GO]
**Verdict (retention gate)**: [GO / SOFT GO / NO-GO / pending]

---

## Charge gate raw numbers

- **Asks sent**: [X] of [10 or 15] target
- **Responses received**: [X] (paid + declined + no_response after follow-up + objection-resolved)
- **Paid**: [X]
- **Declined**: [X]
- **No response**: [X]
- **Total revenue collected (gross)**: $[X]
- **Conversion rate (paid / asks_sent)**: [X]%

### Per-prospect outcome table

| prospect | interview_# | rubric_score | price_arm | outcome | objection_tag |
|---|---|---|---|---|---|
| | | | | | |

(Reference `preorder-test-results.md` for verbatim objection notes.)

---

## Objection-pattern analysis

| tag | count | % of non-payment |
|---|---|---|
| delivery-risk | | |
| price-objection | | |
| feature-gap | | |
| disinterest | | |

**Dominant pattern**: [tag] ([X]% of non-payments)

---

## Charge-gate verdict

**Verdict**: [GO (charge) / SOFT GO / NO-GO]

**Reasoning** (cite specific numbers, no spin):
- [If ≥4/10 paid AND dominant ≠ disinterest → GO charge]
- [If 2-3/10 paid → SOFT GO; describe path forward]
- [If ≤1/10 OR ≥60% disinterest → NO-GO]

**Next steps**:
- [GO charge → unlock exploratory Phase 5 (1 week, Days 21-28). Schedule retention gate at Day 51.]
- [SOFT GO → tighten ICP / raise price / re-ask. Re-evaluate at Day 51.]
- [NO-GO → refund (see below) → commit FROZEN.md → fresh /superpowers:brainstorming on alternative ICP.]

---

## Rubric validity (if Option B was run)

Cohort: 15 asks across rubric buckets.

| rubric_bucket | asks_sent | paid | conversion |
|---|---|---|---|
| 6/6 strong | | | |
| 5/6 strong | | | |
| 4/6 strong | | | |
| 3/6 weak | | | |
| ≤2/6 weak | | | |

**Finding**: [Does the rubric predict conversion? If 6/6 converts at 60% and 4/6 at 30%, the rubric is doing real work. If conversion is flat across buckets, the rubric is noise.]

If rubric is noise: re-design rubric BEFORE attempting another sprint with the same ICP.

---

## Price elasticity (if 2-arm test was run)

| price_arm | asks_sent | paid | conversion |
|---|---|---|---|
| $49 | | | |
| $29 (or $39) | | | |

**Finding**: [If $29 has ≥1.5× the conversion of $49, you're leaving demand on the table at $49. If $29 has ≤1.1× conversion, $49 is approximately right.]

**Pricing recommendation**: [Hold $49 / Move to $X / Test $79 next round].

---

## Rapport-vs-cold conversion (if split was run)

| ask_type | asks_sent | paid | conversion |
|---|---|---|---|
| rapport-driven (personalized) | | | |
| cold-template (Stripe-only) | | | |

**Finding**: [If rapport is ≥2× cold, your conversion measures founder energy as much as product demand. Footnote in roadmap planning.]

---

## What I learned about the product

(Cite anonymized transcript quotes — `$TICKER_A`, dollar buckets.)

- Specific gap most prospects shared: [...]
- Tool stack most prospects already pay for: [...]
- Wound pattern: [...]
- Surprises (things I didn't expect): [...]

---

## What I learned about my bias as a builder

(Honest reflection on places where reality diverged from kickoff hypothesis.)

- Hypothesis I held that was wrong: [...]
- Feature I assumed mattered that prospects didn't mention: [...]
- Feature prospects asked for that I hadn't planned: [...]

---

## NO-GO pivot candidates (NO-GO branch only)

(Read `disqualified-log.md` rows. Cluster patterns.)

### Candidate ICP 1: [name]
- **Tools used**: [common patterns]
- **Wishes**: [common patterns]
- **Sample size**: [N rows in disqualified-log.md]

### Candidate ICP 2: [name]
- ...

### Candidate ICP 3: [name]
- ...

Open `/superpowers:brainstorming` on the most promising candidate. Use the new ICP to scope a follow-up sprint.

---

## Retention-gate raw numbers (filled at Day 51)

- **Charge-gate cohort size**: [X paid customers]
- **Retained through second billing cycle**: [X]
- **Cancelled before second charge**: [X]
- **Retention rate**: [X]%

### Per-customer retention table

| prospect | charge_date | second_charge_date | status | cancellation_reason (if any) |
|---|---|---|---|---|
| | | | | |

---

## Retention-gate verdict

**Verdict**: [GO (committed) / SOFT GO / NO-GO (demoted)]

- ≥80% retained → GO (committed). Start committed 90-day Phase 5.
- 60-79% retained → SOFT GO. Hold 1 week. Investigate churn. Decide.
- ≤40% retained → NO-GO (demoted). Refund holdouts. Commit FROZEN.md.

**Operational gloss**: cohort of 4-9 → lose ≤1; cohort of 10+ → lose ≤2.

---

## 90-day commitment (committed GO branch)

(Top-3 priorities from charge-gate GO section, ratified by retention-gate GO.)

1. **Priority 1**: [feature name]
   - Source: prospect [firstname] in interview [NN]: "[anonymized quote]"
   - Acceptance criteria: [what would make [firstname] use this in their workflow]
   - Routing: /flow:plan or /flow:execute

2. **Priority 2**: ...

3. **Priority 3**: ...

---

## Sprint retro (filled after final verdict)

- **What worked**: [...]
- **What didn't work**: [...]
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

---

## NO-GO refund email template

For each paid customer, after issuing the Stripe refund (refund FIRST, email second).

```
Subject: Important update on the Margin Invest Founder Beta

Hi [first name],

I wanted to write personally and tell you the truth: I'm pausing the Margin Invest Founder Beta. Of the [N] founders I asked to preorder, [X] paid — not enough signal that this is the right product for the people I was building it for.

I've issued a full refund of your $[49] subscription back to your card on file. You should see it in 5-10 business days. The subscription is also cancelled — no future charges.

I'm sorry. You bet on this early, and I owe you honesty about why I won't be shipping it as planned.

What I'm doing next: taking what I learned from these interviews — including yours — and figuring out who the real customer is. If a different version of this ever comes back, I'll email you first.

Thank you again for the conversation. It was the most useful 30 minutes of my month.

— [Your name]
```

**Personalization rules**:
- Use their first name only (consistent with anonymization protocol)
- The N and X numbers are from your raw count
- If quoting their interview, quote anonymized words (replace $TICKER_A back to nothing — don't use the pseudonym in customer-facing email)
- If you genuinely intend to pivot to a different product: include the "I'll email you first" line. If you don't intend to: omit it. Do not promise something you won't deliver.

---

## FROZEN.md template

Save as `FROZEN.md` at repo root. Commit AFTER all refunds are issued and confirmed.

```markdown
# FROZEN

Feature work paused 2026-XX-XX pending new customer discovery.

## What this means

- No new feature commits to engine/, api/, or web/ until this file is removed.
- Maintenance commits (security patches, dependency upgrades, infrastructure fixes) are allowed.
- Documentation updates are allowed.

## Why

The customer discovery sprint that ran from 2026-XX-XX to 2026-XX-XX returned NO-GO. See [docs/customer-discovery/decision.md](docs/customer-discovery/decision.md) for the evidence trail and the alternative ICPs being considered.

## Refund status

All paid Founder Beta subscriptions ($X total) were refunded between 2026-XX-XX and 2026-XX-XX. See `decision.md` §"Refund log" for per-customer confirmation.

## Next step

A new `/superpowers:brainstorming` session has been opened on candidate pivot ICPs surfaced from `disqualified-log.md`. When that produces a new spec and plan, this FROZEN.md will be removed and replaced with a `LAUNCH.md` referencing the new sprint.

## Removal

Remove this file ONLY when:
1. A new ICP has been identified and validated through a fresh discovery sprint
2. New top-3 priorities are documented in a successor `decision.md`
3. Maintenance work has not introduced regressions in the existing build
```

---

## Refund log addendum (for decision.md)

Add this section to `decision.md` immediately after issuing refunds, BEFORE committing FROZEN.md:

```markdown
## Refund log (NO-GO branch)

Refunds issued via Stripe dashboard within 48 hours of NO-GO verdict.

| customer | charge_date | charge_amount | refund_date | refund_id | confirmation_email_sent |
|---|---|---|---|---|---|
| | | | | | |

**Total refunded**: $[X]
**All refunds confirmed**: [Y/N — verified via Stripe dashboard]
**All confirmation emails sent**: [Y/N]
```

---

## Sequence checklist (NO-GO branch)

Strict order. Do not skip steps or change order.

1. [ ] Compute charge-gate metrics (Phase 4 Task 4a.1)
2. [ ] Determine verdict = NO-GO (Task 4a.2)
3. [ ] Open Stripe dashboard, switch to LIVE mode
4. [ ] For each paid customer: issue full refund (Task 4a.3)
5. [ ] Confirm each refund in Stripe dashboard (status = refunded)
6. [ ] Cancel each subscription so no future charges occur
7. [ ] Append refund log to `decision.md`
8. [ ] Send personalized notification email to each refunded customer (Task 4a.4)
9. [ ] Confirm each email sent
10. [ ] Read `disqualified-log.md`, append the probe data to `decision.md` as anecdote-quality input. Realistic yield is 0-3 entries — do NOT pad to "top 3" if fewer exist. With 0 entries: note that absence of pivot data is itself a finding for the next sprint.
11. [ ] Commit `decision.md` (full content — verdict + numbers + refund log + pivot candidates)
12. [ ] Draft `FROZEN.md` from template above
13. [ ] Commit `FROZEN.md`
14. [ ] Open fresh `/superpowers:brainstorming` on top-1 alternative ICP

If any step fails (refund declines, email bounces, etc.), STOP. Resolve the failure. Do not skip ahead to FROZEN.md until refund + notification are complete.

---

## Sequence checklist (charge-gate GO branch)

1. [ ] Compute charge-gate metrics
2. [ ] Determine verdict = GO (charge) or SOFT GO
3. [ ] Write `decision.md` charge-gate section per skeleton above
4. [ ] Commit `decision.md`
5. [ ] Schedule Day 51 retention gate (calendar event)
6. [ ] Begin exploratory Phase 5 (Days 21-28): read transcripts for top-3 priorities
7. [ ] Plan Day-35 beta delivery (per `beta-deliverable.md`)
8. [ ] Day 35: deliver beta to all paid customers
9. [ ] Days 36-50: monitor retention; capture cancellation reasons
10. [ ] Day 51: retention-gate evaluation (Task 4b.1)
11. [ ] Append retention-gate section to `decision.md`
12. [ ] Commit final `decision.md`
13. [ ] If retention-gate GO: start committed 90-day Phase 5
14. [ ] If retention-gate NO-GO (demoted): trigger NO-GO sequence above (refund holdouts, FROZEN.md)
