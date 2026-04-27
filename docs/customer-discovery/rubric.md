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
