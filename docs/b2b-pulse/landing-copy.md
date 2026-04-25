# /b2b Landing Page Copy Spec

## 1. Problem

**Your scoring data has no chain of custody.**

RIAs face mounting compliance pressure to demonstrate how investment recommendations are generated, that the data behind them is auditable, and that results are reproducible on demand. Most vendor APIs deliver a number with no lineage -- no audit trail, no governance record, no way to prove to an examiner that yesterday's score wasn't revised after the fact.

Fintech operators embedding third-party scores face the same exposure: if you can't explain the score, you own the liability.

---

## 2. The Engine

**Deterministic scoring. Same inputs, same outputs. Always.**

Margin Invest's scoring engine is a pure Python library with zero stochastic components in production output. Every asset is scored through:

- **Elimination filters** (fail-fast before scoring -- liquidity, history, sector coverage)
- **Factor scoring** across value, quality, growth, momentum, and capital efficiency
- **Percentile ranking** within GICS sector first, then cross-sector normalization
- **Composite scoring** via weighted geometric mean with configurable factor weights
- **Growth-stage adjustments** that shift factor emphasis based on company maturity

No black boxes. No daily recalibration that silently changes yesterday's output.

---

## 3. Data Sources

| Source | What It Provides |
|---|---|
| **SEC EDGAR** | 10-K / 10-Q XBRL parsing (26 financial fields), quarterly snapshots |
| **13F Filings** | Institutional holdings, quarter-over-quarter position changes, accumulation signals |
| **Filing Analysis** | Semantic diffing of consecutive 10-K Item 1A sections using Voyage AI embeddings |
| **Market Data** | Daily prices, market cap, average daily volume, delisting detection |
| **Point-in-Time Archive** | 217K financial snapshots, 12.8M daily prices, 224K universe memberships -- all timestamped to avoid lookahead bias |

---

## 4. Governance Pipeline

**Every score passes through three gates before it reaches your application.**

```
staged --> approved --> published
```

- **Staged**: Engine produces scores; circuit breakers check for drift (>30%), ingestion failure (>20%), or ML regression (>50%). Scores that trip a breaker are held.
- **Approved**: Human reviewer inspects factor breakdowns, filter results, and reproducibility audit. Approves or rejects.
- **Published**: Approved scores are released to the API and archived with a SHA-256 hash chain to a tamper-evident daily-picks archive (GitHub + R2).

Supporting infrastructure:

- **Reproducibility audits**: Environment snapshot captured after every scoring run -- Python version, package hashes, config state, random seeds.
- **Governance event log**: Every approval, rejection, config change, and circuit-breaker trip is recorded with actor, timestamp, and rationale.
- **Multi-seed ML validation**: 20 seeds per training cycle with distributional gates (median IC > 0.15, CV < 0.50, worst seed > 0.05). Model promotion requires gate passage.

---

## 5. API Surface

| Endpoint | Returns |
|---|---|
| `GET /scores/{ticker}` | Composite score, tier, signal, factor breakdown, filter results |
| `GET /scores/{ticker}/history` | Historical score time series |
| `GET /scores/{ticker}/valuation-audit` | Full valuation methodology trace |
| `GET /analytics/filing-deltas/{ticker}` | Semantic deltas between consecutive 10-K Item 1A sections |
| `GET /analytics/13f/accumulation` | Institutional accumulation signals, crowded-trade detection |
| `GET /analytics/13f/new-positions` | New institutional positions (quarter-over-quarter set difference) |
| `GET /sectors` | Sector list with pass rates and champions |
| `GET /sectors/{sector}/champion` | Top-ranked asset in sector with full factor detail |

All responses include `scored_at` timestamps, governance status, and hash-chain references where applicable.

---

## 6. Pricing

| Tier | Monthly | API Calls | Support |
|---|---|---|---|
| **Starter** | $500 | 10,000 | Email, 48-hour SLA |
| **Growth** | $2,000 | 100,000 | Slack channel, 12-hour SLA |
| **Scale** | Custom | Unlimited | Dedicated onboarding, custom SLA |

All tiers include full governance audit trail access and reproducibility reports.

Enterprise volume discounts available. Annual billing saves 15%.

---

## 7. Call to Action

**Start your free 30-day pilot.**

No credit card. No commitment. Full API access for 30 days. If the data fits your workflow, we'll send a one-page LOI.

`[Start Free Pilot]` --> intake form (name, firm, AUM range, use case)
