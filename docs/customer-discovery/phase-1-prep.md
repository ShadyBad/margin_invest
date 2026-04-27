# Phase 1 Prep — Search Queries & DM Templates

**Drafted**: 2026-04-27 (during Pre-flight, post-PF.4)
**Status**: Pre-launch reference. Use these as starting drafts; refine per-prospect for personalization.

This document expands on `icp.md` Recruitment Sources with:
- More search query variations (initial + Day-7 fallback)
- DM templates per channel + scenario
- Gift-explanation language verbatim
- Per-channel sending discipline

---

## Search query playbook

### Reddit (primary subs: r/SecurityAnalysis, r/ValueInvesting, r/stocks; secondary: r/investing)

**Initial batch** (use during Days 1-7):

```
site:reddit.com/r/SecurityAnalysis "my process" OR "my approach" OR "how I evaluate"
site:reddit.com/r/ValueInvesting "spreadsheet" OR "screener" AND ("ROIC" OR "FCF")
site:reddit.com/r/stocks "I pay for" AND ("Finviz" OR "Koyfin" OR "Stock Rover" OR "TIKR" OR "Seeking Alpha")
site:reddit.com/r/SecurityAnalysis "lost money" OR "lesson learned" AND "should have"
site:reddit.com/r/ValueInvesting "Beneish" OR "Altman" OR "accruals quality"
site:reddit.com/r/SecurityAnalysis "10-K" OR "risk factors" "I noticed" OR "stood out"
```

**Day-7 fallback batch** (only if <8 scheduled by Day 7):

```
site:reddit.com/r/investing "deep dive" OR "thesis" AND ("ROIC" OR "FCF margin")
site:reddit.com/r/dividends "FCF coverage" OR "payout ratio" AND "concerned"
site:reddit.com/r/StockMarket "watchlist" OR "due diligence" multi-paragraph posts
site:reddit.com/r/ValueInvesting "Buffett" OR "Munger" OR "Greenblatt" + own analysis
site:old.reddit.com/r/SecurityAnalysis past 90 days, sort by top
```

**What to look for in each result**:
- Multi-paragraph posts (not one-liners)
- Specific tickers + specific metrics (not just narrative)
- Mentions of paid tools by name
- Process descriptions ("I screen for X then check Y")
- Loss stories with specific signals missed

**Auto-skip on these signals**:
- "$AAPL going to $300 next year" (no fundamental analysis)
- Options chain screenshots
- Crypto/NFT mentions
- "Subscribe to my newsletter"
- Posts in past 30 days with <5 karma (low engagement signal)

### Twitter / X (FinTwit subset, NOT general)

**Initial batch**:

```
"$AAPL ROIC" OR "$MSFT ROIC" OR "$GOOGL ROIC" filter:has_image (sophisticated solo analysts)
"my watchlist" OR "my screener" ("Finviz" OR "Koyfin" OR "Stock Rover")
"risk factors" OR "10-K" OR "Beneish" OR "accruals quality" filter:has_image
"deep dive" OR "investment thesis" $TICKER (specific tickers in finance-focused accounts)
```

**Day-7 fallback**:

```
("Forensic Investors" OR "Stocktwits Pro") (Twitter Lists curated by FinTwit)
"FCF coverage" OR "free cash flow margin" + own analysis (own = no retweets)
"Beneish M-Score" OR "Sloan accruals" recent 90 days
("$X")  -- search the prospect's most-discussed tickers' replies
```

**Pre-DM filter** (apply BEFORE adding to pipeline):
- Followers: 200-5,000 (small enough to feel founder DM matters; not influencer-tier)
- Posting cadence: 2+ posts/week of original analysis (not retweets)
- Bio: investor/analyst, NOT "trader" / "options" / "newsletter"
- Account age: ≥3 months
- No "subscribe to my Substack" or paid newsletter pitch in bio

**Auto-skip on these signals**:
- Blue check, >10K followers, primarily retweets
- Options-flow content
- Newsletter subscription pitch in bio
- Frequent emoji posts ("🚀", "💎🙌")

### Substack comment sections

**Newsletters to monitor** (in priority order):

1. **The Bear Cave** — Edwin Dorsey's short-selling research; commenters often have forensic-accounting depth
2. **Yet Another Value Blog** — Andrew Walker, deep value, frequent commentary
3. **The Acquirer's Multiple / Tobias Carlisle** — systematic deep value
4. **Kailash Concepts** — quantitative value
5. **Greenbackd** (archived) — Tobias's older blog, comment archive is gold

**Tactic**:
- Open the most recent 5 posts of each newsletter
- Scan comments. Look for:
  - Multi-paragraph commenters
  - Mentions of specific tickers + their own analysis
  - Pushback on the author with data ("I think you're underweighting X because...")
  - Tool mentions in passing ("My Koyfin pulled up...")
- Click commenter profile. If email listed: add to pipeline.
- If no email: skip (no DM mechanism on Substack).

**Day-7 fallback Substacks**:
- The Diff (Byrne Hobart) — broad finance, but sophisticated readers
- Net Interest (Marc Rubinstein) — banking + finance sector
- Doomberg (energy/commodities — different ICP, but sophisticated readers)

---

## DM template playbook

All templates assume:
- Gift offer per channel rules (Reddit/Twitter/Substack: yes; Discord: usually no)
- Personalization: reference a specific post/comment they made (not generic)
- ≤4 sentences total
- No mention of Margin Invest, no product description

### Reddit — Comment-then-DM pattern

**Step 1 — Comment on their post first (24-48 hr before DM)**:

> "Really appreciated the breakdown on [TICKER] — especially [SPECIFIC POINT they made about FCF/ROIC/etc.]. Curious how you got to [SPECIFIC ANALYSIS]?"

Wait for them to reply. Engage genuinely.

**Step 2 — DM after comment engagement**:

> Hey, enjoyed our exchange on [TICKER]. I'm doing some research on how serious self-directed investors actually do their stock research — specifically around [accounting red flags / FCF analysis / their stated topic]. Would you be open to a 30-min call about your process? Happy to send a $50 thank-you (Venmo, PayPal, or charity donation) after a complete call. No pitch — just listening.

**Critical**: state "after a complete call" explicitly. This is the moral-hazard guardrail from interview-guide.md.

### Twitter / X — Follow-then-DM pattern

**Step 1 — Follow + reply substantively (7-14 days before DM)**:

Reply to one of their analyses with a specific question:

> "How are you thinking about [SPECIFIC METRIC] given [SPECIFIC CONTEXT they mentioned]?"

Like 2-3 of their posts. Don't spam-engage.

**Step 2 — DM after they follow back OR after they reply to your reply**:

> Hey [first name from bio if visible] — your work on [TICKER / topic] caught my eye. I'm researching how independent investors actually run their research process. Would you be open to a 30-min call? Happy to send $50 (Venmo/PayPal/charity) after the call wraps. No product pitch on my end — just want to hear how you do it.

### Substack — Cold email (private, outside platform rules)

> Subject: 30 min about how you research stocks?
>
> Hi [first name] —
>
> I came across your comment on [Newsletter post title] where you wrote about [SPECIFIC ANALYTICAL POINT]. The depth caught my attention.
>
> I'm doing customer research on how serious self-directed investors run their analysis — what tools, what rituals, what gaps. Would you be open to a 30-min call? I'll send $50 (Venmo/PayPal/charity, your choice) after a complete call. No product pitch — I'm just trying to learn from how you do it.
>
> Best,
> [Your name]

### When prospect asks "what's this about?"

If they push back before agreeing: keep it minimal.

> "Honestly — I'm researching whether there's a real gap between what tools exist and what serious investors need. Trying to get out of my own head and hear it from people who actually do this. 30 minutes, no pitch, $50 thank-you. Up to you."

**Do NOT** describe Margin Invest. Do NOT explain features. The Mom Test rule applies before the call too.

### When prospect agrees but the gift conditional surprises them

If they say "wait, paid AFTER?":

> "Yeah — just to keep the call honest. I want signal from people who'd genuinely engage, not people who'd say anything for $50 upfront. After we wrap, I send the $50 same-day. No exceptions."

---

## Sending discipline

### Reddit volume cap

- ≤5 DMs per day per Reddit account
- ≤25 DMs per week per account
- Comment-then-DM cycle takes 2-3 days minimum
- Account requirements: >30 days old, >100 link + 100 comment karma, posting history in finance subs

### Twitter volume cap

- ≤10 DMs per day per X account
- Vary message wording each DM (Twitter spam detector flags identical-pattern messages)
- Account requirements: >3 months posting history, real bio + header, prior engagement on finance content

### Substack volume cap

- No platform-imposed cap (private email)
- Practical cap: 10-15 emails per day to keep personalization quality high
- Use a personal email account, not a generic "founder@" alias (cold-email filters)

### Per-day batch checklist

For each day of recruitment:

- [ ] Pick 2-3 channels (rotate; don't burn one channel in one day)
- [ ] Source 10-15 candidate prospects via search queries
- [ ] Filter to 5-10 qualified per ICP rubric
- [ ] Comment-engage on Reddit prospects (Day N-2 work)
- [ ] DM Reddit prospects from Day N-2 comment work (today)
- [ ] DM Twitter prospects (today, follow-engaged)
- [ ] Email Substack prospects (today)
- [ ] Update pipeline.csv with all DM activity
- [ ] Note any auto-rejected/banned/shadowban warnings → adjust per recruitment-channel-rules.md

---

## Day-7 yield gate decision tree

At Day 7, count `scheduled_date` non-empty rows in pipeline.csv:

- **≥8 scheduled**: continue current channels at current cadence.
- **5-7 scheduled**: continue but expand to fallback queries above. Don't change tactics yet.
- **3-4 scheduled**: pause Reddit/Twitter primary channels for 24h to review what's working. Run fallback queries on each. Add 1-2 Day-7 fallback Substacks.
- **0-2 scheduled**: trigger explicit rescope decision. Pick (a) raise gift to $75-100 + re-DM cold prospects with bump, (b) accept rescope to half-scope (8 interviews / 5 paid asks), or (c) pause sprint.

Document the decision in `pipeline.csv` notes column AND in `action-plan.md` leading status section.

---

## Post-Phase 1 acceptance criteria

Before proceeding to Phase 2:

- [ ] 18 calls scheduled (full scope) or 10 (half scope)
- [ ] 100+ prospects in pipeline.csv (full) or 60+ (half)
- [ ] Zero network hires verified
- [ ] Day-7 gate passed or rescoped explicitly
- [ ] All DMs comply with `recruitment-channel-rules.md`
- [ ] No active platform warnings/shadowbans on recruitment accounts
