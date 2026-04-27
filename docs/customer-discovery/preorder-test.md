# Preorder Test — $49 Founder Beta

> **v2 amendments live in `phase-3-prep.md`. Read `phase-3-prep.md` BEFORE running Phase 3** — thresholds, ask-cohort rules (Option A vs B), and price-arm rules are amended there. The body of this document is preserved as the scope-locked Phase 0 reference and is OVERRIDDEN where it conflicts with `phase-3-prep.md`.

## Overview

This document defines the exact preorder protocol: when to ask, what to say, how to handle objections, and how to track outcomes. The preorder test is the only signal that matters — everything else (interviews, scores, quotes) is context for interpreting this result.

**The rule:** A preorder ask is a real charge on a real credit card. Not a survey. Not "would you pay." Not a waitlist signup. Real money or it doesn't count.

---

## Who Gets the Ask

Only **Strong prospects** from the rubric (4+ of 6 Strong signals, zero Kill signals). See `rubric.md` for scoring criteria.

- If 10+ prospects scored Strong: send to the top 10, ranked by composite signal strength. Break ties by: (1) dollar-loss specificity in Signal 1, (2) total monthly tool spend in Signal 2.
- If fewer than 10 scored Strong: send to all Strong prospects. Do NOT pad with Weak prospects to reach 10. If only 6 are Strong, only 6 get the ask. Padding corrupts the go/no-go math.
- If fewer than 5 scored Strong: this is itself a signal. The ICP may be wrong or the recruitment sources missed. Document this in the decision file before proceeding.

---

## When to Send

**After the call, not during it.** The preorder ask is sent via DM or email within 24 hours of the interview. Reasons:

1. A live ask on a Zoom call produces social-reciprocity bias — they may say yes because you listened to them for 30 minutes and they like you
2. An async message lets the decision happen without your presence. They're alone with their credit card. That's the real test.
3. It gives you time to personalize the message with specific references to their interview

---

## The Ask — Exact Wording

Send this via the same channel you recruited them on (Reddit DM, X DM, email — whatever they responded to originally):

> Subject: Following up from our call
>
> [First name] — thanks again for the conversation on [day of week]. What you said about [one specific thing from their interview — use their words, not your summary] stuck with me.
>
> I'm building something that directly addresses [the gap they named in Q2 or Q3 — the specific unmet need they articulated]. It's called Margin Invest — a forensic equity scoring engine. No opinions, no analyst picks. Deterministic scoring across quality, value, and momentum with six elimination filters that catch accounting red flags before they show up in the stock price.
>
> I'm opening a founder beta to 10 people in two weeks. $49/month, cancel anytime. You'd be one of the first to use it, and I'd build based on your feedback.
>
> If you're in: [Stripe Checkout link]
>
> If you have questions, just reply. No pressure either way — the conversation alone was valuable.

**Personalization is mandatory.** The bracketed sections must reference THAT specific prospect's interview. "What you said about [your research process]" is not personalized. "What you said about [spending two hours every Saturday cross-referencing Koyfin data with your spreadsheet because neither tool flags accounting quality]" is personalized.

---

## Stripe Checkout Configuration

### Product Setup

- **Product name:** Margin Invest — Founder Beta
- **Price:** $49.00 USD / month (recurring subscription)
- **Trial period:** 0 days — charged immediately upon checkout
- **Billing cycle:** Monthly, starting from the date of purchase
- **Coupon codes:** None. Do not create any. The price is the price.

### Checkout Session Requirements

- **Collects:** Email address (required — this is the beta access identifier), full name, payment card
- **Success URL:** A simple page or redirect confirming: "You're in. I'll email you when the beta opens in approximately 2 weeks."
- **Cancel URL:** Redirect back to a page that says: "No problem. If you change your mind, the link will still work."
- **Customer portal:** Stripe self-serve portal must be enabled so customers can cancel without contacting you. Link to the portal in the confirmation email.
- **Session metadata:** Attach these fields to every Checkout session:
  - `prospect_name` — matches the name in `pipeline.csv`
  - `interview_number` — the NN from the transcript/scorecard filenames
  - `source` — Reddit / X / Substack
  - `strong_signals` — count (e.g., "5")

This metadata ensures every Stripe payment traces back to a specific scorecard and transcript.

### Confirmation Email

After successful payment, send (via Stripe receipt or manual follow-up):

> [First name] — you're in. I'll email you at this address when the founder beta opens in approximately two weeks.
>
> If you ever want to cancel or manage your subscription: [Stripe customer portal link]
>
> In the meantime, I'd love to know: what's the first thing you'd want to check when you get access? Just reply to this email.
>
> Thanks for betting on this early.

The "what's the first thing" question is a free feature-priority signal from a paying customer.

---

## Objection Handling

Only respond to objections they raise. Never preempt objections. Never discount.

### Price Objection ("$49 is a lot" / "$49 seems high")

> "Totally fair. Out of curiosity — what number would feel like a no-brainer for you?"

Record their exact number. This is pricing data. Do NOT offer that number. Do NOT negotiate. If they name a number (e.g., "$25"), note it in the tracker and respond:

> "That's helpful to know. I'll keep you posted as things develop."

Do not close the sale at a lower price. One discounted conversion is worse than zero conversions — it tells you nothing about whether the market supports $49.

### Timing Objection ("I'd buy once it's built" / "Can I wait for the beta?")

> "I get that. What specifically would you need to see in the first beta for it to be worth $49 to you?"

Record their answer — this is a feature priority signal. These prospects are telling you what to build first. Respond:

> "That's really helpful. I'll keep that in mind as I build. Can I follow up when that specific feature is ready?"

### "Let me think about it"

> "Of course. I'll leave the link open — no deadline."

Wait 5 days. If no response, send ONE follow-up:

> "Hey [name], just checking — any questions I can answer about the beta?"

If no response after the follow-up, mark as `no_response` in the tracker. Do not send a third message.

### "What exactly does it do?" (wants more detail)

> "In short: you give it a ticker, it runs six forensic elimination filters (accounting quality, financial distress, cash flow, etc.) and scores what survives across quality, value, and momentum factors. Everything is deterministic — same inputs, same outputs, no analyst opinions. I'll have more to show you in two weeks."

Keep it to this. Do not demo. Do not send screenshots. The preorder test measures willingness to pay based on the problem description, not the solution demo.

---

## Outcome Tracking

Maintain `docs/customer-discovery/preorder-test-results.md` as a table tracking every ask:

```
# Preorder Test Results

## Summary

- **Total asks sent:** [X]
- **Responses received:** [X]
- **Paid:** [X]
- **Declined:** [X]
- **No response:** [X]
- **Objections (pending):** [X]
- **Conversion rate (paid / asks sent):** [X]%
- **Total revenue collected:** $[X]

## Detail

| prospect | interview_# | strong_signals | ask_sent_date | response_date | outcome | amount | objection_type | objection_verbatim | follow_up_sent | notes |
|----------|-------------|----------------|---------------|---------------|---------|--------|----------------|--------------------|----------------|-------|
| | | | | | | | | | | |
```

### Outcome Definitions

There are exactly four outcomes. No "maybe." No "interested." No "warm lead."

- **paid** — They clicked the Stripe link and completed payment. The only outcome that counts toward the go signal.
- **declined** — They explicitly said no, with or without a reason. Record the reason if given.
- **no_response** — They did not respond to the ask AND the one follow-up. After the follow-up, this is final.
- **objection** — They responded with a price, timing, or detail objection. Record the objection verbatim. If the objection resolves to paid or declined, update the outcome. If it goes silent after your response, reclassify as no_response after 5 days.

---

## Go / No-Go Framework

The preorder results feed directly into the Phase 4 decision. The thresholds:

- **GO (5+ of 10 paid):** The ICP is real and willing to pay. Proceed to product work. Produce revised pricing recommendation, revised positioning, and top 3 feature priorities from objection notes and confirmation-email replies.
- **SOFT GO (3-4 of 10 paid):** The ICP exists but is narrower or more price-sensitive than assumed. Two paths: (a) tighten the ICP further using the Strong-vs-Weak patterns from the rubric and re-run Phase 1 with the tightened profile, or (b) test a higher price point with the 3-4 who already paid to find the ceiling.
- **NO-GO (2 or fewer of 10 paid):** The ICP as defined does not convert. Formally pause all feature work. Analyze the disqualifier patterns from Phase 2 to identify who DID show up who wasn't Mark — these are candidate pivot ICPs. Open a fresh brainstorm on those.

**The math must be clean.** Do not count objections-pending as "likely paid." Do not count "let me think about it" as anything other than no_response once the follow-up window closes. Do not include Weak-signal prospects in the denominator to inflate the conversion rate. The number is: paid / asks sent to Strong prospects.

---

## What This Document Does NOT Cover

- Who qualifies as a prospect — see `icp.md`
- How to conduct the interview — see `interview-guide.md`
- How to score the interview — see `rubric.md`
- The full Phase 4 decision analysis — see Phase 4 in the customer discovery action plan
