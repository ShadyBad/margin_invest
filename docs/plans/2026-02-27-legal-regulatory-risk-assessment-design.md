# Legal & Regulatory Risk Assessment — Margin Invest

**Date:** 2026-02-27
**Status:** Approved
**Scope:** Comprehensive pre-launch legal, regulatory, and litigation risk assessment with prioritized mitigation roadmap

## Context

Margin Invest is a deterministic investment analysis platform (monorepo: engine/, api/, web/) that produces quantitative factor scores, composite rankings, and signals (currently labeled BUY/SELL/HOLD/WATCH/URGENT_SELL) for U.S. equities. The platform charges $29/month (Portfolio) and $79/month (Institutional) via Stripe subscriptions.

**Current posture:**
- No legal entity formed (operating as sole proprietor)
- Not FDIC insured, not registered with or approved by the SEC, not pursuing registration
- Pre-launch — no revenue, no paying users
- US-only target market
- Published `/legal` page with disclaimers; Terms of Service and Privacy Policy drafted but not published

---

## 1. Regulatory Classification Risk

### 1A. Investment Adviser Risk — SEVERITY: HIGH

The Investment Advisers Act of 1940 defines an "investment adviser" as anyone who (1) provides advice or analyses about securities, (2) as part of a regular business, (3) for compensation. Margin Invest satisfies all three prongs:

1. **Advice about securities** — BUY/SELL/HOLD signals for specific tickers, conviction levels, composite scores, factor breakdowns
2. **Regular business** — Core product offered continuously via SaaS subscription
3. **Compensation** — $29/month and $79/month subscription fees

**Primary defense: Publisher's exclusion (Section 202(a)(11)(D))**

Lowe v. SEC (1985) established that publishers of general circulation offering impersonal advice qualify for exclusion. Margin Invest has a reasonable argument: scores are computed deterministically for the entire universe, not personalized per user. The platform does not ask about risk tolerance, investment goals, or financial situation.

**Weaknesses in the defense:**
- Watchlist feature (user-selected tickers) creates perception of personalization
- Conviction alerts proactively push "recommendations"
- BUY/SELL language is directive, not analytical
- "Conviction" implies the platform has conviction about securities

**Required mitigations:**

Rename signals from directive to descriptive:

| Current | Replacement | Rationale |
|---------|-------------|-----------|
| `BUY` | `STRONG` or `TOP QUANTILE` | Describes factor strength, not an action |
| `HOLD` | `STABLE` or `MAINTAINING` | Describes score trajectory |
| `WATCH` | `EMERGING` or `APPROACHING` | Describes upward trend |
| `SELL` | `WEAK` or `BELOW THRESHOLD` | Describes factor deterioration |
| `URGENT_SELL` | `FAILED` or `DISQUALIFIED` | Describes filter failure |
| `NO_ACTION` | `UNRANKED` or `NEUTRAL` | Describes distribution position |

Rename conviction terminology:

| Current | Replacement |
|---------|-------------|
| `Exceptional Conviction` | `Exceptional Composite` or `99th Percentile` |
| `High Conviction` | `Strong Composite` or `95th+ Percentile` |
| `Conviction Engine` | `Composite Engine` or `Score Engine` |
| `conviction_level` field | `composite_tier` or `strength_tier` |
| `Conviction alerts` | `Score alerts` or `Factor alerts` |
| `"Conviction. Engineered."` headline | Non-advisory framing emphasizing structure/analysis |

### 1B. Broker-Dealer Risk — SEVERITY: LOW

No trade execution, no customer funds, no brokerage connections. Remains low unless trade execution or commission-based referrals are added.

### 1C. Commodity Pool / CFTC — SEVERITY: NONE

Equities only. No CFTC jurisdiction.

### 1D. State Blue Sky Laws — SEVERITY: MODERATE

Many states have investment adviser definitions broader than federal. Some require registration even for publishers. Requires securities attorney evaluation of state-by-state requirements.

---

## 2. Consumer Protection & Misrepresentation Risk

### 2A. Marketing Language — SEVERITY: MODERATE

**Problematic copy in the codebase:**

1. **"Conviction. Engineered."** (hero-section.tsx) — Advisory language. Replace with analytical framing.
2. **"we'll show you exactly what the math says"** (hero-section.tsx) — "Exactly" implies certainty. Remove or soften.
3. **"measurable advantage"** / **"structure creates advantage"** (positioning-section.tsx) — "Advantage" implies outperformance. Replace with "discipline" or "clarity."
4. **"Conviction alerts"** (pricing) — Rename to "Score alerts" or "Factor alerts."

**Already good:**
- "The system has no opinion. It measures." — Excellent framing, elevate this.
- No "guaranteed returns," "beats the market," or "risk-free" claims anywhere.
- Red-flag avoidance list (23 claims) drafted in docs/legal/.

### 2B. Disclosure Sufficiency — SEVERITY: HIGH

**Critical gap: ToS and Privacy Policy are not published.**

Operating a subscription SaaS collecting email, payment data, and OAuth tokens without published privacy policy violates:
- CCPA/CPRA (California Consumer Privacy Act)
- CalOPPA (California Online Privacy Protection Act)
- FTC Act Section 5 (unfair/deceptive practices)
- Stripe merchant terms (require published ToS and privacy policy)

**Required:** Publish ToS and Privacy Policy (Version 2 "Balanced" from docs/legal/ drafts) with click-through acceptance at registration.

### 2C. Backtesting Disclaimers — SEVERITY: HIGH

All backtested/hypothetical performance displays must include:

1. **"HYPOTHETICAL PERFORMANCE" label** — Prominently co-located with chart, not below-the-fold
2. **Limitations disclosure** — Simulated results, not actual trading, no guarantee, benefit of hindsight
3. **Methodology transparency** — Time period, rebalancing frequency, transaction costs, universe selection
4. **Co-location** — Disclaimers proximate to performance data, not separated

**Recommended disclaimer block (NFA/CFTC gold standard):**

> HYPOTHETICAL PERFORMANCE RESULTS HAVE MANY INHERENT LIMITATIONS. No representation is made that any portfolio will or is likely to achieve profits or losses similar to those shown. There are frequently sharp differences between hypothetical performance results and the actual results achieved by any particular trading program. Hypothetical trading does not involve financial risk, and no hypothetical trading record can completely account for the impact of financial risk in actual trading. All results shown are backtested using point-in-time data and include estimated transaction costs. Actual results may differ materially.

**Codebase locations requiring updates:**
- `proof-section.tsx` / `proof-historical-chart.tsx` — Add HYPOTHETICAL badge + expanded disclaimer
- `backtesting/page.tsx` — Add HYPOTHETICAL RESULTS header above metrics, expand disclaimer
- `clone-lab.tsx` — Add HYPOTHETICAL labeling to any performance data
- `cost-disclosure.tsx` — Make non-collapsible or show summary inline

### 2D. FTC / CFPB Risk — SEVERITY: MODERATE

If a user loses money after acting on a signal and claims they were misled, FTC could investigate under Section 5 (deceptive practices). CFPB jurisdiction over non-lending fintech is expanding.

**Mitigation:** One-time "I understand this is not investment advice" acknowledgment before first score view.

---

## 3. Fiduciary & Suitability Exposure — SEVERITY: MODERATE

### Does the platform create fiduciary obligations?

**Arguments against fiduciary duty (strong):**
- No personalized advice — scores identical for all users viewing same ticker
- No discretionary authority — never touches user money
- No client relationship — explicitly disclaimed on /legal page
- No suitability assessment — never asks about risk tolerance or goals

**Arguments for fiduciary duty (weak but present):**
- BUY/SELL signals feel like personalized advice to unsophisticated users
- Watchlist creates perception of personalization
- Conviction alerts proactively push "recommendations"
- Courts sometimes find disclaimers don't override functional reality

### Negligence scenario

User subscribes → sees "BUY" → buys stock → loses 40% → sues claiming platform was negligent in producing signal. Even if claim fails, defense costs $50k-$200k+.

**Mitigation:**
- Signal renaming (Section 1) eliminates "told me to buy" argument
- Registration acknowledgment: "I understand Margin Invest provides quantitative analysis tools, not investment advice. I am solely responsible for my investment decisions."
- Limitation of liability ($100 cap) in ToS
- Indemnification clause in ToS
- E&O insurance covers defense costs

---

## 4. Operational & Structural Risk — SEVERITY: CRITICAL

### 4A. No Legal Entity — HIGHEST PRIORITY

Operating without a legal entity means the founder is personally liable for everything: user lawsuits, regulatory fines, contract disputes, data breaches, IP claims. A single successful lawsuit can attach to personal bank accounts, property, and future earnings.

### 4B. Piercing the Corporate Veil (post-formation)

Even after forming an entity, courts pierce the veil if:
- Business and personal funds commingled
- Entity undercapitalized relative to risks
- Corporate formalities not observed
- Entity used as alter ego

### 4C. Recommended Structure

Form a **single-member LLC** in Delaware or Wyoming:
- Open dedicated business bank account
- Execute written operating agreement (even single-member)
- Maintain strict separation of personal/business finances
- Register as foreign LLC in state of residence if different
- Obtain EIN from IRS
- **Timeline: Before accepting a single user or dollar**

---

## 5. Data, Privacy, and Cybersecurity Risk — SEVERITY: MODERATE

### 5A. Data Collected

- Email addresses, names (optional), password hashes (Argon2id)
- OAuth tokens (Google, Microsoft, Facebook, GitHub)
- MFA data (TOTP secrets, WebAuthn credentials, recovery codes)
- Stripe payment data (customer ID, subscription ID)
- User-provided API keys (encrypted with Fernet)
- Security event logs (failed logins, IP addresses, timestamps)

### 5B. Regulatory Exposure

| Law | Applicability | Current Status |
|-----|--------------|----------------|
| CCPA/CPRA | Any CA user | Privacy Policy drafted but **not published** |
| CalOPPA | Any CA user | **Not compliant** — no published privacy policy |
| CAN-SPAM | Marketing email | Low risk if transactional only |
| State breach notification (all 50) | Upon breach | **No incident response plan** |
| GLBA | Contested for SaaS analytics | Low probability |

### 5C. Mitigation

- Publish Privacy Policy (Version 2 from drafts)
- Document data breach incident response plan
- Document Fernet key rotation procedure
- Verify data deletion capability exists (CCPA right to delete)
- SOC 2 Type I audit when revenue supports it

---

## 6. Litigation Scenarios

### 6A. Most Probable Causes of Action

| Scenario | Probability | Severity | Trigger |
|----------|------------|----------|---------|
| User sues for losses after signal | HIGH → LOW after renaming | $50k-$500k defense | Market downturn |
| SEC inquiry re: investment adviser | MODERATE | $100k-$1M+ | User complaint, sweep |
| State AG deceptive practices | MODERATE | $50k-$500k | Complaint, backtest claims |
| Class action for misleading performance | LOW-MODERATE | $500k-$5M+ | Backtest implies returns |
| Data breach litigation | LOW | $100k-$1M+ | Breach of PII/payment |
| Stripe ToS violation | HIGH | Account termination | No published ToS/PP |

### 6B. Worst-Case Scenario

SEC issues Wells Notice → cease operations → disgorge revenue → civil penalties → founder personally liable (no entity). Estimated exposure: $500k-$2M+. **Preventable with mitigations in this assessment.**

---

## 7. Prioritized Mitigation Roadmap

### TIER 1: IMMEDIATE — Before any user touches the platform

| # | Action | Type | Risk Addressed |
|---|--------|------|----------------|
| 1 | Form LLC (Delaware or Wyoming) | External | Unlimited personal liability |
| 2 | Open business bank account | External | Commingling / veil piercing |
| 3 | Publish Terms of Service | Codebase | Stripe requirement, contract gap |
| 4 | Publish Privacy Policy | Codebase | CCPA/CalOPPA/FTC compliance |
| 5 | Add click-through ToS/PP acceptance at registration | Codebase | Enforceable contract |
| 6 | Add "not investment advice" acknowledgment before first score view | Codebase | Defeats "thought it was advice" claims |

### TIER 2: HIGH PRIORITY — Before launch

| # | Action | Type | Risk Addressed |
|---|--------|------|----------------|
| 7 | Rename signals (BUY→STRONG, SELL→WEAK, etc.) | Codebase | Investment adviser classification |
| 8 | Rename "conviction" to "composite strength" | Codebase | Advisory language removal |
| 9 | Add HYPOTHETICAL PERFORMANCE labels to backtest charts | Codebase | SEC/FINRA compliance |
| 10 | Expand backtesting disclaimers (co-located) | Codebase | Misleading performance claims |
| 11 | Replace "advantage" marketing copy with "discipline"/"structure" | Codebase | Implied outperformance |
| 12 | Replace "Conviction. Engineered." headline | Codebase | Advisory language |
| 13 | Rename "Conviction alerts" to "Score alerts" | Codebase | Consistent terminology |

### TIER 3: PRE-REVENUE — Before accepting payment

| # | Action | Type | Risk Addressed |
|---|--------|------|----------------|
| 14 | Obtain E&O insurance (~$2k-$5k/yr) | External | Negligence claim defense costs |
| 15 | Obtain D&O insurance (~$1k-$3k/yr) | External | Founder personal liability |
| 16 | Obtain cyber liability insurance (~$1k-$3k/yr) | External | Data breach response costs |
| 17 | Engage securities attorney for publisher's exclusion opinion letter | External | Documented IA non-registration basis |
| 18 | Document incident response plan for data breaches | Internal | Breach notification compliance |

### TIER 4: POST-LAUNCH — Ongoing

| # | Action | Type | Risk Addressed |
|---|--------|------|----------------|
| 19 | Monitor state blue sky law requirements | External | State registration |
| 20 | Annual legal review of marketing copy | External | Language drift |
| 21 | SOC 2 Type I audit (when revenue supports) | External | Enterprise trust |
| 22 | Evaluate SEC registration if personalization increases | External | Regulatory posture |

---

## Gap Analysis Summary

| Risk Area | Current State | Target State | Priority |
|-----------|--------------|-------------|----------|
| Entity structure | No entity — unlimited personal liability | LLC formed, separate accounts | CRITICAL |
| ToS / Privacy Policy | Drafted not published | Published with click-through | CRITICAL |
| Signal language | BUY/SELL/HOLD — directive | STRONG/WEAK/STABLE — descriptive | HIGH |
| Conviction language | "Conviction" throughout | "Composite strength" or equivalent | HIGH |
| Backtesting disclaimers | Minimal one-liners | HYPOTHETICAL labels + expanded | HIGH |
| Marketing copy | "advantage," "Conviction. Engineered." | Discipline/structure framing | HIGH |
| User acknowledgment | None | One-time "not advice" gate | HIGH |
| Insurance | None | E&O + D&O + Cyber | MODERATE |
| Securities counsel | None | Publisher's exclusion opinion | MODERATE |
| Incident response | None | Documented breach procedure | MODERATE |

---

## Implementation Scope (Codebase Changes)

The following changes will be specified in the implementation plan:

**Engine changes:**
- Rename signal enum values (BUY→STRONG, SELL→WEAK, etc.) in `margin_engine/models/scoring.py`
- Rename conviction_level → composite_tier (or equivalent) in scoring models
- Update all engine tests

**API changes:**
- Update response schemas to reflect new signal/tier names
- Ensure backward compatibility during transition (if any external consumers exist)
- Update all API tests

**Web changes:**
- Publish ToS page (`/terms`) from draft Version 2
- Publish Privacy Policy page (`/privacy`) from draft Version 2
- Add click-through acceptance flow at registration
- Add one-time "not investment advice" acknowledgment gate
- Rename all signal display text across all components
- Rename all conviction display text across all components
- Update hero headline and marketing copy
- Add HYPOTHETICAL PERFORMANCE labels to backtest charts
- Expand and co-locate backtesting disclaimers
- Replace "advantage" copy with "discipline"/"structure"
- Rename "Conviction alerts" to "Score alerts"
- Update all web tests
