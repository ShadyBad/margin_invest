# Beta Access Email Template — Day 35

**Drafted**: 2026-04-27 (during Pre-flight)
**Status**: Pre-launch reference. Sent to each paid customer on Day 35 once beta access is live. Personalize the bracketed parts before sending.

---

## When to send

- **Day 35 (charge_date + 14 days)**: send the launch email below.
- Send to each paid customer individually (BCC mass-send is fine if format identical, but personalization beats BCC for retention).
- Run the **Day 35 launch checklist** from `beta-deliverable.md` before sending the first email.

---

## Email template

```
Subject: You're in — Margin Invest Founder Beta access

Hi [first name],

The Founder Beta is live. You're one of [N] founders who bet on this early — thank you.

Your access:
  Login URL: https://www.margin-invest.com/login
  Email: [their email — pre-filled, no need to remember]
  Password reset: use the "Forgot password" link to set yours on first login

Where to start (in this order):
  1. Log in and complete the onboarding flow (~3 min). It walks you through the dashboard and how to read the scores.
  2. Open /asset/AAPL (or any ticker you care about) — that's the per-stock view with the full forensic breakdown.
  3. Try the backtesting tool at /backtesting if you want to see how the scoring would have performed on a historical universe.

What's in scope:
  Everything documented at [link to beta-deliverable.md or public-readable copy]
  Quick version: ~5,300 US equities, daily price refresh, quarterly fundamentals, 5-factor composite scoring, 6-filter forensic elimination, 13F smart-money tracking, asset detail with full audit trail, backtesting tool.

What's not in scope (yet):
  Mobile app, intraday quotes, options/futures/crypto, international, custom portfolio P&L, broker integration, push alerts.

Two things you can do right now that I'd love your honest reaction on:
  1. Reply to this email with the FIRST thing you tried after onboarding. I want to know what you reached for.
  2. If you find ANY data that looks wrong (a score that surprises you, a filter result that doesn't match your read of the company), reply with the ticker. I'll investigate within 48 hours.

Cancel anytime: self-serve at /settings → Billing portal. No questions asked.

Support: reply to this email. I read everything personally during the beta.

— [Your name]
Founder, Margin Invest
```

---

## Personalization variables

Before sending each email, fill these:

| Variable | Source |
|---|---|
| `[first name]` | Stripe Checkout session data, OR `pipeline.csv` |
| `[N]` | Total paid customers from `preorder-test-results.md` (e.g., "5") |
| `[their email]` | Stripe Checkout session data |
| `[link to beta-deliverable.md or public-readable copy]` | Whatever URL you set up in Phase 3 prep |
| `[Your name]` | Your name |

---

## Rules

- **Send within 6 hours of beta going live on Day 35.** Don't make customers wonder if you forgot.
- **Same wording across all customers** EXCEPT first name and possibly the "first thing you tried" hook (which can reference something specific from their interview if you have it; default to the generic version).
- **Track in `preorder-test-results.md`**: add a `beta_access_sent_date` column. Mark each customer when sent.
- **Reply tracking**: any reply within 48 hours of access goes to the retention monitoring data (Phase 4 Day 51 retention-gate evidence). Capture in a separate file: `docs/customer-discovery/beta-feedback.md` (anonymized).

---

## Specific-interview personalization (optional but better)

If you want stronger retention, reference something from their interview transcript in the email. Replace the generic "Two things you can do right now" with:

```
One thing I'd love your read on:

When we talked, you mentioned [SPECIFIC ANALYTICAL POINT they made — quote anonymized words]. The closest thing in the beta to that is [SPECIFIC PAGE OR FEATURE]. Try it — does it match how you actually do that step in your process? Reply with what's missing or what you'd change.
```

This costs you ~5 min per customer (re-reading their transcript) but signals you remember them as a person, not a Stripe row. Mark in `pipeline.csv` notes column whether you sent the personalized variant.

---

## Failure-mode handling

### Customer email bounces

- Check Stripe Checkout email for typos
- Try alternative contact (the recruitment-channel handle from `pipeline.csv`)
- If unreachable: refund the subscription proactively. Better to refund than to have a paid customer who can't access.

### Customer reports access broken

- Drop everything; investigate within 2 hours
- Common issues: wrong email in Stripe (typo), magic-link sender domain issues (DKIM/SPF), MFA setup loop
- Have a known-good email template ready: "Sorry — found the issue, please try again here: [URL]"

### Customer cancels within 24 hours of access

- Send a non-pushy follow-up: "Quick question — was there something specific that didn't work, or did the scope just not match what you expected? No pressure to reply, but useful for me to learn."
- Capture answer in `beta-feedback.md` regardless of reply
- Do NOT offer a discount or promo to retain. Cancellations within 24h are signal, not problems to solve.

---

## Day 51 retention check email (sent only to retained customers)

If a customer is still active at Day 51 (passed the second billing cycle), send a brief check-in:

```
Subject: Quick check-in — month 2 of Margin Invest

Hi [first name],

You're past the first month. Two questions, one minute each:

1. What's the ONE thing in Margin Invest that's been most useful to you so far?
2. What's the ONE thing that's still missing or feels off?

Reply when you have a sec — your answer shapes what I build next.

— [Your name]
```

This data is gold for retention-gate analysis AND committed Phase 5 priorities. Not optional if you want a real read on retention drivers.
