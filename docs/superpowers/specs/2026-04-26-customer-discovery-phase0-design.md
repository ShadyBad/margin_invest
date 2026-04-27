# Customer Discovery Phase 0 — Scope Lock Design

**Date:** 2026-04-26
**Objective:** Prove or disprove that a "Mark"-profile customer will pay $49+/month for Margin Invest.
**Decision deadline:** 30 days from kickoff.
**Go signal:** 5+ of 10 qualified prospects complete a paid pre-order.
**Stop signal:** 2 or fewer of 10 pay. Halt all feature work, re-brainstorm ICP.

---

## Phase 0 Deliverables

Four artifacts under `docs/customer-discovery/`:

1. `icp.md` — Persona, disqualifiers, recruitment sources
2. `interview-guide.md` — 30-minute Zoom script with five questions
3. `rubric.md` — Six-signal scoring rubric with thresholds
4. `preorder-test.md` — Preorder ask wording, Stripe requirements, tracker

No code changes in this phase. Artifacts only.

---

## 1. ICP Definition

### Design Decisions

- **Spectrum Mark, not Tight Mark.** The "built their own tool" requirement is relaxed to "has a defined, repeatable personal system" — could be a custom screener, spreadsheet, checklist, or script. The rubric scores intensity of investment, not form of the workaround. This broadens the recruitment pool while the rubric filters for quality.
- **Active sleeve counts.** A prospect with $400K total but $250K in VTI and $150K actively managed is IN. The disqualifier targets people whose *entire* portfolio is passive, not core-and-explore allocators.
- **Age range widened to 30-60.** No evidence that 35-55 is meaningfully different from 30-60 for this persona. The behavioral markers (ritual, spend, wound) are the real filters.
- **Tool spend threshold set at $30/month** for a Strong rubric signal. Some serious investors consolidate into one tool (e.g., Koyfin Pro at $39) rather than stacking three cheap ones. The disqualifier flags $0/month as a soft signal but doesn't kill — the rubric handles granular scoring.

### Persona — Mark Hendricks, 42

- VP of Operations at a mid-size logistics company, Austin TX
- $320K brokerage (Fidelity): ~$200K in VTI/VXUS core, ~$120K actively managed individual stocks
- Pays $72/month: Koyfin Pro ($39), Finviz Elite ($25), Seeking Alpha ($8/mo promo)
- Weekly ritual: Saturday 7-9am. Reviews positions, runs screener, reads 10-Ks on EDGAR. Bi-weekly deep dives on new candidates.
- Personal system: Google Sheet with 47 rows tracking his "pipeline" — ROIC trend, debt/equity, management tenure, a custom quality score formula derived from What Works on Wall Street
- The wound: Held GE through 2017-2018 because "the dividend yield looked safe." Missed deteriorating cash flow and accounting opacity. Lost $38K. Now obsessively checks free cash flow coverage before any position.
- Doesn't code. His system is a spreadsheet + saved Finviz screens + OneNote decision criteria.

### Disqualifiers

Five questions run conversationally at interview start:

1. **Passive-only check:** "Is your entire portfolio in index funds, robo-advisors, or target-date funds?" — Kill if yes (no active sleeve).
2. **Primary activity:** "Is options or crypto trading your main investing activity?" — Kill if yes.
3. **Professional access:** "Do you work as a sell-side analyst, fund manager, or have Bloomberg/FactSet through your job?" — Kill if yes (different product category).
4. **Engagement check:** "Can you tell me roughly what you paid for your three largest holdings?" — Kill if can't (not engaged enough to track cost basis).
5. **Tool spend:** "Do you pay for any investing research tools?" — Soft disqualifier. Flag if $0/month but don't kill if ritual and wound are strong.

### Recruitment Sources

1. **Reddit** — r/SecurityAnalysis, r/ValueInvesting, r/stocks. Filter for users who post detailed analysis, mention specific metrics (ROIC, FCF, Beneish, accruals), and discuss their process. Search queries: "my process for evaluating," "built a spreadsheet," "paying for," "screener setup."

2. **Fintwit / X** — Accounts with 200-5,000 followers posting stock analysis with their own data tables or screenshots. Not influencers (>10K = content creator, different motivation). Search: "$TICKER ROIC" with screenshots, "my watchlist process" threads.

3. **Substack/Blog comment sections** — Readers (not authors) who leave detailed comments on forensic/deep-value newsletters: The Bear Cave, Yet Another Value Blog, Kailash Concepts, Tobias Carlisle. These people consume serious analysis and engage enough to comment but aren't content creators.

---

## 2. Interview Guide

### Design Decisions

- **Pure Mom Test.** No pitch, no demo, no mention of Margin Invest. All five questions are backward-looking (past behavior only). No hypotheticals.
- **Scar tissue and existing-spend lead.** These two questions are the highest-signal predictors of willingness to pay. They go first while the prospect is freshest.
- **Workflow archaeology consolidates three overlapping questions.** The original five (workflow, ritual, cobble, scar tissue, spend) had three questions covering similar ground. Consolidated into one rich workflow question, freeing a slot for the switching trigger question.
- **Cobble probe is conditional.** Only asked if Q3 didn't already surface their workarounds.
- **Switching trigger added.** Backward-looking question about their last tool purchase decision. Directly predicts purchase behavior and reveals the threshold for action.
- **Preorder ask happens async.** Not on the call. Sent via DM/email after, so the decision happens without social pressure.

### Call Structure (30 minutes)

**Opening (2 min):**
> "Thanks for making time. I'm researching how serious stock investors do their research — what works, what doesn't, what's missing. I'm not selling anything on this call. I just want to learn from how you do it. There are no right answers — I'm most interested in specific examples from your actual experience. Cool if we jump in?"

**Disqualifier check (2 min):**
Run the five disqualifiers conversationally, woven into rapport:
> "Before we dive in — just to make sure I'm talking to the right person — roughly how is your portfolio set up? Mostly individual stocks, mostly funds, some mix?"

If any kill-signal fires: thank them, pay the $50 gift/donation, end the call.

**Five Questions (20 min, ~4 min each):**

**Q1 — Scar Tissue** (emotional motivation)
> "Can you tell me about a specific stock where you lost real money — and looking back, there was a signal you wish you'd caught earlier?"

Follow-up: "What would have had to be different in your process for you to catch that?"

**Q2 — Existing Spend** (proven willingness to pay)
> "Walk me through the tools and subscriptions you use for stock research. Which ones do you pay for, and is there anything they don't do that bugs you?"

Follow-up: "If you could fix one thing about [tool they named], what would it be?"

**Q3 — Workflow Archaeology** (process depth + surfaces ritual and workarounds)
> "Take me through the last time you decided to buy a specific stock — from first hearing about it to actually placing the order. What did you do step by step?"

Follow-up: "Where in that process did you feel least confident?"

**Q4 — Cobble Probe** (intensity of personal system investment — conditional)
> "You mentioned [tool/spreadsheet/process from Q3]. How much time have you put into setting that up? Has it changed a lot over time?"

Only ask if Q3 didn't already go deep on their system. If it did, give extra time to Q5.

**Q5 — Switching Trigger** (purchase behavior prediction)
> "Think about the last research tool or subscription you started paying for. What specifically made you pull the trigger — what were you doing before, and what changed?"

Follow-up: "How long did you think about it before paying?"

**Closing (5 min):**

*If strong prospect:*
> "This has been really helpful. I'll be honest with you — I am working on something in this space. I'm not ready to show it yet, but based on what you've told me, you're exactly the kind of person I'm building it for. In about two weeks I'm opening a small founder beta — $49 a month, cancel anytime. Would you want early access?"

If yes: send Stripe link in a follow-up message (not live). If hesitation: "Totally fair. Can I follow up by email when it's ready?" Move on.

*If weak/disqualified prospect:* Thank them, send $50 gift/donation, end warmly.

**Post-call red-flag self-check:**
- Did I describe features? (flag the interview if yes)
- Did I lead any question? (note which one)
- Did I feel myself selling during the closing? (discount preorder outcome if yes)

---

## 3. Scoring Rubric

### Design Decisions

- **Six signals, independently scored.** Each maps to a specific interview question or observable behavior. No composite weighting — just count Strong signals.
- **Evidence-based scoring.** Every Strong signal requires a direct quote from the transcript. No quote, no Strong. This prevents score inflation after friendly conversations.
- **Kill signals are negative.** A Kill on any signal overrides the total count — one Kill means the prospect is not eligible for the preorder ask regardless of Strong count.
- **Post-Phase 2 analysis tags** added to each scorecard for pattern detection across the 15 interviews.

### Six Signals

| # | Signal | Strong (1 pt) | Weak (0 pt) | Kill (-1 pt) |
|---|--------|---------------|-------------|---------------|
| 1 | **Specific loss with identifiable missed signal** | Names the ticker, approximate dollar amount, AND the specific signal they missed. All three elements present. | Vague loss ("I've lost money before") or names ticker but not what they missed. | Can't recall any specific loss. |
| 2 | **Active tool spend >= $30/month** | Names specific tools with prices totaling >= $30/month. Unprompted. | Pays for one tool under $30, or free tiers only. | Pays for nothing. |
| 3 | **Defined, repeatable process** | Walks through last purchase in 5+ concrete steps with specific data sources at each. Process is clearly repeatable, not ad hoc. | General approach ("I look at fundamentals") but vague or inconsistent steps. | No process. Buys on tips or gut. |
| 4 | **Personal system investment** | Has built or heavily customized something (spreadsheet, screener config, checklist, script) AND describes how it evolved over time. Hours invested, not minutes. | Uses tools out of the box. No customization beyond a saved watchlist. | Doesn't track anything. |
| 5 | **Articulated gap in current tools** | Names a specific unmet need unprompted during Q2 or Q3. Something their stack doesn't do that they work around or tolerate. | Vague dissatisfaction but can't name the gap. | "My current tools do everything I need." |
| 6 | **Purchase decision speed** | Last tool adoption took < 2 weeks from awareness to payment, or has switched tools 2+ times in past 2 years. | Took months, or hasn't adopted a new paid tool in 2+ years. | Has never paid for a research tool. |

### Thresholds

- **Strong prospect:** 4+ of 6 Strong AND zero Kill signals. Eligible for preorder ask.
- **Weak prospect:** 2-3 Strong with zero Kill signals. Not eligible for preorder. Capture what segment they represent.
- **Kill override:** Any prospect with 1+ Kill signal is automatically Weak or Disqualified regardless of Strong count. A Kill signal means a fundamental mismatch — even 5 Strong signals can't overcome it.
- **Disqualified:** 0-1 Strong signals, or 2+ Kill signals. Interview still useful for understanding who ISN'T Mark.

### Per-Interview Score Template

```
Prospect: [name]
Date: [date]
Source: [recruitment source]
Interview #: [N of 15]
Interviewer confidence: [high / medium / low]

Signal 1 - Scar tissue:    [Strong / Weak / Kill] — "[exact quote]"
Signal 2 - Tool spend:     [Strong / Weak / Kill] — "[exact quote]"
Signal 3 - Process:        [Strong / Weak / Kill] — "[exact quote]"
Signal 4 - System:         [Strong / Weak / Kill] — "[exact quote]"
Signal 5 - Gap:            [Strong / Weak / Kill] — "[exact quote]"
Signal 6 - Switch speed:   [Strong / Weak / Kill] — "[exact quote]"

Total Strong: [X / 6]
Kill signals: [X]
Verdict: [Strong / Weak / Disqualified]

--- Analysis tags (fill after all 15 complete) ---
Wound type: [accounting-fraud / macro / sector / timing / other]
Mentioned unprompted: [13F data / insider txns / risk factors / forensic metrics / none]
Recruitment source quality: [high / medium / low]

Notes: [surprises, things that don't fit the rubric]
```

---

## 4. Preorder Test

### Design Decisions

- **Async ask, not live.** Sent via DM/email after the call. The social pressure of a live ask inflates yes-rates and produces politeness purchases.
- **Cancel anytime retained.** The friction of entering credit card details and being charged real money is sufficient signal. Optimizing for purity (non-refundable) risks getting zero usable data from a 10-person sample.
- **Personalized message required.** Each ask must reference something specific from THAT prospect's interview. Mass-mailed asks are not allowed.
- **No discounts, ever.** If someone objects on price, capture the number they'd pay. That's data. Discounting corrupts the price signal.
- **One follow-up maximum.** Ask, wait 5 days, one nudge, then mark as no_response. No chasing.
- **Four outcomes only.** Paid / declined / no_response / objection. No "maybe."

### The Ask — Exact Wording

> Subject: Following up from our call
>
> [First name] — thanks again for the conversation on [day]. What you said about [one specific thing from their interview — reference their own words] stuck with me.
>
> I'm building something that directly addresses [the gap they named in Q2 or Q3]. It's called Margin Invest — a forensic equity scoring engine. No opinions, no analyst picks. Deterministic scoring across quality, value, and momentum with six elimination filters that catch accounting red flags before they show up in the stock price.
>
> I'm opening a founder beta to 10 people in two weeks. $49/month, cancel anytime. You'd be one of the first to use it, and I'd build based on your feedback.
>
> If you're in: [Stripe Checkout link]
>
> If you have questions, just reply. No pressure either way — the conversation alone was valuable.

### Stripe Checkout Requirements

- **Product name:** "Margin Invest — Founder Beta"
- **Price:** $49/month recurring subscription
- **Trial period:** 0 days (charged immediately)
- **Collects:** email (required, beta access identifier), name, card
- **Success page:** "You're in. I'll email you when the beta opens in ~2 weeks."
- **Cancel:** Self-serve via Stripe customer portal, linked from confirmation email
- **No coupon codes.** No discounts.
- **Session metadata:** `prospect_name`, `interview_number`, `source` — every payment traces to a scorecard

### Objection Handling

Only respond to objections. Never preempt them.

**Price objection** ("$49 is a lot"):
> "Totally fair. Out of curiosity — what number would feel like a no-brainer for you?"
> Record their answer. Do not offer it.

**Timing objection** ("I'd buy after it's built"):
> "I get that. What specifically would you need to see in the first beta for it to be worth $49 to you?"
> Record their answer. This is a feature priority signal.

**"Let me think about it":**
> "Of course. I'll leave the link open — no deadline."
> One follow-up after 5 days: "Hey [name], just checking — any questions I can answer about the beta?" Then mark no_response.

### Tracker

| prospect | interview_# | score | ask_sent_date | response_date | outcome | amount | objection_type | objection_verbatim | follow_up_sent | notes |
|----------|-------------|-------|---------------|---------------|---------|--------|----------------|--------------------|----------------|-------|
| | | | | | paid / declined / no_response / objection | | price / timing / other / none | | yes / no | |

---

## Go / No-Go Framework

- **GO (5+ of 10 paid):** Proceed to product work with narrowed ICP. Produce revised pricing, revised positioning, top 3 feature priorities from objection notes.
- **SOFT GO (3-4 of 10 paid):** ICP is real but narrower or more expensive. Either tighten ICP and re-run Phase 1, or raise price and re-validate with the 3-4 who paid.
- **NO-GO (2 or fewer paid):** Formally pause all feature work. Identify alternative ICPs from disqualifier patterns. Open fresh brainstorm on those.

---

## Scope Boundaries

- **In scope:** The four artifacts above. No code changes.
- **Out of scope for Phase 0:** Stripe implementation, outreach messages, interview scheduling, product changes.
- **Dependency:** This spec produces the materials. The user's customer discovery action plan (separate document) sequences the execution across Phases 0-5.
