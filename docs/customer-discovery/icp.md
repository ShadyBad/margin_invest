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

- Interview questions and protocol — see `interview-guide.md`
- How to score interview responses — see `rubric.md`
- The preorder ask and Stripe setup — see `preorder-test.md`
- Phases 1-5 execution — see the customer discovery action plan (separate document)
