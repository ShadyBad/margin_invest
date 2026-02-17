# Strategic Dominance Analysis & Redesign

**Date:** 2026-02-17
**Status:** Approved
**Type:** Full Strategic Audit + Conversion-Optimized Redesign
**Constraint:** Solo founder + Claude. All recommendations prioritized P0/P1/P2.

---

## 1. Executive Summary

Margin Invest has a genuine competitive moat in its deterministic scoring engine — the 6-factor pipeline, elimination-before-scoring architecture, sector-neutral normalization, and growth-stage weight adjustments are intellectually rigorous in ways most fintech products never attempt.

**The problem is not the engine. The problem is the wrapping.**

The product currently reads as a well-built indie SaaS tool, not as conviction infrastructure for serious capital. Visitors arrive at a landing page that takes ~4 scroll depths to reveal differentiation. They sign up to a dashboard that shows scores but doesn't teach the framework. They leave without forming a mental model of why this is different. There's no activation loop, no habit trigger, no emotional hook that makes the product sticky.

**Current state: B- product with A+ engine.** The gap between engine quality and product experience is the single biggest unlock.

---

## 2. Market Leader Scorecard

| Dimension | Score | Assessment |
|---|---|---|
| First Impression | 6/10 | Reads as sophisticated indie, not market leader. Good typography/spacing discipline but lacks visual depth that signals "serious money lives here." |
| Premium Perception | 5.5/10 | Dark theme + emerald restraint is right. But flat card surfaces, uniform color weight, and lack of data viz richness undercut perception. Login page actively hurts. |
| Conversion Architecture | 4/10 | Biggest weakness. No urgency, no activation hook, no free-tier scarcity. CTAs all go to `/dashboard` with no onboarding flow. |
| Behavioral Stickiness | 3/10 | Almost nonexistent. No reason to return daily. No progress tracking. No alerts. No weekly recap. |
| Competitive Positioning | 6.5/10 | "Conviction infrastructure" framing is genuinely differentiated. Constellation animation and editorial copy tone are unique. Dashboard experience looks like any stock screener. |
| Data Visualization | 5/10 | Percentile bars work but are visually monotone. No sparklines visible on most cards. Everything is the same shade of emerald. |

**Overall: 5/10.** A solid B- that could be an A- with focused, high-leverage changes.

---

## 3. Conversion Killers

### Kill #1: No Onboarding Flow (P0)

Every CTA on the landing page goes directly to `/dashboard`. Zero onboarding. A new user signs up, lands on a dashboard full of tickers they didn't choose, with scores they don't understand, using a framework they haven't been taught. The "aha moment" is left entirely to chance.

**What happens today:**
Landing page -> "Score your first position" -> `/dashboard` -> Wall of stock cards with obscure tickers (ATEYY, ADTTF, TISNF) -> "This isn't for me" -> Bounce.

**What should happen:**
Landing -> Sign up -> "What's in your portfolio?" (enter 3-5 tickers) -> Engine scores them live -> User sees THEIR holdings scored -> Immediate personal relevance -> "I need this for the rest of my portfolio."

### Kill #2: Hero CTA Doesn't Match User Intent (P0)

"Score your first position" is the right copy — but it links to `/dashboard`, which shows pre-computed scores for the full universe. The promise ("score YOUR first position") is broken immediately. The user expected to do something. They got a read-only grid.

### Kill #3: No Urgency or Scarcity in Free Tier (P1)

The free tier (Scout: 3 tickers/month) has zero visible scarcity mechanics. No counter showing "2 of 3 analyses remaining." No nudge when close to the limit. No "your portfolio has 12 more unscored holdings" prompt. The constraint exists in the backend but is invisible in the UI.

### Kill #4: Pricing Section Has No Anchor (P1)

Pricing cards show Free / $29 / $79 with no psychological framing. No "most popular" badge on Operator. No annual discount shown as savings. No crossed-out monthly price. Operator card has a green border but no copy explaining why it's highlighted. Allocator looks identical to Scout except for the price.

### Kill #5: Dashboard Shows No Progress (P1)

No sense of portfolio completeness. No "you've scored 6 of 18 holdings" progress bar. No weekly performance delta. No "your conviction changed on 2 positions this week." The dashboard is a static snapshot with no temporal dimension.

### Kill #6: Login Page Is Pre-Redesign (P1)

Current login page is a flat dark background with full-width OAuth buttons and a gold "Sign In" button that clashes with the emerald design system. Glassmorphism redesign spec exists (`2026-02-17-login-redesign-design.md`) but isn't implemented. This page actively damages premium perception at a critical trust moment.

### Kill #7: No Social Proof Anywhere (P2)

Zero testimonials, zero user counts, zero "trusted by X investors," zero backtest results. The product proves itself through methodology, but there's no external validation. Even one credible data point ("Scoring 2,400+ equities daily") would help.

### Kill #8: Dashboard Cards Are Visually Monotone (P2)

Every stock card uses the same emerald percentile bars, same layout, same visual weight. There's no differentiation between a 91-score exceptional pick and an 82-score high pick at a glance. Everything looks equally important, which means nothing feels important.

---

## 4. Premium Perception Audit

### Typography: 7/10

Inter Tight at the right weights with tight letter-spacing on headlines is solid. The -0.5px tracking on H1 creates confidence. Geist Mono for data is a good choice.

**Gap:** Body text at 15-17px sometimes feels small for premium fintech. Bloomberg uses 13px because density is the product — but Margin isn't a terminal, it's a decision tool. Body copy could go to 16-18px consistently.

### Spacing Rhythm: 7.5/10

Intentional variation in section padding (80px-160px) is one of the strongest design decisions. Creates editorial rhythm most SaaS products never achieve.

**Gap:** Dashboard doesn't inherit this rhythm. Stock cards sit in a uniform grid with identical gaps. The app experience feels "Tailwind default" compared to the landing page's editorial intentionality.

### Color Confidence: 6/10

Emerald-at-10% rule is disciplined and correct. But the result is monochromatic. Dark background, dark cards, dark borders, green as the only accent. Premium products use depth — subtle gradients, layered surfaces, strategic secondary accents for data states.

**Specific issue:** Percentile bars use a 4-tier color system (green/accent/gray/red) but in practice, most visible scores on the dashboard are 65+, so everything appears emerald. Differentiation between "good" and "exceptional" is invisible.

### Depth & Layering: 5/10

Biggest perception gap. Landing page has WebGL background, scroll-driven constellation, animated data panels — genuine depth. Dashboard is flat. Cards sit directly on `bg-primary` with 1px border and no shadow. No elevation hierarchy. Nav floats beautifully but below it, content has no z-axis variation.

**What premium looks like:** Subtle card shadows (`0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)`), background noise texture (already exists in globals.css but barely perceptible on dashboard), graduated surface colors creating visual layers.

### Data Visualization Quality: 5/10

Percentile bars are functional but visually basic — flat rectangles with no end caps, no gradient, no animation on load. Sparkline component exists but shows dashed empty lines on most cards ("Target: N/A"). Price chart uses Recharts defaults with minimal customization. Data viz is where premium perception lives or dies in fintech.

### Motion Polish: 7/10

Landing page motion is genuinely good — staggered reveals, scroll-driven constellation, animated number counters. Dashboard has zero motion. Cards don't animate on load. Expanding a card has no transition. Score changes have no temporal animation. The contrast between "cinematic landing page" and "static dashboard" creates a jarring quality cliff.

### Copy Tone: 8/10

Strength. "Conviction scoring for serious investors," "Hold with structure, not hope," "Emotion is expensive" — elite copy. Declarative, confident, zero hype. Reads like it was written by someone who manages real money. **Preserve this.**

### Overall: $49-79 SaaS Perception

To reach $99+ perception: (1) depth and layering in dashboard, (2) richer data visualization, (3) motion continuity from landing to app, (4) social proof/authority signals.

---

## 5. Behavioral Psychology Breakdown

### Status Signaling: 2/10

No status mechanism. No portfolio score users could share. No "conviction level" for the overall portfolio. No badge, rank, or tier indicator. Premium fintech users want to feel like they're operating at a higher level.

**Fix (P1):** Add portfolio-level conviction score in dashboard header. "Portfolio Conviction: 74/100 — Operating." Single number becomes shareable, trackable, aspirational.

### Scarcity Triggers: 1/10

Free tier's 3-ticker limit is invisible. No counter, no nudge, no "1 analysis remaining" badge. Constraint has no psychological weight because it has no visual presence.

**Fix (P0):** Add persistent "3/3 analyses used this month" indicator in dashboard nav or header. When 0 remain, show gentle upgrade prompt.

### Competence Signaling: 3/10

Product scores stocks but doesn't educate. Users see 87 but don't understand why that's good or what to do about it. Factor breakdown shows percentile numbers but doesn't interpret them.

**Fix (P1):** Add contextual interpretation to scores. Not just "Quality: P84" but "Quality: P84 — Top 16% in its sector. Strong ROE, low debt, consistent earnings." One sentence per factor transforms data into understanding.

### Authority Positioning: 4/10

Methodology page is excellent but hidden behind a nav link. Engine's rigor — deterministic scoring, elimination-before-scoring, sector-neutral normalization — barely visible in the product.

**Fix (P2):** Add subtle "Deterministic score — same inputs, same output, every time" badge or tooltip on the dashboard. Reinforce methodology where users interact with scores.

### Reward Loops: 1/10

No weekly email recap. No "your portfolio conviction improved +3 this week." No achievement mechanics. Zero temporal engagement hooks.

**Fix (P1):** Weekly conviction recap email. "3 positions improved. 1 dropped below threshold. Portfolio conviction: 74 to 77." Backend cron job + email template. Highest-leverage retention mechanic.

### Progress Visibility: 2/10

No portfolio completeness indicator. No historical score trend. No "conviction trajectory" chart.

**Fix (P1):** Mini conviction trend sparkline in dashboard header showing portfolio conviction over last 30/60/90 days.

### Loss Aversion: 1/10

No alerts when conviction drops. No "AAPL dropped from High to Watchlist" notification. Doesn't leverage the most powerful behavioral principle.

**Fix (P1):** Conviction change alerts — even just in-app (red badge on nav icon). "2 positions had conviction changes since your last visit."

### Dopamine Mechanics: 1/10

No satisfying micro-interactions. No score reveal animation. No "new score available" notification.

**Fix (P2):** When a user searches/scores a new ticker, animate the score counting up from 0 (reuse `AnimatedNumber` from landing page on the dashboard).

### Stickiness Verdict: Forgettable.

Users try it once, get their scores, and have no reason to return. No push, no pull, no loop.

---

## 6. Competitive Weakness Map

### vs. TradingView

| Dimension | TradingView | Margin Invest | Verdict |
|---|---|---|---|
| Charting | World-class | Basic Recharts | TradingView wins |
| Screening | Powerful but DIY | Opinionated & deterministic | Margin wins on philosophy |
| Community | Massive | None | TradingView wins |
| Data viz polish | Exceptional | Functional | TradingView wins |
| Price | Free-$60/mo | Free-$79/mo | Comparable |
| Unique value | Charting tools | Conviction scoring framework | Different categories |

**Where Margin wins:** TradingView gives tools. Margin gives answers. Don't compete on charting — compete on conviction.

### vs. Simply Wall St

| Dimension | Simply Wall St | Margin Invest | Verdict |
|---|---|---|---|
| Visual appeal | Snowflake diagrams | Flat percentile bars | Simply Wall St wins |
| Analysis depth | Broad but shallow | Deep + opinionated | Margin wins |
| Methodology transparency | Moderate | Fully transparent | Margin wins |
| First impression | "Wow, beautiful" | "Hmm, data-dense" | Simply Wall St wins |

**Key insight:** Simply Wall St proves data visualization quality directly drives perceived value. Their snowflake diagram is their brand. Margin needs an equivalent signature visualization.

### vs. Bloomberg (lite concept)

**The aspiration:** Margin should feel like "Bloomberg convictions for the rest of us." Not the terminal — the conviction layer Bloomberg doesn't provide.

### Where Margin Looks Amateur

1. Dashboard data visualization — flat bars when competitors use rich, branded visualizations
2. Empty social proof — no user count, no backtests, no credibility signals
3. Login page — gold button, no logo, no WebGL, feels 2020 indie SaaS
4. Stock cards — obscure tickers without enough context for non-expert users
5. No search — user can't search for their ticker; they get whatever the engine scored

---

## 7. Conversion-Optimized UI Fixes

### Fix 1: Onboarding Flow (P0)

**Current:** CTA -> `/dashboard` (wall of pre-scored tickers)

**New flow:**
1. CTA -> `/onboarding` (new page)
2. Full-screen centered card (reuse login glassmorphism pattern): "What are you holding?"
3. Multi-ticker input field (comma-separated or one-at-a-time with enter)
4. Minimum 1, suggest 3-5, placeholder: "AAPL, MSFT, GOOGL"
5. "Score my positions" button (primary accent)
6. Loading state: animated pipeline visualization (4 nodes light up sequentially, 400ms each)
7. Results: personalized dashboard showing their tickers scored
8. Upsell: "You scored 3. Your portfolio probably has more."

**Specifics:**
- Input: `text-[17px]`, `bg-bg-elevated`, `border-border-primary`, `rounded-[4px]`, `px-4 py-3`
- Card: Same glassmorphism spec as login redesign (`blur(16px)`, `rgba(17,17,19,0.6)`)
- Pipeline animation: 4 nodes light up sequentially during scoring (each 400ms)

### Fix 2: Dashboard Header — Portfolio Conviction Score (P0)

**Current:** "Dashboard" heading + "Last updated" timestamp. No summary metric.

**New layout:**
```
Dashboard                                          Portfolio Conviction
Last updated: Feb 16, 2026                         74/100
                                                   +3 this week | Operating
```

- Portfolio score: `text-[40px] font-bold font-mono text-accent`
- Trend indicator: `text-[13px] text-bullish` (positive) or `text-bearish` (negative)
- Status label: "Operating" (60+), "Building" (30-59), "Reviewing" (<30)
- Mini sparkline (last 30 days): `48px wide, 24px tall` to the left of the score

### Fix 3: Percentile Bar 5-Tier Color Encoding (P0)

**Current:** All bars above 70 are the same emerald green.

**New system:**
- 90-100: `#10B981` (bright green) — Exceptional
- 70-89: `#1C7A5A` (emerald) — Strong
- 50-69: `#6B7280` (gray) — Average
- 30-49: `#D97706` (amber) — Below average
- 0-29: `#DC2626` (red) — Weak

Add subtle gradient within each bar (darker to lighter left-to-right) and round the right end cap with `rounded-r-full`.

### Fix 4: Stock Card Visual Hierarchy (P1)

**Current:** All cards look identical regardless of conviction level.

**New tiered treatment:**

**Exceptional (90+):**
- Left border: `border-l-2 border-accent`
- Score: `text-accent`
- Subtle background: `bg-accent/[0.03]`

**High (75-89):**
- Left border: `border-l-1 border-border-primary`
- Score: `text-text-primary`
- Standard background

**Watchlist (50-74):**
- No left border
- Score: `text-text-secondary`
- Background: `bg-bg-primary` (slightly recessed)

### Fix 5: Free Tier Scarcity Indicator (P0)

**Add to FloatingNav (app variant):**
```
[ M ] [ Dashboard  Backtesting  Settings ] [ 1/3 ] [ Avatar  Sign Out ]
```

- Counter pill: `text-[11px] font-mono bg-accent/10 text-accent px-2 py-0.5 rounded-full`
- When 0 remaining: pill turns `bg-warning/10 text-warning` with "0/3"
- Click opens popover: "You've used all 3 analyses this month. Upgrade to Operator for unlimited."

### Fix 6: Implement Login Page Redesign (P1)

Implement existing spec (`2026-02-17-login-redesign-design.md`):
- Glassmorphism card with WebGL "Liquidity Flow" background
- OAuth-first with icon-only buttons
- Credentials collapsed behind "Continue with email"
- Geometric M logo centered at top of card
- Kill the gold button — use emerald accent consistently

### Fix 7: Score Interpretation Layer (P1)

**Current:** "Quality: 84" with a green bar.

**New:** Add one-line interpretation below each factor in expanded card view.

```
Quality    84
           Top 16% in Technology. Strong ROE, consistent margins.

Value      96
           Deeply undervalued vs sector. P/E and FCF yield both exceptional.

Momentum   93
           Strong uptrend across all timeframes. Relative strength top 7%.
```

- Interpretation text: `text-[12px] text-text-tertiary leading-snug mt-0.5`
- Pre-generated by engine, stored as part of score payload

### Fix 8: Pricing Section Improvements (P1)

1. Add "Most popular" badge on Operator: `absolute -top-3 left-1/2 -translate-x-1/2 bg-accent text-white text-[11px] font-semibold px-3 py-0.5 rounded-full`
2. Show annual savings: "$29/mo billed annually (Save 25% vs monthly)" `text-[12px] text-text-tertiary`
3. Add crossed-out monthly price on Allocator: "~~$99~~ $79/mo billed annually"
4. Make Scout card shorter (less vertical space) — it's the decoy
5. Subtle upward gradient on Operator: `bg-gradient-to-t from-bg-elevated to-accent/[0.04]`

### Fix 9: Social Proof — Operational Metrics (P2)

**Add below hero section or above pricing:**
```
Scoring 2,400+ equities daily  |  6 quantitative factors  |  Updated every market close
```

- Style: `text-[13px] font-mono text-text-tertiary tracking-[0.3px]` centered, with subtle dividers

### Fix 10: Dashboard Card Sparklines (P2)

Sparkline component exists but shows dashed empty lines for most tickers because `bars` data isn't populated. When price data is available, sparkline should be prominently visible on every card, colored by signal (green buy, gray hold, red sell). When unavailable, hide entirely rather than showing empty dashed line.

### Fix 11: Weekly Conviction Email (P1)

Backend implementation:
- Cron job: Every Sunday at 9am user's timezone
- Content: Portfolio conviction delta, top 3 conviction changes, one new high-conviction pick teaser
- Design: Minimal, matches product aesthetic (dark bg, emerald accents, monospace numbers)
- Footer CTA: "View full dashboard"

### Fix 12: Dashboard Motion Continuity (P2)

- Stock cards: staggered fade-in on load (reuse landing page `whileInView`, 50ms stagger per card)
- Score numbers: `AnimatedNumber` on first render (count from 0, 800ms)
- Percentile bars: width animation from 0% on first render (600ms, ease-out)
- Card expand: `animate-in` height transition (300ms)

---

## 8. Growth Architecture Redesign

### Value Escalation Funnel

```
LANDING                    "Conviction scoring for serious investors"
  |                        Emotional hook: "Emotion is expensive"
  |                        Proof: engine output visualization
  v
ONBOARDING (NEW)           "Score your portfolio in 60 seconds"
  |                        Enter 3-5 tickers, watch scoring pipeline animate
  |                        See YOUR holdings scored for the first time
  v
DASHBOARD                  Personal conviction dashboard
  |                        Portfolio conviction score front and center
  |                        Explore factor breakdowns, understand the framework
  v
HABIT LOOP                 Weekly conviction email + in-app alerts
  |                        "2 positions changed conviction this week"
  |                        Score trend tracking, progress over time
  v
UPGRADE TRIGGER            "You've scored 3 of 18 holdings"
  |                        Free tier scarcity becomes visceral
  |                        Upgrade unlocks the remaining portfolio
  v
RETENTION                  Portfolio-level insights (Allocator)
                           Correlation analysis, sector signals, API
                           "I can't manage my portfolio without this"
```

---

## 9. Monetization Reframing Strategy

### Current Problem

Pricing page presents tiers as feature lists. Users compare checkmarks and calculate cost-per-feature. Race to the bottom.

### Reframe: Identity-Based Tiers

| Tier | Current Frame | New Frame |
|---|---|---|
| Scout | "Free with limits" | "See what conviction looks like" |
| Operator | "Full access" | "Run your portfolio like a system" |
| Allocator | "Portfolio tools" | "Capital allocation infrastructure" |

### Copy Changes

**Scout:** "Evaluate the engine with real positions" -> "See what conviction scoring reveals about 3 of your holdings."

**Operator:** "Full scoring for active portfolio management" -> "Score every position. Track every conviction change. Operate with structure."

**Allocator:** "Portfolio-level conviction infrastructure" -> "Portfolio-level conviction infrastructure for investors managing serious capital."

### Conversion Hooks (In-Product)

**Free -> Operator (after 3 analyses used):**
"You've scored your 3 positions for this month. Your portfolio has more holdings that haven't been evaluated. Unlock unlimited analysis."

**Operator -> Allocator (after 30 days):**
"3 of your watchlist tickers had conviction changes this week. See how they impact your overall portfolio correlation."

### Anchor Pricing

Show monthly price crossed out next to annual:
```
OPERATOR
$39/mo -> $29/mo
billed annually | Save $120/year
```

Anchors perceived value at $39, makes $29 feel like a deal.

---

## 10. Design System Refinements

### Color Psychology Additions

**Add secondary data accents:**
- Current: Single emerald for everything
- Add: `--color-data-blue: #3B82F6` for informational/neutral data states
- Add: `--color-data-purple: #8B5CF6` for Mispricing opportunity type (partially implemented)
- Keep emerald exclusively for: positive states, CTAs, conviction indicators

### Elevation System (New)

| Level | Usage | Dark Mode Treatment |
|---|---|---|
| 0 | Page background | `bg-primary` (#0D0F12) |
| 1 | Card surfaces | `bg-elevated` (#151820) + `border-primary` |
| 2 | Active/focused cards | `bg-elevated` + `shadow-[0_2px_8px_rgba(0,0,0,0.3)]` + `border-accent/20` |
| 3 | Modals, popovers | `bg-subtle` + `shadow-[0_8px_32px_rgba(0,0,0,0.5)]` + `backdrop-blur-sm` |

### Motion Rules (Dashboard)

| Element | Trigger | Animation | Duration |
|---|---|---|---|
| Stock cards | Page load | Staggered fade + slide-up (y: 8px) | 400ms, 50ms stagger |
| Score numbers | First render | Count up from 0 | 800ms |
| Percentile bars | First render | Width grow from 0% | 600ms ease-out |
| Card expand | Click | Height + opacity | 300ms |
| Conviction delta | Data change | Color flash (subtle) | 200ms |

### Data Visualization Standards

**Percentile bars:** Add right-end-cap rounding (`rounded-r-full`), 5-tier color encoding, 6px height.

**Score display:** Use `font-mono` for all numerics. Add subtle text-shadow on dark mode: `text-shadow: 0 0 20px rgba(28, 122, 90, 0.15)` for scores above 80.

**Charts:** Decrease Recharts grid opacity from 20% to 8%, use `strokeLinecap="round"` on all lines, add gradient fill under price lines (accent, 5% opacity fading to 0%).

---

## 11. Implementation Roadmap

### Days 1-30: "Make It Convert" (P0)

| Week | Task | Impact |
|---|---|---|
| 1 | Build onboarding flow (`/onboarding` with ticker input + scoring animation) | Activation rate |
| 1 | Add portfolio conviction score to dashboard header | Value perception |
| 2 | Implement 5-tier percentile bar colors + bar styling | Visual quality |
| 2 | Add free tier scarcity indicator to nav | Upgrade conversion |
| 3 | Stock card visual hierarchy (tiered treatment by conviction level) | Scannability |
| 3 | Fix sparkline visibility (hide when no data, show when available) | Dashboard polish |
| 4 | Buffer / testing / refinement | Quality |

### Days 31-60: "Make It Premium" (P1)

| Week | Task | Impact |
|---|---|---|
| 5 | Implement login page redesign (glassmorphism + WebGL) | Trust + premium |
| 5 | Score interpretation layer (one-line per factor) | Comprehension |
| 6 | Pricing section improvements (anchor, badges, framing) | Conversion |
| 6 | Weekly conviction email (backend cron + template) | Retention |
| 7 | Conviction change alerts (in-app badge system) | Return visits |
| 7 | Portfolio conviction trend sparkline in dashboard header | Progress visibility |
| 8 | Buffer / testing / refinement | Quality |

### Days 61-90: "Make It Sticky" (P2)

| Week | Task | Impact |
|---|---|---|
| 9 | Dashboard motion continuity (card animations, score count-up) | Polish |
| 9 | Social proof metrics strip (landing page) | Authority |
| 10 | Dashboard card sparkline improvements | Data richness |
| 10 | Elevation system implementation (card shadows, depth) | Premium feel |
| 11 | Score interpretation expansion (full thesis summaries) | Stickiness |
| 11 | Publish first backtest (content, not code) | Authority |
| 12 | Conviction Dispatch #1 (newsletter content) | SEO + authority |

---

## 12. Core Strengths to Preserve

Non-negotiable. Do not touch in any redesign:

1. **The "M" logo** — geometric stroke-based M in FloatingNav. Clean, distinctive, memorable.
2. **Editorial copy tone** — "Hold with structure, not hope," "Emotion is expensive," "You're not trading. You're operating." This copy is a competitive moat.
3. **Emerald-at-10% discipline** — accent restraint separates this from crypto/fintech noise.
4. **Asymmetric grid layouts** — intentional 7+5 / 5+7 column variations create editorial sophistication.
5. **Constellation animation** — chaos-to-structure narrative is a signature moment.
6. **Section padding variation** — no two sections have the same vertical padding. This rhythm is a design asset.
7. **Left-aligned landing page** — resisting center alignment is what makes this read as editorial/authoritative.
8. **Deterministic philosophy** — the design system embodies the product philosophy: same inputs, same outputs, algorithmic spacing.
9. **FloatingNav design** — pill-shaped floating nav is polished and works well across public/app contexts.
10. **The scoring engine** — 6-factor deterministic pipeline with elimination-before-scoring is the product. Everything else is wrapping.

---

## Pricing Strategy

**Approach: Start low, earn up.**

Keep current prices (Free / $29 / $79) for 6-12 months. Focus on adoption and proving value. Build social proof through backtests, Conviction Dispatch newsletter, and organic authority. Raise prices only after the product has earned the right.

Growth path:
- Months 0-6: Current prices, maximize activation and retention
- Months 6-12: Evaluate usage data, consider modest increase
- Year 2+: Introduce team/advisor tier ($149-199/mo) after product-market fit
