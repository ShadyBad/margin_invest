# Phase 3 Prep — Stripe Configuration & v2 Amendments

**Drafted**: 2026-04-27 (during Pre-flight)
**Status**: Pre-launch reference. Augments `preorder-test.md` (which is scope-locked) with v2 amendments and operational checklists.

> **IMPORTANT — v2 threshold override**: `preorder-test.md` says "GO = 5/10 paid." This is **superseded** by the v2 amendments in `action-plan.md` and the source spec. Use the v2 thresholds: GO = ≥4/10, SOFT GO = 2-3/10, NO-GO = ≤1/10 OR ≥60% disinterest. Do not run Phase 4 with the 5/10 threshold.

---

## What this doc adds vs. preorder-test.md

`preorder-test.md` covers the verbatim ask, the Stripe configuration, the objection handling for price/timing/"let me think." It is the canonical reference for the ask itself.

This doc adds:

- v2 threshold corrections (above)
- Option B (15 asks vs. 10) framing
- Optional 2-arm price test setup
- Mandatory link to `beta-deliverable.md` in the Stripe ask
- Objection-tagging schema (delivery-risk / price / feature-gap / disinterest)
- Stripe test-mode verification checklist
- Product configuration checklist before going live

---

## Decision: Option A (10 asks) vs. Option B (15 asks)

`preorder-test.md` assumes top-10 strong-signal asks only. The pressure-test (V4) recommends Option B — send to all 15 interviewed prospects to validate the rubric vs. paid conversion.

**Choose before Phase 3 launches**:

| | Option A (default) | Option B (recommended if you have ~2 hr extra) |
|---|---|---|
| Cohort | Top 10 strong-signal | All 15 interviewed |
| GO threshold | ≥4/10 paid | ≥6/15 paid (40%) |
| SOFT GO | 2-3/10 paid | 3-5/15 paid |
| NO-GO | ≤1/10 OR ≥60% disinterest | ≤2/15 OR ≥60% disinterest |
| Bonus signal | none | rubric validation (compare conversion across rubric buckets) |
| Cost | baseline | +5 Stripe asks, +2 hr objection handling |

Document the choice in `preorder-test-results.md` leading section before sending the first ask.

---

## Decision: Single-price ($49) vs. 2-arm price test

`preorder-test.md` assumes single price. The pressure-test (V5) suggests an optional split.

**Choose before Phase 3 launches**:

| | Single-price | 2-arm split |
|---|---|---|
| Asks at $49 | all (10 or 15) | 7 of 15 (or 5 of 10) |
| Asks at $29 (or $39) | none | 8 of 15 (or 5 of 10) |
| Statistical signal | conversion at $49 | slope estimate (point-A vs point-B) |
| Risk | no elasticity data | small per-arm CI is wide (N=7-8) |

**Recommendation**: if running Option B (15 asks), do the 2-arm. If Option A (10 asks), skip — N=5 per arm is too thin.

If skipping the split: pre-commit a Phase 4 conclusion in `decision.md` — "Assuming $49 is correct unless retention drops below 60%."

---

## Mandatory: Link to beta-deliverable.md in the Stripe ask

The pressure-test (E1) requires the customer consent to the Day-35 deliverable scope, not a vibe.

In the Stripe Checkout description (or the ask message itself), the link to `beta-deliverable.md` MUST appear. Two ways:

**Option 1 — Public-readable file**: copy `docs/customer-discovery/beta-deliverable.md` (Included + Not Included sections only) to a public page on the Margin Invest site. Link from Stripe.

**Option 2 — Inline in ask**: paste the Included + Not Included + Known Limitations sections verbatim into the Stripe Checkout description field.

**Option 3 — Inline in DM**: include "Here's exactly what's in the beta on Day 35: <link or paste>" in the ask DM/email above the Stripe link.

Pick one. The customer's consent is to a specific scope, not to whatever you eventually ship.

---

## Objection-tagging schema (v2 addition)

Every non-payment outcome must be tagged with one of:

| Tag | Definition | Phase 4 implication |
|---|---|---|
| `delivery-risk` | "I'd buy a working product" — they want to see it work first | Counts as latent positive; ≥60% delivery-risk + ≥3 paid → consider GO with shortened delivery promise |
| `price-objection` | "$49 is too high" or "I'd pay X instead" | Counts as price-elasticity signal; capture their no-brainer number |
| `feature-gap` | "I'd buy if it did X" — specific feature missing | Counts as feature priority signal; informs Phase 5 roadmap |
| `disinterest` | "I don't have this problem" / no value perceived | Counts as anti-signal; ≥60% disinterest → NO-GO regardless of paid count |

Add an `objection_tag` column to `preorder-test-results.md` if not already present (it is per action-plan.md v2). Tag every ask outcome that wasn't `paid`, `declined-no-reason`, or `no_response`.

---

## Stripe Checkout — pre-go-live checklist

Before sending the first ask:

### Product configuration

- [ ] Product name: "Margin Invest — Founder Beta"
- [ ] Description: includes link to (or text of) `beta-deliverable.md` Included + Not Included sections
- [ ] Price: $49.00 USD/month, recurring (or $49 + $29/$39 for 2-arm test = two separate products)
- [ ] Trial period: 0 days
- [ ] Tax handling: Stripe Tax enabled OR explicit "tax included" / "tax exclusive" stance

### Checkout session configuration

- [ ] Required fields: email, full name, payment card
- [ ] Success URL: live page confirming "You're in. Beta access in approximately 14 days." (NOT a 404)
- [ ] Cancel URL: live page that doesn't break the funnel
- [ ] Customer portal: enabled for self-serve cancellation
- [ ] Session metadata template: `prospect_name`, `interview_number`, `source`, `strong_signals`, `price_arm` (if 2-arm)

### Test-mode verification

- [ ] Open Stripe test mode
- [ ] Test card 4242 4242 4242 4242, any future expiry, any CVC
- [ ] Complete a test transaction end-to-end
- [ ] Verify Success URL loads correctly
- [ ] Verify subscription appears in test-mode dashboard
- [ ] Verify Customer Portal link works (test cancellation flow)
- [ ] Verify refund flow from dashboard (you'll need this for NO-GO branch)
- [ ] Verify metadata fields are captured on the test subscription

### Live-mode go-live

- [ ] Switch to Stripe live mode
- [ ] Verify Checkout URL is the LIVE one, not test
- [ ] Save Checkout URL to a private notes file (NOT committed): `~/.margin-invest-stripe-notes.md`
- [ ] Verify your Stripe account has refund permissions enabled
- [ ] Confirm card payouts schedule (so paid revenue actually lands in your account if GO ratifies)

---

## Sending the asks — operational checklist

For each ask sent:

- [ ] Personalize message per `preorder-test.md` template (anonymized: tickers as $TICKER_A, dollar buckets)
- [ ] Quote the prospect's actual words from the transcript (use them, anonymized)
- [ ] Reference `beta-deliverable.md` (link or inline)
- [ ] Use the LIVE Stripe Checkout URL (not test)
- [ ] If 2-arm test: assign per-prospect price arm; use the right URL
- [ ] Update `preorder-test-results.md` with `ask_sent_date`, `price_arm`, `status="sent_awaiting_response"`
- [ ] Send via the same channel they responded on (Reddit DM / X DM / email)
- [ ] Set a 7-day reminder to check for response

---

## Common pitfalls

### "Did you offer a discount?"

NO. Per pressure-test E5, never discount. The "what number would feel like a no-brainer" follow-up captures elasticity data without contaminating the conversion signal.

### "What if they ask for a longer trial?"

Decline. The trial period is 0 days by design — charging today is the test.

> "I'm intentionally not running a trial — I want signal from people who'd commit before seeing it. If you'd rather wait until it's live, totally fine — I'll email you when the beta opens."

Mark this as `delivery-risk` and capture in `objection_notes`.

### "What if they say 'send me one when it's ready'?"

Capture as `delivery-risk`. Get their email. Move on. Do not pitch.

### "What if Stripe Checkout breaks at 2am and a prospect can't pay?"

Test the Checkout in test mode AND in live mode (with your own card, then refund yourself) before sending the first ask. If a prospect reports Checkout failure, fix the URL/config and send a fresh link. Don't lose a hot prospect to a Stripe misconfiguration.

---

## Phase 3 close — verification

Before triggering Phase 4 charge gate:

- [ ] 10 (or 15) asks sent — check `preorder-test-results.md`
- [ ] 7+ responses logged (paid + declined + no_response after follow-up)
- [ ] Every non-payment has an `objection_tag`
- [ ] Stripe metadata correctly attached to every paid subscription
- [ ] No outstanding "let me think" replies older than 7 days (those become no_response)
