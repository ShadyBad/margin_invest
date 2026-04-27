# Customer Discovery Phase 0 — Scope Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce four customer discovery artifacts under `docs/customer-discovery/` that lock the ICP, interview protocol, scoring rubric, and preorder test before any outreach begins.

**Architecture:** Four standalone markdown documents. No code changes, no dependencies between files. Each artifact is self-contained and readable by someone who hasn't seen the spec.

**Tech Stack:** Markdown only. No code.

**Spec:** `docs/superpowers/specs/2026-04-26-customer-discovery-phase0-design.md`

---

### Task 1: Create directory and ICP document

**Files:**
- Create: `docs/customer-discovery/icp.md`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p docs/customer-discovery
```

- [ ] **Step 2: Write `icp.md`**

Create `docs/customer-discovery/icp.md` with the following content:

```markdown
# Ideal Customer Profile — "Mark"

## Overview

This document defines the target customer for Margin Invest's customer discovery sprint. The persona, disqualifiers, and recruitment sources below were validated in the Phase 0 design spec (`docs/superpowers/specs/2026-04-26-customer-discovery-phase0-design.md`).

**Key design choice — Spectrum Mark:** The ICP uses "has a defined, repeatable personal system" rather than "has built their own tool." A Google Sheet, a heavily customized screener, a written checklist, or a Python script all qualify. The rubric (see `rubric.md`) scores intensity of investment in the system, not its form.

---

## The Persona — Mark Hendricks, 42

Mark is a VP of Operations at a mid-size logistics company in Austin, TX. Investing is not his job — it's his craft.

- **Portfolio:** $320K at Fidelity. ~$200K in VTI/VXUS as a core allocation. ~$120K actively managed in individual US equities. The active sleeve is where he spends his time and attention.
- **Tool spend:** $72/month — Koyfin Pro ($39), Finviz Elite ($25), Seeking Alpha ($8/mo on annual promo).
- **Ritual:** Every Saturday, 7-9am. Coffee, laptop, no distractions. Reviews existing positions for red flags. Runs his Finviz screener for new candidates. Reads 10-Ks on EDGAR for anything in his pipeline. Every other week, does a deep dive on one new candidate.
- **Personal system:** A Google Sheet with 47 rows — his stock "pipeline." Columns: ticker, ROIC trend (3yr), debt/equity, management tenure, a custom "quality score" formula he reverse-engineered from What Works on Wall Street. He also has a OneNote with his decision rules written out and saved Finviz screens for each stage of his pipeline.
- **The wound:** Held GE through 2017-2018. "The dividend yield looked safe." Missed three quarters of deteriorating free cash flow and increasingly opaque segment reporting. Lost $38K. Now obsessively checks FCF coverage and accounting transparency before any new position. This is the scar that made him systematic.
- **What he doesn't do:** He doesn't code. He's not on fintwit. He doesn't write about investing publicly. He reads The Bear Cave and Yet Another Value Blog but doesn't comment. He is a consumer of forensic analysis, not a producer.

### Why Mark pays $49/month

Mark already pays $72/month across three tools and is still manually bridging gaps between them. His Saturday ritual exists because no single tool does what he needs. He has a specific, named wound that makes fraud detection and accounting quality personally important — not abstractly interesting. He has demonstrated willingness to pay, willingness to build systems, and a recurring time investment. The $49 ask is a consolidation of spend he already makes, aimed at a gap he already feels.

---

## Qualifying Criteria

A prospect qualifies as a "Mark" if they meet ALL of the following:

1. **Age 30-60** — behavioral markers matter more than demographics, but this range captures the career stage where self-directed investing becomes serious
2. **$100K+ in actively managed individual stocks** — this is the active sleeve, not total portfolio. Core index allocations don't count. A $400K portfolio with $150K active qualifies.
3. **Pays $30+/month on investing research tools** — proves willingness to spend on the problem (scored in rubric; $0/month is a soft disqualifier, not an automatic kill)
4. **Has a recurring investing ritual of 1+ hours/week** — not a one-time research binge, but a repeatable cadence
5. **Has a defined personal system** — spreadsheet, customized screener, written checklist, script, or any other artifact they've invested hours building and refining
6. **Can name a specific stock loss tied to a missed signal** — the wound that makes systematic analysis emotionally important, not just intellectually interesting

---

## Disqualifiers

Run these conversationally at the start of each interview. Weave into rapport — don't read them as a checklist.

**Opening line:**
> "Before we dive in — just to make sure I'm talking to the right person — roughly how is your portfolio set up? Mostly individual stocks, mostly funds, some mix?"

This single question naturally surfaces answers to disqualifiers 1, 2, and 5.

| # | Question | Kill if... | Notes |
|---|----------|------------|-------|
| 1 | "Is your entire portfolio in index funds, robo-advisors, or target-date funds?" | Yes — entire portfolio is passive | Core-and-explore is fine. Only kill if there is zero active sleeve. |
| 2 | "Is options or crypto trading your main investing activity?" | Yes — primary activity is derivatives or crypto | Occasional options use is fine. Kill if it's the main thing. |
| 3 | "Do you work as a sell-side analyst, fund manager, or have Bloomberg/FactSet through your job?" | Yes — professional access | Different product category. They need institutional tools, not Margin Invest. |
| 4 | "Can you tell me roughly what you paid for your three largest holdings?" | Can't answer | Not engaged enough to know their own cost basis. |
| 5 | "Do you pay for any investing research tools?" | Soft flag if $0/month | Don't kill on this alone. Flag it and let the rubric score it. If ritual and wound are both strong, $0 spend may just mean they haven't found a tool worth paying for yet. |

If any kill-signal fires: thank them, pay the $50 gift card or charity donation, end the call gracefully. Don't waste their time.

---

## Recruitment Sources

### Source 1: Reddit

**Communities:** r/SecurityAnalysis, r/ValueInvesting, r/stocks

**What to look for:** Users who post detailed stock analysis (not memes or one-liners), mention specific financial metrics (ROIC, FCF, Beneish M-Score, accruals, Altman Z), and discuss their research process.

**Search queries to run manually:**
- `site:reddit.com/r/SecurityAnalysis "my process" OR "my approach" OR "how I evaluate"`
- `site:reddit.com/r/ValueInvesting "spreadsheet" OR "screener" OR "watchlist" AND ("ROIC" OR "FCF" OR "free cash flow")`
- `site:reddit.com/r/stocks "I pay for" OR "paying for" AND ("Finviz" OR "Koyfin" OR "Stock Rover" OR "TIKR" OR "Seeking Alpha")`
- `site:reddit.com/r/SecurityAnalysis "lost money" OR "lesson learned" OR "mistake" AND "should have"`

**Qualifying signals in posts:** References to specific metrics, screenshots of spreadsheets or screener setups, comments describing multi-step research processes, mentions of tool subscriptions.

**Disqualifying signals in posts:** "To the moon" language, options chain screenshots, crypto discussion, posts that are purely about price targets without fundamental analysis.

### Source 2: Fintwit / X

**What to look for:** Accounts with 200-5,000 followers who post original stock analysis with their own data tables, charts, or screenshots of spreadsheets/screeners. NOT influencers (>10K followers = content creator with different motivations).

**Search queries to run manually:**
- `"$AAPL ROIC" OR "$MSFT ROIC" OR "$GOOGL ROIC" filter:has_image` (people posting their own analysis with screenshots)
- `"my watchlist" OR "my process" OR "my screener" ("Finviz" OR "Koyfin" OR "Stock Rover")`
- `"risk factors" OR "10-K" OR "Beneish" OR "accruals quality" filter:has_image`

**Qualifying signals:** Original data tables (not retweets of hedge fund PMs), screenshots of their own spreadsheet or screener, threads describing their research process step by step.

**Disqualifying signals:** >10K followers, primarily retweets/commentary, options flow content, "subscribe to my newsletter" in bio, blue-check media figures.

### Source 3: Substack / Blog Comment Sections

**What to look for:** Readers (not authors) who leave detailed, substantive comments on forensic accounting or deep-value investing newsletters. These people consume serious analysis, engage deeply enough to write multi-paragraph comments, but are NOT content creators themselves.

**Newsletters to monitor:**
- The Bear Cave (short-selling, accounting fraud)
- Yet Another Value Blog (deep value, special situations)
- Kailash Concepts (quantitative value)
- Tobias Carlisle / The Acquirer's Multiple (deep value, systematic)
- Greenbackd (discontinued but archived comments are a rich source)

**What qualifies a commenter:** References their own analysis or portfolio decisions, pushes back on the author with specific data, mentions tools they use, describes their process. Multi-paragraph comments that show independent thinking.

**What disqualifies:** One-line reactions ("Great post!"), promotional comments linking to their own content, comments that only agree without adding analysis.

---

## What This Document Does NOT Cover

- Interview questions and protocol → see `interview-guide.md`
- How to score interview responses → see `rubric.md`
- The preorder ask and Stripe setup → see `preorder-test.md`
- Phases 1-5 execution → see the customer discovery action plan (separate document)
```

- [ ] **Step 3: Commit**

```bash
git add docs/customer-discovery/icp.md
git commit -m "docs(discovery): add ICP definition — Spectrum Mark persona, disqualifiers, 3 recruitment sources"
```

---

### Task 2: Create interview guide

**Files:**
- Create: `docs/customer-discovery/interview-guide.md`

- [ ] **Step 1: Write `interview-guide.md`**

Create `docs/customer-discovery/interview-guide.md` with the following content:

```markdown
# Interview Guide — 30-Minute Zoom Protocol

## Overview

This guide scripts a 30-minute customer discovery interview using the Mom Test methodology. Every question is backward-looking (past behavior only). There are no hypotheticals, no product descriptions, and no mention of Margin Invest until the closing ask — and only then if the prospect qualifies.

**The one rule:** If you catch yourself describing what you're building, stop. Redirect to their experience. The interview is about THEIR past, not YOUR future.

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

---

## Disqualifier Check (2 minutes)

> "Before we dive in — just to make sure I'm talking to the right person — roughly how is your portfolio set up? Mostly individual stocks, mostly funds, some mix?"

This single question naturally surfaces their allocation (active vs. passive), their primary activity (stocks vs. options/crypto), and their level of engagement. Listen for kill signals defined in `icp.md`:

- Entire portfolio is passive → thank them, end call, send gift
- Primary activity is options/crypto → thank them, end call, send gift
- Professional analyst with Bloomberg → thank them, end call, send gift

If they mention a mix (e.g., "mostly index funds but I actively manage about $150K"), that's fine — follow up: "Tell me about the active part. What does that look like?"

If needed, ask: "And roughly, do you know what you paid for your biggest positions?" If they can't answer, they're not engaged enough — end gracefully.

**Do NOT run through all five disqualifiers as a checklist.** Weave them into the conversation. If the opening answer is clearly qualified ("I manage about $200K in individual stocks, mostly value names"), skip the follow-ups and move to questions.

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

- Who to interview → see `icp.md` for the persona and recruitment sources
- How to score the interview → see `rubric.md` for the six-signal rubric
- What to do with the scores → see `preorder-test.md` for the preorder protocol
```

- [ ] **Step 2: Commit**

```bash
git add docs/customer-discovery/interview-guide.md
git commit -m "docs(discovery): add Mom Test interview guide — 5 questions, Zoom protocol, transcript template"
```

---

### Task 3: Create scoring rubric

**Files:**
- Create: `docs/customer-discovery/rubric.md`

- [ ] **Step 1: Write `rubric.md`**

Create `docs/customer-discovery/rubric.md` with the following content:

```markdown
# Scoring Rubric — Six-Signal Scorecard

## Overview

Score every interview against these six signals. Each signal maps to a specific interview question. The rubric is evidence-based: every Strong signal requires a direct quote from the transcript. No quote, no Strong.

**Why evidence-based:** After a friendly 30-minute conversation, it's natural to feel positive about the prospect. The quote requirement prevents you from inflating scores based on vibes. If you can't point to their exact words, the signal is Weak.

---

## The Six Signals

### Signal 1: Specific Loss With Identifiable Missed Signal
**Maps to:** Q1 (Scar Tissue)

| Rating | Criteria | Example |
|--------|----------|---------|
| **Strong** (1 pt) | Names the ticker, the approximate dollar amount, AND the specific signal they missed. All three elements must be present. | "I lost about $38K on GE. I should have seen the free cash flow dropping for three straight quarters, but I was focused on the dividend yield." |
| **Weak** (0 pt) | Vague loss ("I've lost money before"), or names the ticker but can't identify what they missed. | "Yeah I took a hit on GE, it just kept going down." |
| **Kill** (-1 pt) | Can't recall any specific loss. Says investing has "gone pretty well." | "I've been pretty lucky honestly, no major losses." |

---

### Signal 2: Active Tool Spend >= $30/Month
**Maps to:** Q2 (Existing Spend)

| Rating | Criteria | Example |
|--------|----------|---------|
| **Strong** (1 pt) | Names specific tools with specific prices totaling >= $30/month. Unprompted — you didn't suggest the tools. | "I pay $39 for Koyfin and $25 for Finviz Elite. Plus Seeking Alpha when they run a promo." |
| **Weak** (0 pt) | Pays for one tool under $30/month, or uses only free tiers. | "I use the free version of Finviz and pay $10/month for Stock Rover." |
| **Kill** (-1 pt) | Pays for nothing. All research is done with free tools. | "I just use Yahoo Finance and Google. Never saw the point in paying." |

---

### Signal 3: Defined, Repeatable Process
**Maps to:** Q3 (Workflow Archaeology)

| Rating | Criteria | Example |
|--------|----------|---------|
| **Strong** (1 pt) | Walks through their last stock purchase in 5+ concrete steps, each with a specific data source. The process is clearly something they do every time, not a one-off. | "First I screen in Finviz for ROIC > 15%. Then I pull the 10-K and check the cash flow statement. Then I look at the debt schedule. Then I compare it to my quality scorecard. Then I check the chart for entry timing." |
| **Weak** (0 pt) | Has a general approach ("I look at fundamentals then decide") but the steps are vague or change significantly each time. | "I usually look at the financials and read some analyst reports, then decide if it feels right." |
| **Kill** (-1 pt) | No discernible process. Buys on tips, articles, gut feeling, or social media mentions. | "My buddy told me about it and I looked at the chart and it seemed like it was about to break out." |

---

### Signal 4: Personal System Investment
**Maps to:** Q3 or Q4 (Workflow Archaeology / Cobble Probe)

| Rating | Criteria | Example |
|--------|----------|---------|
| **Strong** (1 pt) | Has built or heavily customized a personal tool — spreadsheet, screener configuration, written checklist, script — AND can describe how it has evolved over time. Time invested is measured in hours, not minutes. | "I've got a Google Sheet I've been refining for about two years. Started with just ROIC and debt/equity, now it's got 12 columns including a custom quality score I derived from O'Shaughnessy." |
| **Weak** (0 pt) | Uses tools out of the box with no customization beyond a saved watchlist or a few bookmarked pages. | "I have a watchlist on Fidelity with my positions and a few I'm watching." |
| **Kill** (-1 pt) | Doesn't track anything. No watchlist, no spreadsheet, no records, no system. | "I just keep it in my head. I know what I own." |

---

### Signal 5: Articulated Gap in Current Tools
**Maps to:** Q2 or Q3 (Existing Spend / Workflow Archaeology)

| Rating | Criteria | Example |
|--------|----------|---------|
| **Strong** (1 pt) | Names a specific, concrete unmet need unprompted during Q2 or Q3. Something their current tool stack doesn't do that they either work around manually or just tolerate. | "Koyfin is great for financials but it doesn't flag accounting quality issues. I have to manually check the Beneish score on a separate site and then cross-reference." |
| **Weak** (0 pt) | Vague dissatisfaction ("there's always room for improvement") but can't name what's specifically missing. | "I mean, nothing's perfect, but I get by." |
| **Kill** (-1 pt) | Explicitly satisfied. "My current tools do everything I need." | "Honestly, between Koyfin and Finviz I'm pretty set. Can't think of anything missing." |

---

### Signal 6: Purchase Decision Speed
**Maps to:** Q5 (Switching Trigger)

| Rating | Criteria | Example |
|--------|----------|---------|
| **Strong** (1 pt) | Last tool adoption took < 2 weeks from first awareness to payment. OR has switched/adopted tools 2+ times in the past 2 years. Shows willingness to act on a purchasing decision. | "I saw someone mention Koyfin on Twitter, tried the free trial that weekend, and subscribed the next Monday." |
| **Weak** (0 pt) | Took months to decide, or hasn't adopted a new paid tool in 2+ years. Slow to change. | "I thought about getting Stock Rover for like six months before I finally did it." |
| **Kill** (-1 pt) | Has never paid for a research tool in their life. No purchasing precedent exists. | "I've never really felt the need to pay for any of this." |

---

## Scoring Thresholds

- **Strong prospect** — 4+ of 6 signals score Strong AND zero Kill signals. Eligible for the preorder ask.
- **Kill override** — Any prospect with 1+ Kill signal is automatically Weak or Disqualified, regardless of how many Strong signals they have. A Kill means a fundamental mismatch that Strong signals can't overcome.
- **Weak prospect** — 2-3 Strong signals with zero Kill signals. Not eligible for the preorder ask. Still valuable data — capture what segment they represent and what patterns differ from Strong prospects.
- **Disqualified** — 0-1 Strong signals, or 2+ Kill signals. The interview is still useful for understanding who shows up who ISN'T Mark. These patterns feed the NO-GO analysis in Phase 4.

---

## Per-Interview Scorecard Template

Create one file per interview at `docs/customer-discovery/scores/[NN]-[firstname].md`:

```
# Scorecard — [Firstname] (Interview [NN])

**Date:** [YYYY-MM-DD]
**Source:** [Reddit / X / Substack]
**Interviewer confidence:** [High / Medium / Low]

---

## Signals

### Signal 1 — Scar Tissue
**Rating:** [Strong / Weak / Kill]
**Evidence:** > "[Exact quote from transcript]"
**Notes:** [Any context]

### Signal 2 — Tool Spend
**Rating:** [Strong / Weak / Kill]
**Evidence:** > "[Exact quote from transcript]"
**Monthly total:** $[X]
**Notes:** [Any context]

### Signal 3 — Process
**Rating:** [Strong / Weak / Kill]
**Evidence:** > "[Exact quote from transcript]"
**Step count:** [N]
**Notes:** [Any context]

### Signal 4 — System
**Rating:** [Strong / Weak / Kill]
**Evidence:** > "[Exact quote from transcript]"
**System type:** [Spreadsheet / Screener config / Checklist / Script / Other]
**Notes:** [Any context]

### Signal 5 — Gap
**Rating:** [Strong / Weak / Kill]
**Evidence:** > "[Exact quote from transcript]"
**Gap described:** [One-line summary]
**Notes:** [Any context]

### Signal 6 — Switch Speed
**Rating:** [Strong / Weak / Kill]
**Evidence:** > "[Exact quote from transcript]"
**Time to last purchase:** [Days / Weeks / Months / Never]
**Notes:** [Any context]

---

## Summary

| Metric | Value |
|--------|-------|
| Total Strong | [X] / 6 |
| Kill signals | [X] |
| **Verdict** | **[Strong / Weak / Disqualified]** |

---

## Analysis Tags (fill after all 15 interviews complete)

- **Wound type:** [accounting-fraud / macro / sector-rotation / timing / other]
- **Mentioned unprompted:** [13F data / insider transactions / risk factors / forensic metrics / none]
- **Recruitment source quality:** [High / Medium / Low — did this source produce a strong prospect?]

---

## Notes

[Anything that surprised you, patterns you're noticing, things that don't fit the rubric, quotes worth revisiting]
```

---

## Post-Phase 2 Analysis

After all 15 interviews are scored, aggregate the data to answer:

1. **Which recruitment source produced the most Strong prospects?** This determines where to focus if you need to recruit more.
2. **Which signal had the most Kill ratings?** This reveals which part of the ICP is weakest — the market may not have the wound, the spend, or the process you assumed.
3. **What wound types dominate?** If most wounds are accounting/fraud-related, the forensic filters are the right lead feature. If they're macro or timing, the positioning needs adjustment.
4. **What did prospects mention unprompted?** If nobody mentioned 13F data or risk factors, those features have no organic pull — they're builder assumptions, not customer needs.
5. **How many scored Strong?** If fewer than 10, you cannot fill the preorder pipeline from this batch. Either recruit more or make the preorder ask to a mix of Strong + top Weak (and flag the dilution risk in your decision doc).
```

- [ ] **Step 2: Commit**

```bash
git add docs/customer-discovery/rubric.md
git commit -m "docs(discovery): add 6-signal scoring rubric with evidence requirements and scorecard template"
```

---

### Task 4: Create preorder test document

**Files:**
- Create: `docs/customer-discovery/preorder-test.md`

- [ ] **Step 1: Write `preorder-test.md`**

Create `docs/customer-discovery/preorder-test.md` with the following content:

```markdown
# Preorder Test — $49 Founder Beta

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

- Who qualifies as a prospect → see `icp.md`
- How to conduct the interview → see `interview-guide.md`
- How to score the interview → see `rubric.md`
- The full Phase 4 decision analysis → see Phase 4 in the customer discovery action plan
```

- [ ] **Step 2: Commit**

```bash
git add docs/customer-discovery/preorder-test.md
git commit -m "docs(discovery): add preorder test protocol — Stripe config, objection handling, outcome tracker"
```

---

### Task 5: Create empty directories for transcripts and scores

**Files:**
- Create: `docs/customer-discovery/transcripts/.gitkeep`
- Create: `docs/customer-discovery/scores/.gitkeep`

- [ ] **Step 1: Create directories with .gitkeep files**

```bash
mkdir -p docs/customer-discovery/transcripts docs/customer-discovery/scores
touch docs/customer-discovery/transcripts/.gitkeep docs/customer-discovery/scores/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add docs/customer-discovery/transcripts/.gitkeep docs/customer-discovery/scores/.gitkeep
git commit -m "docs(discovery): add empty transcript and scorecard directories for Phase 2"
```

---

### Task 6: Final review — verify all artifacts cross-reference correctly

**Files:**
- Read: all four `docs/customer-discovery/*.md` files

- [ ] **Step 1: Verify cross-references**

Read each file and confirm:
- `icp.md` references `interview-guide.md`, `rubric.md`, and `preorder-test.md` in its "Does NOT Cover" section
- `interview-guide.md` references `icp.md`, `rubric.md`, and `preorder-test.md`
- `rubric.md` references `icp.md` and `preorder-test.md`
- `preorder-test.md` references `icp.md`, `interview-guide.md`, and `rubric.md`
- The transcript template in `interview-guide.md` has fields that map to every rubric signal
- The scorecard template in `rubric.md` has fields that map to every interview question
- The tracker in `preorder-test.md` has a `strong_signals` column that maps to the rubric verdict

- [ ] **Step 2: Fix any broken cross-references**

If any file references a document name or section that doesn't exist in the target file, fix it.

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add docs/customer-discovery/
git commit -m "docs(discovery): fix cross-references across Phase 0 artifacts"
```
