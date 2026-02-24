# Behavioral Positioning Analysis — Margin Invest V1

**Date:** 2026-02-23
**Status:** Approved
**Author:** Claude (brainstorming session)

## Purpose

This document analyzes how Margin Invest's V1 feature set aligns with the deep psychological drivers and unmet needs of our core audience. It identifies strengths, blind spots, perception risks, and a unifying narrative. It is the reference document for all future messaging, copy, and positioning decisions.

---

## 1. Audience Archetypes

### 1.1 The Burned but Serious Investor

Has lost money chasing narratives. Not reckless — they did research, built conviction, and still got burned. The specific wound: they trusted their own judgment on a thesis that turned out to be wrong, and the information to avoid it was available but invisible to them.

**Core need:** Outsource the part of themselves that failed.
**Emotional driver:** Relief. Protection from repeating the worst experience of their investing life.
**Product relationship:** The elimination filters are a prosthetic for broken judgment.

### 1.2 The DIY Quant

Data-driven, skeptical, independent. Has built their own models (spreadsheets, Python scripts, backtested strategies). Knows more about factor investing than 95% of retail investors. Cannot scale because they lack institutional-grade data infrastructure.

**Core need:** The system they would build if they had unlimited time and data.
**Emotional driver:** Respect. Recognition of intellectual sophistication.
**Product relationship:** The methodology and rigor are the product. If the implementation passes their sniff test, they become the most vocal evangelist.

### 1.3 The Rationalist

Bias-aware. Has read Kahneman, Thaler, Ariely. Knows about anchoring, loss aversion, herding. Critically: knows that knowing about biases doesn't protect you from biases (the bias blind spot). Has watched themselves make irrational decisions while knowing they were irrational.

**Core need:** A system that structurally prevents human interference.
**Emotional driver:** Vindication. Proof that removing the human is the correct approach.
**Product relationship:** Determinism is the product. They would pay to have the override button removed.

---

## 2. Feature-Archetype Psychological Map

### 2.1 Elimination Filters

| Archetype | Fit Strength | Emotional Response | Why |
|-----------|-------------|-------------------|-----|
| Burned but Serious | Strongest | Relief | "This would have caught what I missed." The Beneish M-Score and Altman Z-Score address the exact failure mode — companies that looked fine until they weren't. |
| DIY Quant | Strong | Authority | They recognize Beneish and Altman by name. Academically validated filters signal that the builders read the same papers. Will probe for exact thresholds and false-positive rates. |
| Rationalist | Moderate | Safety | Appreciates the binary nature (no ambiguity, no discretion), but their primary fear is bias, not bankruptcy. Filters address a secondary anxiety. |

**Emotional resonance scores:**

| Dimension | Rating |
|-----------|--------|
| Relief | Very High — "This catches what I missed" |
| Trust | Very High — binary pass/fail, no ambiguity |
| Authority | Medium — academic pedigree (Beneish 1999, Altman 1968) |
| Safety | Very High — the floor is protected |

**Key insight:** The elimination gauntlet is the most emotionally loaded feature in the product. It doesn't just protect — it validates past pain. The Burned investor who lost money on a company cooking the books will look at the Beneish M-Score and feel seen. This is the trust anchor of the entire product.

**Blind spot:** The feature name "Elimination Filters" is a technical label. What the user actually feels is: "This system would have stopped me from buying Wirecard." The gap between the feature name and the emotional reality is the biggest messaging opportunity.

### 2.2 Growth-Stage-Adjusted Factor Weights

| Archetype | Fit Strength | Emotional Response | Why |
|-----------|-------------|-------------------|-----|
| Burned but Serious | Moderate | Reassurance | They've been caught in value traps or overpaid for growth. Dynamic weights address both, but the concept is abstract. |
| DIY Quant | Strongest | Respect | This is the feature that separates the product from naive quantitative screens. Every quant knows applying the same value metric to Amazon and Coca-Cola is nonsensical. |
| Rationalist | Strong | Trust | Weights shift algorithmically, not by human judgment. The system adapts without anyone deciding it should adapt. |

**Emotional resonance scores:**

| Dimension | Rating |
|-----------|--------|
| Relief | Low — too abstract to trigger the exhale |
| Trust | Medium — algorithmic, not discretionary |
| Authority | Very High — signals deep quant sophistication |
| Safety | Medium — prevents value traps, but indirectly |

**Key insight:** Highest intellectual value, lowest emotional accessibility. "Growth-Stage-Adjusted Factor Weights" is a feature description, not a benefit. What it actually means: "We don't compare Amazon to Coca-Cola."

**Blind spot:** The landing page pipeline visualization doesn't surface growth-stage adaptation anywhere. It's buried in the methodology page. The DIY Quant — the most vocal potential advocate — will discover this deep in the product and wonder why it wasn't prominent.

### 2.3 Deterministic Rules & Anti-Bias Framework

| Archetype | Fit Strength | Emotional Response | Why |
|-----------|-------------|-------------------|-----|
| Burned but Serious | Strong | Liberation | Followed a guru or their own gut and got burned. "No human judgment anywhere" is the antidote to that specific betrayal. |
| DIY Quant | Moderate-to-Strong | Conditional trust | Appreciates determinism but probes for edge cases. "What about regime changes? Black swans?" |
| Rationalist | Strongest | Vindication | This IS the feature for this archetype. A system that structurally prevents every cognitive bias they've studied is their dream product. |

**Emotional resonance scores:**

| Dimension | Rating |
|-----------|--------|
| Relief | Medium — "I can't override my own bad instincts" |
| Trust | Very High — same inputs, same outputs, every time |
| Authority | Medium — principled but not credentialed in the same way as named academic models |
| Safety | High — removes the human failure mode |

**Key insight:** Determinism isn't a technical property — it's a worldview statement. "Markets are emotional, humans are biased, and the only way to win is to remove the human from the decision loop." All three archetypes share this belief. This is the foundation of the unifying narrative.

**Blind spot:** The landing page subtitle ("A deterministic capital allocation system that replaces narrative with structure") is accurate but cold. "Deterministic" resonates with the Rationalist but alienates the Burned investor. They don't want a system — they want protection from themselves.

---

## 3. Emotional Resonance Summary

| Feature | Relief | Trust | Authority | Safety |
|---------|--------|-------|-----------|--------|
| Elimination Filters | High | High | Medium | Very High |
| Growth-Stage Weights | Low | Medium | Very High | Medium |
| Deterministic Rules | Medium | Very High | Medium | High |

**The gap:** Excellent coverage on Trust and Safety. Strong Authority in the methodology. Underweight on Relief — the visceral exhale moment. Relief comes from recognition: the user needs to feel the product understands the specific pain they've been through. Current copy describes the system, not the problem the system solves in the user's life.

---

## 4. The Trust Timeline

Trust develops across a predictable arc. Each stage maps to a different product surface.

### Stage 1: Skeptical Curiosity (Landing Page, 30 seconds)

The user asks: "Is this real or is this another finance grift?"

**Current strengths:**
- "Conviction. Engineered." is concise and confident, no hyperbole
- Rotating HeroCandidateCard with live data is immediate proof-of-life
- "Not for / For" positioning section self-selects effectively

**Current gaps:**
- No social proof. Zero external validation. The Burned investor has been burned by platforms with big claims and no evidence.
- No performance number. Backtesting is gated behind auth. One metric on the landing page — even with disclaimers — would do more for conversion than any copy change.
- Pipeline visualization (counter-scrolling cards) is cognitively expensive for first-time visitors. Process should come after belief, not before.

**Recommendation:** Move the Proof section above the Pipeline section. Insert one backtesting metric on the landing page.

### Stage 2: The Sniff Test (Search a Familiar Ticker, 2-5 minutes)

The most critical moment in the user journey. Every user will search a ticker they know well — one they own, or one they lost money on — and check whether the system matches their lived experience.

**Three outcomes:**
- System confirms expectation: trust increases slightly (confirmation is comfortable, not impressive)
- System contradicts expectation with rigorous explanation: trust increases dramatically (the "aha" moment)
- System contradicts expectation with thin explanation: trust collapses

**Recommendation:** Consider a limited search interaction on the landing page — even just the verdict (PASS/ELIMINATED) and top-line score. "See what the system thinks of any ticker" as an interactive element. Fastest path to the sniff test, and the sniff test is the fastest path to trust.

### Stage 3: Methodological Verification (Methodology Page, 10-20 minutes)

The DIY Quant and Rationalist both end up here. They need intellectual verification before commitment.

**Current strength:** The methodology page is thorough — pipeline, universe, filters, scoring, conviction, outputs.

**Current gap:** It reads like documentation, not like an argument. For each section, the user's implicit question is: "Why this approach instead of the obvious alternative?" (Why Beneish instead of just auditor flags? Why percentile ranking instead of raw scores? Why 7-year median for cyclicals?) One sentence of "why not the alternative" per section transforms documentation into persuasion.

### Stage 4: Portfolio Alignment (Weeks 2-4)

The user evaluates whether to put money behind the signals. The SELL signal becomes the product — anyone can recommend a stock, but when do you tell them to get out?

**Recommendation:** Show one specific historical example of a SELL signal firing correctly. Not aggregate performance — one ticker, one date, one outcome. Concrete, verifiable, visceral.

### Stage 5: Long-Term Retention (Months 3+)

Retention drivers differ by archetype:
- **Burned but Serious:** Retained by absence of disaster. Every quarter without a major loss reinforces protection.
- **DIY Quant:** Retained by intellectual discovery. Sub-factor tables become a research tool. "Similar Profile" features (v2+) create rabbit holes.
- **Rationalist:** Retained by consistency. The system does the same thing every time. Fixed factor weights are a retention feature.

---

## 5. Competitive Positioning

### 5.1 Landscape

| Competitor | What They Sell | Hidden Weakness |
|------------|---------------|-----------------|
| Motley Fool | Expert analyst picks | Experts are wrong ~40% of the time; user never knows which 40% |
| Seeking Alpha | Crowd-sourced analysis | Narratives fighting narratives — maximally biased |
| Zacks | Quantitative ratings | Black box — shows rank without work |
| Portfolio123 | DIY factor models | User builds it themselves — user IS the bias |
| Koyfin / FinChat | Professional data terminals | Data firehose, no synthesis |
| Simply Wall St | Visual financial analysis | Gorgeous but analytically shallow |

### 5.2 The Positioning Gap

Nobody occupies the intersection of: rigorous quantitative engine + fully transparent methodology + zero human discretion + opinionated enough to say BUY/SELL.

Portfolio123 is rigorous but requires the user to be the quant. Zacks is opinionated but opaque. Koyfin gives data without synthesis. Simply Wall St synthesizes without depth. Motley Fool and Seeking Alpha are entirely narrative-driven.

Margin Invest is the only platform that says: "We'll do the work, we'll show the work, and you can't override the work."

### 5.3 The "No Opinion" Moat

This positioning is structurally unforgeable:

**Competitors cannot replicate it retroactively.** Any competitor can add a backtesting feature or more data. But a competitor cannot retroactively remove human discretion from their methodology. Motley Fool has analysts. Seeking Alpha has a community. Even Zacks has an opaque methodology that may have humans in the loop.

**Transparency is the proof.** Open formulas, shown thresholds, deterministic guarantees — these are not just features. They are evidence of the absence of human interference. No competitor can claim this without rebuilding from scratch.

**Honesty is self-reinforcing.** Every time the product shows a negative result honestly (overvalued pick, empty dashboard during a crash, failed filter on a popular stock), it strengthens the narrative. Competitors cannot do this because their business model depends on always having something positive to say.

---

## 6. Strategic Recommendations

### 6.1 Lead with Elimination, Not Process

**Current state:** Landing page hierarchy is Hero → Problem → Pipeline → Engine → Proof → Positioning.

**Problem:** Pipeline and Engine describe process before establishing emotional resonance.

**Recommendation:** After the Problem section, insert a short "Elimination in Action" vignette. Show one concrete example: "In [recent quarter], our elimination filters flagged [N] companies before they reported [negative event]." One real example outweighs six process diagrams.

### 6.2 Rename the Abstractions

| Current Label | Problem | Suggested Reframe |
|---------------|---------|-------------------|
| Elimination Filters | Technical, clinical | "The Gauntlet" (already used internally — promote it) |
| Growth-Stage-Adjusted Factor Weights | Unparseable outside quant finance | "Context-Aware Scoring" or one-liner: "We don't compare Amazon to Coca-Cola" |
| Deterministic Rules | Cold, robotic | "Zero Discretion" or "No Overrides. Ever." |

### 6.3 Surface One Backtesting Metric

Move one performance number to the landing page. "Our scoring pipeline has beaten the S&P 500 by X% annualized since 2015 with a max drawdown of Y%." A single number with a specific time range creates more trust than a methodology essay. Include appropriate disclaimers.

### 6.4 Weaponize the "What If?" Section

The failed-ticker hypothetical scoring section is the product's best trust-builder — it proves honesty when it's inconvenient. But nobody knows it exists until they search a failed ticker.

Reference it in marketing: "Search any ticker. Even the ones we reject. We'll show you exactly why." Turns a defensive feature into an offensive positioning statement.

### 6.5 Surface Smart Money as Convergent Evidence

The "Institutional Accumulation" factor (13F tracking of Berkshire, Baupost, etc.) is buried deep in the scoring methodology. Consider surfacing "Smart Money Alignment" as a visible element on the asset detail conviction section. Not as social proof ("others bought this") but as convergent evidence ("independently, these funds arrived at the same conclusion").

### 6.6 Add Formula Inline to Sub-Factor Tables

The DIY Quant's trust ritual is verification. When they see "Gross Profitability: 0.43, 78th percentile," they want to see "(Revenue - COGS) / Total Assets" right there. Add a collapsible formula row within sub-factor tables — not default-visible, but one click away. The methodology page already has this information; surface it at the point of use.

### 6.7 Pair Every Threshold with Its Source

Systematic academic citation for every threshold and formula: not "M-Score > -1.78 = FAIL" but "M-Score > -1.78 = FAIL (Beneish, 1999)." Shifts burden of proof from the product to the literature. Methodology page does this inconsistently — make it systematic.

### 6.8 Design the Empty State

If market conditions produce zero high-conviction picks, an empty dashboard destroys trust unless explicitly designed for. The empty state message should read something like: "The system found nothing worth your capital right now. That's the point." Cash is a position. Silence is not malfunction.

### 6.9 Address the Overvaluation Dissonance

The valuation section honestly shows negative upside for recommended stocks. This creates dissonance: "You recommend this but say it's overpriced?" Add one sentence to the asset detail page explaining that composite score (multi-factor rank across quality, value, and momentum) and valuation (price target) measure different things. A stock can be the best-in-class quality/momentum play while trading slightly above intrinsic value.

---

## 7. Perception Risks

### 7.1 Determinism as Liability

If the system recommends a stock that subsequently crashes, determinism cuts both ways. "The machine said buy and I lost money" is more bitter than "I made a bad call." The system removes agency, which feels great when it works and terrible when it doesn't.

**Mitigation:** The URGENT SELL signal (fails elimination after previously passing) partially addresses this. Make its speed and visibility prominent in marketing. The speed of the exit signal is as important as the entry signal for trust.

### 7.2 The "Too Good to Be True" Problem

Sophisticated investors have deeply ingrained skepticism about systematic stock picking (EMH, random walk). The product makes a bold implicit claim.

**Mitigation:** Be precise about what the product is NOT claiming. Not predicting the future. Not guaranteed to beat the market every year. Not eliminating risk. IS claiming that systematic factor analysis with forensic elimination produces better risk-adjusted outcomes than narrative-driven stock picking. The distinction between "better risk-adjusted outcomes" and "guaranteed returns" is critical for credibility.

### 7.3 The Cold Product Problem

Every surface — dark theme, monospace fonts, clinical language — signals authority and precision. Right for the DIY Quant and Rationalist. The Burned investor needs one more dimension: the feeling that someone behind this product understands their experience.

**Mitigation:** Does not require a personality change. Requires a handful of sentences across the product that acknowledge the human experience. The "WHY THIS MATTERS" blocks on failed filters already do this. Extend the pattern to one or two additional surfaces (methodology introduction, landing page positioning section). Recognition is the precondition for trust.

### 7.4 The Transparency Paradox

Radical transparency creates surface area for disagreement. Every visible parameter becomes debatable. The DIY Quant who sees the M-Score threshold at -1.78 might think it should be -2.22.

**Mitigation:** Academic sourcing (Recommendation 6.7) shifts the burden of proof. The user has to argue with the original paper, not with the product.

---

## 8. The Unifying Narrative

### The Statement

> **"The system has no opinion."**

### Why This Works

This is the thread that ties everything together:

- Elimination filters don't think a company is fraudulent — they measure it
- Growth-stage weights don't believe in value or growth — they adapt to what the data shows
- Determinism doesn't prefer any outcome — same inputs, same outputs, every time
- The "What if?" section doesn't hide bad news — it shows everything, even when unflattering
- The valuation section doesn't pretend overvalued picks are cheap — it shows the number

Every competitor has an opinion. Analyst picks are opinions. Community ratings are opinions. Even quantitative tools that let users adjust weights inject opinion back in. Margin Invest is the only platform that structurally prohibits opinion at every layer.

This maps directly to what all three archetypes are running from: the opinion that cost them money.

### The Messaging Cascade

| Level | Message |
|-------|---------|
| Tagline | "The system has no opinion." |
| Explanation | "No analyst discretion. No narrative. No overrides. The same inputs produce the same outputs, every time." |
| Proof | "Search any ticker. We'll show you exactly what the math says — even when it's inconvenient." |
| Differentiator | "Other platforms have opinions. Analyst picks are opinions. Community ratings are opinions. This system has none." |

### Archetype-Specific Resonance

| Archetype | What They Hear |
|-----------|---------------|
| Burned but Serious | "This system won't betray me the way [that guru / my own conviction] did." |
| DIY Quant | "This system is as rigorous as what I'd build, and it admits when it doesn't know." |
| Rationalist | "This system does what I've always believed was the right approach — and it can't be overridden." |

---

## 9. Messaging Architecture

### Tier 1: Identity Statement

> "A conviction engine with no opinion."

The paradox is the hook: high conviction, zero bias. Strong recommendations, no human judgment.

### Tier 2: Promise

> "The top 1% of investable equities, filtered for manipulation, fragility, and overvaluation — synthesized into a single score. Search any ticker. We'll show you exactly what the math says."

Hits all three needs: protection (elimination), synthesis (time efficiency), transparency (show the math).

### Tier 3: Proof Points (One Per Emotional Dimension)

1. **Safety (Burned investor):** "Every stock passes through six elimination filters — including forensic accounting screens that catch earnings manipulation before it becomes public."
2. **Rigor (DIY Quant):** "Factor weights adapt to each company's growth stage. We don't apply value metrics to hypergrowth companies or momentum metrics to cash cows."
3. **Integrity (Rationalist):** "Same inputs, same outputs, every time. No analyst discretion. No narrative overrides. The system doesn't care what the market thinks."

### Tier 4: Differentiator

> "Other platforms have opinions. Analyst picks are opinions. Community ratings are opinions. Even 'quantitative' tools that let you adjust the weights are injecting your opinion back in. This system has none."

### Tier 5: Objection Handling

| Objection | Response |
|-----------|----------|
| "What if the system is wrong?" | "It will be. No system is perfect. But every error is traceable — you can see exactly which factor, which data point, which threshold contributed. When the system is wrong, you'll know why. When a human is wrong, you get excuses." |
| "Empty dashboard means broken product." | "When the system finds nothing worth your capital, it says so. That's not failure — it's the most valuable signal it can give. Cash is a position." |
| "I can build this myself." | "You can build the model. Can you build the data infrastructure, the elimination filters, the real-time re-scoring pipeline, the institutional-grade insider transaction feed, the backtesting framework with point-in-time data? At what point does building it yourself cost more than your time is worth?" |

---

## 10. Priority Actions

Ordered by impact-to-effort ratio:

| Priority | Action | Effort | Impact | Primary Archetype |
|----------|--------|--------|--------|-------------------|
| 1 | Design the empty dashboard state | Low | High | All |
| 2 | Add one backtesting metric to landing page | Low | High | Burned, Rationalist |
| 3 | Reference "Search any ticker" in landing page copy | Low | Medium | All |
| 4 | Add academic citations to methodology thresholds | Medium | Medium | DIY Quant |
| 5 | Add inline formula toggle to sub-factor tables | Medium | Medium | DIY Quant |
| 6 | Add "Elimination in Action" vignette to landing page | Medium | High | Burned |
| 7 | Rework landing page section order (Proof before Pipeline) | Medium | High | All |
| 8 | Add overvaluation explanation to asset detail | Low | Medium | Rationalist |
| 9 | Surface Smart Money Alignment in conviction section | Medium | Medium | DIY Quant, Rationalist |
| 10 | Add limited ticker search to landing page (pre-auth) | High | Very High | All |
