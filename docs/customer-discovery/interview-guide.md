# Interview Guide — 30-Minute Zoom Protocol

## Overview

This guide scripts a 30-minute customer discovery interview using the Mom Test methodology. Every question is backward-looking (past behavior only). There are no hypotheticals, no product descriptions, and no mention of Margin Invest until the closing ask — and only then if the prospect qualifies.

**The one rule:** If you catch yourself describing what you're building, stop. Redirect to their experience. The interview is about THEIR past, not YOUR future.

---

## Anonymization Rules (added 2026-04-27 per pressure-test E2)

Apply at capture time, not later. The transcript file you write during/after the call must be anonymized as you go — not cleaned up post-hoc.

- **First name only** in the transcript filename and content (`transcripts/03-firstname.md`, never the prospect's handle or last name).
- **Tickers**: replace with `$TICKER_A`, `$TICKER_B`, `$TICKER_C` ... assigned in order of mention. Keep a private mental note of which letter maps to which ticker; never write the mapping to a committed file.
- **Dollar amounts**: bucket as `($1-5K)`, `($5-20K)`, `($20-100K)`, `($100K+)`. Do not record exact figures.
- **AUM**: bucket using the same scale.
- **Brokerage names**: keep generic — "major retail brokerage", "specialty broker", "international broker." Do NOT record Schwab / Fidelity / IBKR / etc. by name.
- **Real handle**: stays in `pipeline.csv` only. Do NOT reference the handle in the transcript.

The pipeline.csv file is the single document that maps real handle ↔ first name. Per the PII retention policy in `action-plan.md`, transcripts (and pipeline.csv data rows) are deleted 30 days after `decision.md` is committed.

---

## Before the Call

1. Review the prospect's entry in `pipeline.csv` — know their source, the post that qualified them, and why they matched.
2. Open this guide on a second screen. Keep the five questions visible.
3. Open a blank copy of the transcript template at `transcripts/[NN]-[firstname].md` (see template below).
4. Set a timer for 30 minutes. Respect their time.

---

## Call Structure

| Block | Duration | Purpose |
|-------|----------|---------|
| Opening | 2 min | Frame the call, set expectations, build rapport |
| Disqualifier check | 2 min | Verify they match the ICP before investing 20 minutes |
| Five questions | 20 min | ~4 min each, scar tissue and spend first |
| Closing | 5 min | Preorder ask (if qualified) or graceful end |
| Buffer | 1 min | Overrun cushion |

---

## Opening (2 minutes)

> "Thanks for making time. I'm researching how serious stock investors do their research — what works, what doesn't, what's missing. I'm not selling anything on this call. I just want to learn from how you do it. There are no right answers — I'm most interested in specific examples from your actual experience. Cool if we jump in?"

**What this does:** Frames you as a researcher, not a salesperson. Sets the expectation that you want specifics, not opinions. "Cool if we jump in?" transfers control to them.

**What NOT to say:**
- Don't mention "startup," "product," "app," or "tool I'm building"
- Don't say "I think there's a gap in the market" — that's leading
- Don't apologize for taking their time — you're offering $50 for it

### Consent script (added 2026-04-27 per pressure-test E2)

Before the disqualifier check or any of the five questions, say verbatim:

> "Quick housekeeping before we start: I take notes that I store in a private code repository so I can review patterns later. I'll use a first name only and won't store your handle or specific holdings — is that OK?"

**Wait for verbal yes.** Don't interpret silence as consent.

**If the prospect declines**: thank them, end the call politely. Do NOT run the disqualifier check or 5 questions. Mark in `pipeline.csv` as "consent declined." NO gift paid (per gift payout rule below).

**If the prospect asks for clarification**: keep it short. "Just a private working file — you'd be one of about 15 people I'm talking to. I won't share anything with anyone else and I'll delete the notes after I make my decision." If still uncomfortable, end the call.

---

## Disqualifier Check (2 minutes)

> "Before we dive in — just to make sure I'm talking to the right person — roughly how is your portfolio set up? Mostly individual stocks, mostly funds, some mix?"

This single question naturally surfaces their allocation (active vs. passive), their primary activity (stocks vs. options/crypto), and their level of engagement. Listen for kill signals defined in `icp.md`:

- Entire portfolio is passive — thank them, end call, send gift
- Primary activity is options/crypto — thank them, end call, send gift
- Professional analyst with Bloomberg — thank them, end call, send gift

If they mention a mix (e.g., "mostly index funds but I actively manage about $150K"), that's fine — follow up: "Tell me about the active part. What does that look like?"

If needed, ask: "And roughly, do you know what you paid for your biggest positions?" If they can't answer, they're not engaged enough — end gracefully.

**Do NOT run through all five disqualifiers as a checklist.** Weave them into the conversation. If the opening answer is clearly qualified ("I manage about $200K in individual stocks, mostly value names"), skip the follow-ups and move to questions.

### Disqualified-prospect 5-min probe (added 2026-04-27 per pressure-test V3)

If the disqualifier check fails (passive-only, options/crypto primary, professional analyst, can't name cost basis on top 3):

1. Don't end the call yet. Pivot:

> "Got it — sounds like our usual conversation isn't quite aimed at how you invest. If you have a few more minutes, I'd love a quick read on the tools you DO use and what you wish existed."

2. Run the 3-question probe (5 min max):
   - "What tools do you currently use to manage or research investments?"
   - "What's a workflow that frustrates you?"
   - "What would you pay for if it existed?"

3. Capture answers in `docs/customer-discovery/disqualified-log.md` (one row per disqualified-but-probed call).

4. Pay the $50 gift (kept-promise rule, see gift payout rule below).

5. Thank them, end warmly. Do NOT make the preorder ask.

**Why this matters:** the Phase 4 NO-GO branch wants to identify alternative ICPs from disqualifier patterns. Without the probe, we have no data on who showed up that wasn't Mark. The probe rescues the NO-GO pivot path.

---

## Five Questions (20 minutes)

### Q1 — Scar Tissue (emotional motivation to pay)

> "Can you tell me about a specific stock where you lost real money — and looking back, there was a signal you wish you'd caught earlier?"

**Why this is first:** Emotional motivation is the strongest predictor of willingness to pay for a prevention tool. If they can't name a specific loss with a specific missed signal, their pain is abstract — and abstract pain doesn't convert to $49/month.

**What you're listening for:**
- A specific ticker (not "I've had some losses")
- An approximate dollar amount (shows the wound is real)
- A specific signal they missed (deteriorating FCF, accounting red flag, insider selling, sector headwind)
- Emotion — do they still feel it?

**Follow-up:** "What would have had to be different in your process for you to catch that?"

**If they deflect** ("Oh, everyone loses money sometimes"): Push gently once — "Sure, but is there one that still bugs you? One where you think, if I'd just looked at X, I would have gotten out?" If they still can't name one, note it. This is a Weak signal on the rubric.

---

### Q2 — Existing Spend (proven willingness to pay)

> "Walk me through the tools and subscriptions you use for stock research. Which ones do you pay for, and is there anything they don't do that bugs you?"

**Why this is second:** This validates both ability and willingness to pay. You need them to name specific tools AND specific gaps — unprompted. If they pay $0/month for tools, the $49 preorder ask faces a "first dollar" problem that's much harder than a consolidation play.

**What you're listening for:**
- Specific tool names and prices (Finviz Elite $25, Koyfin $39, etc.)
- Total monthly spend (Strong signal if >= $30/month)
- Specific gaps — things they wish their tools did but don't
- Workarounds they've built around those gaps

**Follow-up:** "If you could fix one thing about [tool they named], what would it be?"

**If they only use free tools:** Don't judge. Ask: "Have you ever tried a paid tool and decided it wasn't worth it?" Their answer tells you whether the barrier is price sensitivity or lack of a compelling offering.

---

### Q3 — Workflow Archaeology (process depth, ritual, workarounds)

> "Take me through the last time you decided to buy a specific stock — from first hearing about it to actually placing the order. What did you do step by step?"

**Why this is third:** This is the richest question. A good answer reveals their ritual (how often, how long), their process (structured or ad hoc), their data sources, their workarounds, and their confidence gaps — all in one narrative. It does the work of three separate questions.

**What you're listening for:**
- Number of discrete steps (Strong = 5+, each with a specific data source)
- Time investment (hours per week on research)
- Repeatability — does this sound like something they do every time, or was this a one-off?
- Where they got stuck or felt uncertain — this is the gap
- Tools mentioned — cross-reference with Q2

**Follow-up:** "Where in that process did you feel least confident?"

**If they give a vague answer** ("I just look at the fundamentals and decide"): Push for specifics — "Can you pick a recent one? What was the ticker? Walk me through what you actually did, step by step." If they still can't get specific, their process is ad hoc — note it as Weak on the rubric.

---

### Q4 — Cobble Probe (intensity of personal system investment)

> "You mentioned [tool/spreadsheet/process from Q3]. How much time have you put into setting that up? Has it changed a lot over time?"

**This question is conditional.** Only ask if Q3 didn't already go deep on their personal system. If Q3 produced a detailed answer about their spreadsheet/screener/checklist and how it evolved, skip Q4 and give the extra time to Q5.

**What you're listening for:**
- Time invested — hours, not minutes. "I spent a weekend building it" vs. "I just saved a screener"
- Evolution — has it changed over time? Multiple iterations = high investment
- Specificity — can they describe columns, filters, rules, or criteria?

**If Q3 already covered this:** Skip to Q5. Say: "You actually already answered my next question when you described your [spreadsheet/process]. Let me ask you something different."

---

### Q5 — Switching Trigger (purchase behavior prediction)

> "Think about the last research tool or subscription you started paying for. What specifically made you pull the trigger — what were you doing before, and what changed?"

**Why this is last:** This directly predicts whether they'll convert on the preorder ask. You're asking them to reconstruct a past buying decision: the trigger, the pain that crossed the threshold, the alternative they abandoned. Their answer is a template for how they'll decide about Margin Invest.

**What you're listening for:**
- Speed of decision (Strong = < 2 weeks from awareness to payment)
- The trigger — was it a specific failure, a recommendation, a free trial, or gradual frustration?
- What they were doing before (the incumbent they replaced)
- Whether they've switched tools more than once in the past 2 years (shows willingness to change)

**Follow-up:** "How long did you think about it before paying?"

**If they've never paid for a research tool:** This is a Kill signal on the rubric. Note it. Don't push — just ask: "What's kept you from paying for one?" Their answer tells you whether the barrier is price sensitivity, satisfaction with free tools, or distrust of paid offerings.

---

## Closing (5 minutes)

### If the prospect scored strong (you'll feel it during the call)

Strong signals: specific loss story with real emotion, $30+/month in tools, 5+ step process, built/customized their own system, named a specific gap, switched tools recently.

> "This has been really helpful. I'll be honest with you — I am working on something in this space. I'm not ready to show it yet, but based on what you've told me, you're exactly the kind of person I'm building it for. In about two weeks I'm opening a small founder beta — $49 a month, cancel anytime. Would you want early access?"

**If they say yes:** "Great — I'll send you a link after this call. Thanks for being open to it." Do NOT describe features. Do NOT show a demo. Send the Stripe link in a follow-up message (see `preorder-test.md`).

**If they hesitate:** "Totally fair. Can I follow up by email when it's ready?" Get their email. Move on. Do not pitch.

**If they ask "what does it do?":** Give the one-liner only: "It's a forensic equity scoring engine — deterministic scoring with accounting red-flag detection. I'll send you more detail in the follow-up." Then stop. Do not elaborate.

### If the prospect scored weak or was disqualified

> "This was really helpful — I appreciate you walking me through how you think about this stuff. I'll send over the [gift card / charity donation] today. Thanks again."

End warmly. Do not make the preorder ask. Do not mention what you're building.

---

## $50 Gift Payout Rule (added 2026-04-27 per pressure-test F4)

The gift is paid AFTER the call ends, only if one of:

1. **Qualified-and-completed call**: disqualifier check passed, call ran ≥25 minutes, preorder ask delivered if eligible (or graceful weak-signal close).
2. **Disqualified-but-probed call**: disqualifier check failed, BUT the 5-min probe (above) was completed and captured in `disqualified-log.md`.

**NO gift paid** for:
- Consent declined (call ended at consent step)
- Ghosted (no-show, no rescheduling response within 7 days)
- Call ended <25 minutes for reasons other than disqualified-and-probed
- Disqualified-and-no-probe (prospect declined the probe pivot)

**State the rule** in:
- The recruitment DM template (so the prospect knows the conditions before agreeing to call)
- The interview opening (so the conditions are reaffirmed before the call starts)

This reframes the gift from "pay for time" to "pay for completed signal." It removes the moral-hazard incentive for a prospect to fake-qualify just to collect.

**Payment mechanism**: prospect's choice — Venmo, PayPal, Stripe transfer, or charity donation in their name. Confirm sent before marking `gift_paid_date` in `pipeline.csv`.

---

## Post-Call Red-Flag Self-Check

Immediately after hanging up, before you do anything else, answer these three questions in the transcript file:

1. **Did I describe features?** If yes, flag the interview. The prospect's preorder decision is contaminated by product knowledge, not just their pain.
2. **Did I lead any question?** If yes, which one? Note the moment. A led question produces unreliable data for that signal.
3. **Did I feel myself selling during the closing?** If yes, discount the preorder outcome. Social selling inflates yes-rates.

---

## Transcript Template

Create one file per interview at `docs/customer-discovery/transcripts/[NN]-[firstname].md`:

```
# Interview [NN] — [Firstname]

**Date:** [YYYY-MM-DD]
**Source:** [Reddit / X / Substack]
**Qualification post:** [URL or description of the post that qualified them]
**Duration:** [minutes]

---

## Disqualifier Check

- Portfolio setup: [their answer]
- Kill signals fired: [none / which one]

---

## Q1 — Scar Tissue

**Their answer:**
[Verbatim or near-verbatim notes]

**Key quote:**
> "[Exact words]"

**Follow-up answer:**
[Notes]

---

## Q2 — Existing Spend

**Their answer:**
[Verbatim or near-verbatim notes]

**Tools named:** [tool — $X/mo, tool — $X/mo]
**Total monthly spend:** $[X]
**Gaps mentioned:** [specific gaps]

**Key quote:**
> "[Exact words]"

---

## Q3 — Workflow Archaeology

**Their answer:**
[Verbatim or near-verbatim notes. Capture each step.]

**Steps identified:**
1. [step]
2. [step]
...

**Key quote:**
> "[Exact words]"

**Follow-up — least confident moment:**
[Notes]

---

## Q4 — Cobble Probe

**Asked?** [Yes / Skipped — covered in Q3]

**Their answer:**
[Notes]

**Key quote:**
> "[Exact words]"

---

## Q5 — Switching Trigger

**Their answer:**
[Notes]

**Last tool adopted:** [tool name]
**Time to decision:** [days/weeks/months]
**Trigger:** [specific failure / recommendation / free trial / frustration]

**Key quote:**
> "[Exact words]"

---

## Closing

**Preorder ask made?** [Yes / No — weak/disqualified]
**Response:** [interested / hesitant / declined / N/A]
**Follow-up email collected?** [Yes — address / No]

---

## Red-Flag Self-Check

- Did I describe features? [Yes — details / No]
- Did I lead any question? [Yes — which one, what I said / No]
- Did I feel myself selling? [Yes — when / No]

---

## Raw Notes

[Anything else that came up, surprises, things that don't fit the structure above]
```

---

## What This Document Does NOT Cover

- Who to interview — see `icp.md` for the persona and recruitment sources
- How to score the interview — see `rubric.md` for the six-signal rubric
- What to do with the scores — see `preorder-test.md` for the preorder protocol
