# Regulatory Attorney Consultation Prep Memo

**Prepared:** 2026-04-23
**Status:** RESEARCH SUPPORT ONLY — This is not legal advice. It is a research memo prepared for a consultation with a securities attorney.
**Product:** Margin Invest (deterministic investment analysis platform)
**Prepared by:** Internal product team

---

## 1. Publisher's Exclusion Summary

### The Investment Advisers Act of 1940 — Section 202(a)(11)

The Investment Advisers Act of 1940 defines an "investment adviser" as any person who, for compensation, engages in the business of advising others as to the value of securities or the advisability of investing in, purchasing, or selling securities. Section 202(a)(11)(D) excludes from this definition "the publisher of any bona fide newspaper, news magazine or business or financial publication of general and regular circulation."

### *Lowe v. SEC*, 472 U.S. 181 (1985)

The Supreme Court in *Lowe v. SEC* interpreted this publisher's exclusion broadly. The Court held that Christopher Lowe — whose personal registration as an investment adviser had been revoked — could nonetheless continue publishing his investment newsletter because the publication fell within the publisher's exclusion.

The Court articulated a three-part test. To qualify for the publisher's exclusion, a publication must be:

1. **Bona fide** — The publication must be genuine and not a sham or device to evade the Act. A publication that is merely the vehicle for delivering personalized advice to specific individuals, disguised as a newsletter, would not qualify.

2. **Of general and regular circulation** — The publication must be distributed to subscribers on a regular schedule and must offer the same content to all subscribers. It cannot be a one-off advisory letter to a specific person.

3. **Not personalized advice** — The publication must offer impersonal advice to its readership at large. It must not be tailored to the individual needs, portfolio, or circumstances of a specific subscriber. The Court emphasized the distinction between "individualized" advice (which triggers registration) and "impersonal" advice disseminated to a broad audience (which does not).

The Court relied heavily on First Amendment principles, noting that Congress did not intend the Advisers Act to regulate genuine publishing activity. The exclusion protects publications that are "entirely impersonal and do not purport to be tailored to the needs of specific individuals."

### SEC No-Action Letters and Guidance

The SEC has issued guidance clarifying where the boundary lies:

- **General principle from SEC staff**: A service that provides the same analysis, scores, or recommendations to all subscribers — without tailoring output based on the individual subscriber's portfolio, risk tolerance, or financial situation — generally falls within the publisher's exclusion. Research needed — verify whether specific no-action letters (such as letters addressing quantitative screening tools or online stock screeners) address platforms substantially similar to Margin Invest's model.

- **Interactive tools**: The SEC has addressed whether interactive features on financial websites (e.g., stock screeners, calculators) cross the line from publishing to advising. The general position is that tools generating the same output for anyone who inputs the same parameters are not personalized advice, whereas tools that incorporate a specific user's portfolio data to generate tailored recommendations may constitute advisory activity. Research needed — verify specific no-action letters addressing online screening tools (potential examples include letters to Financial Engines, Inc. or similar platforms, but these should be confirmed before citation).

### Key Takeaway

Margin Invest's core model — a deterministic scoring engine that produces the same scores for the same ticker for every user, published as a general-circulation list — maps closely to the classic publisher's exclusion. The risk arises when features begin to incorporate user-specific data to generate user-specific outputs.

---

## 2. Disqualifying Factors — What Crosses the Line

### Case Law and Enforcement Patterns

The following factors have been identified in case law, enforcement actions, and SEC guidance as indicators that a service has crossed from publishing to personalized advisory activity:

**a) Personalization Based on Individual Circumstances**

When a service tailors its output based on a user's specific portfolio holdings, risk tolerance, financial goals, time horizon, or other personal factors, it is providing individualized advice — not a general-circulation publication. The *Lowe* decision drew a clear line: the exclusion covers "impersonal" advice, not advice "tailored to the needs of specific individuals."

**b) One-on-One Advisory Relationships**

Courts and the SEC have found that newsletters or publications that serve as a front for what is functionally a one-on-one advisory relationship — e.g., where the publisher communicates individually with subscribers about their specific investments — do not qualify for the exclusion. The form of delivery (newsletter, app, website) does not override the substance of the relationship.

**c) Tailored Advice to Specific Subsets**

Even without full one-on-one relationships, services that segment users and deliver different recommendations to different segments based on user-specific inputs (e.g., "conservative" vs. "aggressive" portfolios) approach the line. If the segmentation incorporates individual financial data, it resembles personalized advice.

**d) Interactive Tools Generating Individual-Specific Recommendations**

The SEC has scrutinized interactive tools that:
- Accept a user's portfolio as input and recommend specific trades
- Generate position sizes based on a user's account value
- Suggest asset allocations based on a user's risk profile
- Produce recommendations that differ from user to user because of user-specific inputs

The distinction is between a tool that says "Stock X has a score of 85" (same for everyone) and a tool that says "Based on YOUR $50,000 portfolio and moderate risk tolerance, you should allocate 4.2% to Stock X" (personalized).

**e) The "Functional" Test**

Post-*Lowe*, courts and the SEC apply a functional test: regardless of what a service calls itself, if it functions as an investment adviser — providing individualized advice for compensation — it must register or qualify for an exemption. Labels like "educational" or "informational" do not immunize a service that is substantively providing personalized advisory services.

**f) Relevant Enforcement Context**

The SEC has brought enforcement actions against entities that claimed the publisher's exclusion while:
- Providing individualized portfolio recommendations via email or messaging
- Offering "model portfolios" that were adjusted based on individual subscriber input
- Using software to generate user-specific buy/sell/hold recommendations incorporating the user's holdings

Research needed — specific enforcement citations should be verified. The SEC's actions against various investment newsletter publishers in the 2000s-2010s are relevant but specific case names should be confirmed by the attorney.

---

## 3. Feature Risk Assessment

The following assessment rates each current and proposed Margin Invest feature on a three-color scale.

### Rated GREEN (Low Risk — Likely Within Publisher's Exclusion)

**Public Scored List (Survivor List) — GREEN**

The daily survivor list is a general-circulation publication. Every user who views it sees the same list. It is generated deterministically from the same inputs. It does not incorporate any user-specific data. This is the textbook case for the publisher's exclusion: an impersonal publication of general and regular circulation that analyzes securities without tailoring to any individual.

Supporting factors:
- Same output for all users
- Regular publication cadence (daily)
- Deterministic methodology (same inputs = same outputs)
- No user-specific inputs

**Single-Ticker Forensic Scorecard (No Sizing) — GREEN**

A forensic scorecard for a single ticker — showing composite score, factor breakdowns, percentile rankings, and filter results — is general analytical content. Any user querying the same ticker sees the same output. This is analogous to a research report: impersonal analysis of a specific security.

Supporting factors:
- Output is identical for all users querying the same ticker
- No portfolio context, no sizing, no allocation recommendation
- Informational/analytical, not advisory

**Score Alerts (Non-Personalized Threshold) — GREEN to YELLOW**

If score alerts simply notify a user "Ticker X's score changed from 72 to 85" — the same fact available to any user — this is closer to a news alert service. However, the risk increases depending on implementation. See the Yellow-rated assessment below.

### Rated YELLOW (Moderate Risk — Requires Attorney Guidance)

**Saved Portfolios / Watchlists — YELLOW**

Currently, Margin Invest offers watchlists (5-ticker on Scout, 25-ticker on Analyst, unlimited on Portfolio). Watchlists alone are likely low risk — they are a user convenience feature, similar to bookmarking articles in a newspaper.

However, risk increases if the platform:
- Generates aggregate analytics across a user's watchlist (e.g., "your watchlist is 60% correlated")
- Suggests additions or removals based on the user's existing watchlist composition
- Produces portfolio-level risk analysis of the user's watchlist as a portfolio

The stored watchlist itself is not advisory. But using it as an input to generate user-specific analytical output moves toward personalization.

Recommendation: Clarify with attorney what operations on user-stored watchlists are permissible without crossing into personalized advice.

**Personalized Score Alerts — YELLOW**

Score alerts triggered by a user's specific watchlist occupy a gray zone. On one hand, the underlying data (the score change) is the same for everyone. On the other hand:
- The user has selected specific tickers to monitor (personalization of scope)
- The alerts are triggered by user-defined thresholds (personalization of delivery)
- The combination — "YOUR tickers that crossed YOUR thresholds" — begins to resemble a service tailored to an individual's interests

The strongest argument for staying within the exclusion: the alert content itself is not advice. It is notification of a publicly available fact. The user chose what to watch, but the platform is not advising them on what to do about it.

The risk factor: if alerts include action-oriented language (e.g., "Score dropped below your threshold — consider reviewing your position"), they move toward advisory territory.

Recommendation: Alerts should report facts only ("AAPL composite score: 72 -> 58") without any action-oriented framing. Attorney should confirm this approach.

**Correlation Analysis — YELLOW**

The Portfolio tier currently includes "Correlation analysis." If this analyzes correlations between securities in general (e.g., "AAPL and MSFT have a 0.87 correlation"), it is impersonal analytical content — GREEN.

If it analyzes correlations among a user's specific watchlist or portfolio to produce user-specific diversification insights (e.g., "Your watchlist has a concentration risk — 4 of your 5 tickers are highly correlated"), it moves toward personalized portfolio advice — RED.

Recommendation: Clarify implementation with attorney.

### Rated RED (High Risk — Likely Crosses the Line)

**Kelly-Sized Per-User Position Recommendations — RED**

This is the highest-risk feature. The Kelly Criterion position sizing formula in the engine (`kelly_position_sizing.py`) computes a fractional Kelly position size as a percentage, using win probability, gain/loss ratios, and portfolio-level constraints.

If this feature takes a user's portfolio value (or account size) as input and outputs "allocate X% of YOUR portfolio to Ticker Y" — that is individualized investment advice by any reasonable reading of the Advisers Act. It incorporates the user's specific financial situation (portfolio size) and produces a recommendation tailored to that individual.

Why this is RED:
- **Incorporates user-specific input**: The user's portfolio value/account size is an individual financial datum.
- **Produces user-specific output**: The position size recommendation differs from user to user based on their inputs.
- **Is action-oriented**: A position size recommendation is a direct instruction on how much to invest, tailored to the individual. This is the core of what investment advisers do.
- **Fails the *Lowe* impersonality test**: The output is not "impersonal advice to the readership at large." It is advice to a specific person based on that person's specific circumstances.

Even if the underlying formula is deterministic and publicly documented, the act of applying it to a user's individual portfolio data and delivering a personalized sizing recommendation is functionally advisory.

Mitigation options (for attorney review):
- Offer Kelly sizing as a general educational tool ("if an investor had $100,000, a quarter-Kelly position in Ticker X would be Y%") — same output for everyone, educational context
- Remove user-specific portfolio inputs entirely
- Register as an investment adviser (eliminates the issue but triggers significant regulatory obligations)

---

## 4. Three Questions for the Attorney

### Question 1 (Highest Priority): Kelly Position Sizing

> "We have a deterministic scoring engine that produces identical scores for all users. We are considering adding a feature where users input their portfolio size and the platform outputs Kelly Criterion-based position size recommendations (e.g., 'allocate 3.2% to AAPL'). The formula is publicly documented, the inputs are the same scores everyone sees plus the user's portfolio value, and the output is mathematically determined — not discretionary.
>
> Does this feature disqualify us from the publisher's exclusion? Is there a way to structure it — such as presenting hypothetical portfolio sizes rather than accepting user input, or framing it as an educational calculator — that preserves the exclusion? Or does any form of position sizing based on individual portfolio data require registration?"

### Question 2 (Boundary Clarification): Watchlists, Alerts, and Correlation Analysis

> "Our platform allows users to save watchlists (up to 25 tickers on paid tiers). We generate score-change alerts for watchlisted tickers and offer correlation analysis. The underlying data is the same for all users — the personalization is only in which tickers the user chose to watch.
>
> Where is the line? Is a watchlist-triggered alert ('AAPL dropped from 72 to 58') permissible if it contains no action language? Does running correlation analysis across a user's watchlist — showing them which of THEIR selected tickers are correlated — cross into personalized advice? What specific features or language would push these from permissible publication features into advisory territory?"

### Question 3 (Structural): Product Architecture for Compliance

> "We want to build the most comprehensive product we can while remaining within the publisher's exclusion. Our current architecture: deterministic scoring (same inputs = same outputs, temperature=0), human-oversight governance pipeline (scored lists go through staged -> approved -> published), and all content is impersonal — no user-specific inputs affect scoring.
>
> What structural guardrails should we implement? For example: (a) Should we maintain a bright-line rule that no feature ever accepts user financial data as input? (b) Is there a safe way to offer portfolio-construction tools that stays within the exclusion? (c) If we want to add features that do cross the line, what is the most efficient registration path — full RIA registration, state registration, or an exemption? What would that cost and require operationally for a small team?"

---

## 5. Estimated Consultation Cost

### Securities Attorney Hourly Rates (2025-2026 Estimates)

Rates for attorneys specializing in the Investment Advisers Act and SEC regulatory compliance vary significantly by firm size, geography, and attorney seniority:

| Firm Type | Hourly Rate Range | Notes |
|---|---|---|
| Large national firm (AmLaw 100) | $600 - $1,500+/hr | Partners at top-tier securities practices (e.g., firms with dedicated IA Act groups). Likely overkill for a one-hour consultation. |
| Mid-size firm with securities practice | $350 - $700/hr | Often the best value for this type of consultation. Firms with former SEC staff are particularly useful. |
| Boutique securities/compliance firm | $300 - $600/hr | Specialists who focus exclusively on investment adviser regulation. May offer flat-fee consultations. |
| Solo practitioner (former SEC staff) | $250 - $500/hr | Can be excellent if they have direct experience with publisher's exclusion matters. |

### Estimated Cost for This Consultation

For a one-hour consultation covering the three questions above:

- **Budget estimate**: $400 - $800 for a one-hour consultation with a mid-size firm or boutique specialist.
- **Some firms offer**: A flat-fee initial consultation (30-60 minutes) in the $500 - $1,500 range, which may include a brief written summary of conclusions.
- **If a formal opinion letter is needed** (e.g., a written legal opinion on whether Margin Invest qualifies for the publisher's exclusion): $3,000 - $10,000+, depending on scope and firm.

### Finding the Right Attorney

Look for attorneys who:
- Have direct experience with the publisher's exclusion under the Investment Advisers Act
- Have SEC staff alumni on the team (former Division of Investment Management attorneys)
- Have represented fintech platforms, robo-advisers, or financial publishers
- Are members of the Investment Adviser Association or have published on IA Act topics

Resources for finding specialists:
- Investment Adviser Association (IAA) member directory
- State bar association securities law sections
- Referrals from fintech accelerators or incubators

---

## Appendix: Current Margin Invest Product Features (for Attorney Reference)

| Feature | Current Status | User-Specific Input? | Same Output for All Users? |
|---|---|---|---|
| Composite scoring (entire US equity universe) | Live | No | Yes (deterministic) |
| Daily survivor list | Live | No | Yes |
| Forensic scorecard (single ticker) | Live | No (user selects ticker, but output is identical for all) | Yes |
| Elimination filter results | Live | No | Yes |
| Factor breakdowns + percentile rankings | Live | No | Yes |
| Score history (90-day / unlimited) | Live | No | Yes |
| Sector peer comparison | Live | No | Yes |
| Smart Money / 13F tracking | Live | No | Yes |
| Watchlists (5 / 25 / unlimited) | Live | Yes (user selects tickers) | N/A — user-curated list |
| Score alerts | Live | Yes (user selects tickers + thresholds) | Alert content is same data, delivery is personalized |
| Correlation analysis | Live | Depends on implementation | Unclear — needs review |
| Kelly position sizing | Proposed (engine code exists, not exposed to users) | Yes (portfolio value) | No — output differs per user |
| API access | Live (Portfolio tier) | No (same API, same data) | Yes |

---

**Disclaimer:** This memo is internal research support prepared by the product team. It is not legal advice and should not be relied upon as such. All analysis herein should be reviewed and validated by a qualified securities attorney before any product, regulatory, or business decisions are made.
