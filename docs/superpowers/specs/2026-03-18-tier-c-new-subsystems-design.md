# Tier C: Engine v2 — New Subsystems (Refined Design)

Validated against codebase state post Tier A/B merges (2026-03-18). Six subsystems,
each with its own implementation cycle. Ordered by dependency graph.

---

## Implementation Order & Dependencies

```
C4 (Inflection Detection) ─── no deps ─────────────────┐
C6 (Kelly Position Sizing) ── metrics.py enhancement ───┤
C3p1 (Moat Quantitative) ─── no deps ──────────────────┤── all independent
C5 (Drawdown Re-Screening) ── existing pit_daily_prices ┘
C1 (NLP Pipeline) ─────────── Anthropic API key ────────┐
C2 (TAM Expansion) ────────── C1 Phase 2 (fallback) ───┤── sequential
C3p2 (Moat NLP) ───────────── C1 Phase 2 ──────────────┘
```

C4, C6, C3p1, and C5 can be implemented in parallel. C2's primary data source is
XBRL tags (no C1 dependency), but its fallback path uses Claude API segment
extraction from C1 Phase 2. C2 can ship with XBRL-only and gain the fallback later.
C3 Phase 2 requires C1 Phase 2.

---

## C4: Inflection Detection Factor

**Effort: Medium | Architecture: Score modifier (not standalone factor)**

### Problem

No factor detects when a company crosses a fundamental inflection point — margin
expansion, FCF turning positive, or operating leverage kicking in. These are temporal
signals that predict near-term outperformance.

### Why Score Modifier (Not Cascade Factor)

Inflection is a temporal signal (something just changed), not a structural quality
(like ROIC or moat durability). The Tier B modifiers (anti_consensus, insider,
liquidity) follow this same pattern — they adjust the composite score
post-computation. Keeping inflection as a modifier maintains the v3 cascade's core
factor count and allows independent weight tuning.

### Design

New `engine/src/margin_engine/scoring/quantitative/inflection_detection.py`:

**Signal 1: Operating Expense Deleverage (0-4 points)**
- Detect OpEx/Revenue ratio declining for 2+ consecutive periods
- Score = min(consecutive_declines × magnitude_per_period / 0.01, 4.0)
- Each 100bps/period decline = 1 point

**Signal 2: FCF Crossover (0-3 points)**
- Free cash flow turning positive after negative streak
- Score = min(prior_negative_streak_length, 3.0)
- Longer prior negative streak = deeper turnaround = higher score

**Signal 3: Margin Expansion Toward Historical Highs (0-3 points)**
- Gross margin trending toward all-time high with consistent improvement
- Score by proximity to ATH × consistency of expansion
- Within 200bps of ATH after 3+ periods of expansion = max score

**Composite:** `score = opex_deleverage + fcf_crossover + margin_expansion` (0-10 scale)

**Metadata output:**
```python
{
    "opex_deleverage_detected": bool,
    "fcf_crossover_detected": bool,
    "margin_expansion_magnitude": float,
    "periods_since_inflection": int,
}
```

**Wiring:** New `inflection_modifier()` function in `score_modifiers.py`.
`apply_all_modifiers()` gains a 4th parameter (`inflection_mod: float`). The
combined product of all 4 modifiers remains clamped to [0.75, 1.25] — the clamp
range does NOT widen with more modifiers, which means each individual modifier's
effective impact decreases slightly. This is intentional: more signals = more
confidence, but no single modifier should dominate.

### Files to Create/Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/inflection_detection.py` | New: three signal functions + composite |
| `engine/src/margin_engine/scoring/score_modifiers.py` | Add `inflection_modifier()`, update `apply_all_modifiers()` signature to accept 4th param |
| `engine/src/margin_engine/scoring/v3_pipeline.py` | Compute inflection modifier, pass to `apply_all_modifiers()` |
| `engine/src/margin_engine/scoring/v4_pipeline.py` | Compute inflection modifier, pass to `apply_all_modifiers()` |

### Data Dependencies

None. Uses existing `FinancialHistory.periods` data (income statement, cash flow).

### Test Strategy

- OpEx deleverage: OpEx/Rev declining 0.35 → 0.33 → 0.31 → score > 0
- FCF crossover: FCF goes [-100, -50, -20, 10, 30] → detected, score = 3.0
- Margin expansion: GM goes [0.30, 0.32, 0.34, 0.36] toward ATH 0.37 → detected
- No inflection: stable company with flat margins → score 0
- Single period history → graceful fallback, score 0
- Backward compat: modifier returns 0 adjustment when no inflection detected

---

## C6: Kelly Criterion Position Sizing

**Effort: Small-Medium | Architecture: Replaces fixed tier-based sizing**

### Problem

`v3_position_sizing.py` uses fixed conviction-tier-to-percentage mapping. This ignores
the actual expected return/risk profile of each position. Kelly criterion provides
mathematically optimal sizing based on edge and odds.

### Design

**Primary sizer** when backtest stats are available. Fixed tier-based sizing serves as
cold-start fallback only (no config toggle).

**Per-position tracking (new):**

The current `PerformanceCalculator` computes win_rate at the portfolio level (months
beating benchmark). For Kelly to work, we need per-position stats:
- Track individual position outcomes (entry price → exit price return)
- Group by conviction tier
- Compute `avg_winner_return` and `avg_loser_return` per tier

**Data model changes required in `backtesting/models.py`:**
- `HoldingRecord`: Add `conviction_tier: str | None`, `exit_price: float | None`,
  `position_return: float | None` fields
- New `PositionOutcome` model: `ticker`, `conviction_tier`, `entry_date`, `exit_date`,
  `entry_price`, `exit_price`, `return_pct`, `is_winner: bool`
- New `TierStats` model: `tier`, `win_rate`, `avg_winner_return`, `avg_loser_return`,
  `n_positions`
- `PerformanceMetrics`: Add `tier_stats: list[TierStats] | None`

The `simulator.py` must populate `conviction_tier` on `HoldingRecord` at entry time
and compute `position_return` at exit time. This data feeds `metrics.py` to compute
per-tier Kelly inputs.

New `engine/src/margin_engine/scoring/kelly_position_sizing.py`:

```python
def kelly_position_size(
    win_probability: float,         # Per-tier hit rate from backtest
    expected_gain: float,           # Mean gain on winning positions
    expected_loss: float,           # Mean loss on losing positions (abs value)
    volatility: float,              # Historical annualized volatility
    kelly_fraction: float = 0.25,   # Conservative: 25% of full Kelly
    max_position_pct: float = 15.0, # Hard cap
) -> float:
    """Full Kelly: f* = (p * b - q) / b
    Fractional Kelly: kelly_fraction * max(0, f*) * 100
    Capped at max_position_pct."""
```

**Safety constraints:**
```python
class KellyConstraints(BaseModel):
    max_single_position: float = 15.0    # Hard cap per position
    max_top_3_combined: float = 50.0     # Top 3 can't exceed 50%
    max_sector_concentration: float = 30.0  # Per-sector cap
    min_positions: int = 5               # Minimum diversification
```

**Fallback:** When backtest stats unavailable (new factor combos, cold start), fall
back to existing fixed tier-based sizing in `v3_position_sizing.py`.

### Files to Create/Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/kelly_position_sizing.py` | New: Kelly formula + constraints |
| `engine/src/margin_engine/backtesting/models.py` | Add `conviction_tier`, `exit_price`, `position_return` to HoldingRecord; new PositionOutcome, TierStats models; extend PerformanceMetrics |
| `engine/src/margin_engine/backtesting/simulator.py` | Populate conviction_tier at entry, compute position_return at exit |
| `engine/src/margin_engine/backtesting/metrics.py` | Add per-position outcome tracking, avg_winner/loser per tier |
| `engine/src/margin_engine/scoring/v3_position_sizing.py` | Delegate to Kelly when stats available |

### Data Dependencies

- Backtest per-position outcomes: computed from existing `simulator.py` + `pit_daily_prices`
- Historical volatility: from `pit_daily_prices`
- No external APIs

### Test Strategy

- Kelly formula with known inputs (p=0.6, b=2.0 → expected f*)
- Constraints enforcement: cap at 15%, sector at 30%, top-3 at 50%
- kelly_fraction=0.25 produces 25% of full Kelly
- Negative edge (p*b < q, e.g. p=0.3, b=1.5 → f* < 0) → position size 0
- Positive edge with low win rate (p=0.45, b=3.0 → f* > 0) → valid positive size
- No backtest stats → fallback to fixed sizing
- Backtest comparison: Kelly vs fixed sizing, measure Sharpe difference

---

## C3: Moat Source Classification

**Effort: Medium (Phase 1) + Small (Phase 2, after C1)**

### Problem

`moat_durability.py` detects 4 quantitative signatures (operating_leverage,
pricing_power, scale_economics, capital_efficiency) but cannot distinguish moat types
(network effects, switching costs, brand, regulatory). Moat type matters for
durability prediction.

### Phase 1: Quantitative Moat Proxies (No Dependencies)

Add three new proxy detectors to existing `moat_durability.py`. These are scored
**separately** from the existing 4 signatures in `_SIGNATURE_WEIGHTS` — they do NOT
get added to `_SIGNATURE_WEIGHTS` (which would change the normalization denominator
`_MAX_WEIGHTED` and silently shift all existing gate thresholds).

Instead, new proxies produce a `moat_classification` dict in `FactorScore.metadata`.
The existing 0-4 quantitative score from `_SIGNATURE_WEIGHTS` is unchanged. The
classification metadata is informational (for frontend display and C3 Phase 2
enrichment) and does not affect the numeric moat score or gate pass rates.

**Switching Costs Proxy:**
- High SGA/Revenue ratio (support-intensive) + low revenue churn
- Revenue retention > 95% for 3+ years with SGA > 20% → 0.8 confidence

**Regulatory Moat Proxy:**
- Deterministic: Utilities, Insurance → 1.0. Pharma with patents → 0.7
- Other sectors → 0.0

**Brand Moat Proxy:**
- Gross margin >> sector median (sustained 5+ years) + P/E premium
- Consumer staples/luxury with GM > sector_median + 15pp → 0.7 confidence

**Output:** Classification metadata in `FactorScore.metadata`:
```python
{
    "primary_moat": "switching_costs",  # or "network_effects", "brand", "regulatory", "none"
    "moat_confidence": 0.8,
    "secondary_moats": ["brand"],
    "moat_sources_detected": ["switching_costs", "brand"],
}
```

No separate `MoatClassification` model class — metadata dict is sufficient until
a frontend consumer needs structured access.

### Phase 2: NLP Enrichment (Depends on C1 Phase 2)

After C1 delivers Claude API analysis of filing text, enrich moat classification
with keyword-based confidence from MD&A sections:
- "switching costs", "customer lock-in", "ecosystem", "platform"
- "network effects", "marketplace", "two-sided", "flywheel"
- "brand equity", "premium pricing", "customer loyalty"
- "regulatory barrier", "license", "patent portfolio"

NLP confidence merged with quantitative proxy confidence (weighted average).

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/moat_durability.py` | Add 3 proxy detectors, update _SIGNATURE_WEIGHTS, add classification metadata |

### Test Strategy

- Regulatory moat: Utilities sector → confidence 1.0
- Brand moat: consumer staples with 50% GM (sector median 35%) → high confidence
- Switching costs: high SGA/Revenue + stable revenue → detected
- No moat: commodity producer → all proxies return 0
- Existing signatures unaffected (regression test)

---

## C5: Drawdown-Triggered Re-Screening

**Effort: Medium | Architecture: New cron job + service + tracking table**

### Problem

No event-driven re-evaluation when quality companies drop 20-30%+. The scoring
pipeline runs on a fixed schedule. A high-conviction compounder that drops 25% on an
earnings miss should be immediately re-evaluated.

### Design

**New cron job** in `workers.py`:
```python
cron(screen_drawdown_candidates, hour=23, minute=30)  # After daily_pit_update (23:00)
```

**New service** `api/src/margin_api/services/drawdown_screener.py`:

```python
class DrawdownScreener:
    async def find_candidates(
        self,
        session: AsyncSession,
        min_drawdown_pct: float = -0.20,  # 20% from 52-week high
    ) -> list[DrawdownCandidate]:
        """Query pit_daily_prices for stocks in scored universe down >= threshold."""

    async def trigger_rescreening(
        self,
        session: AsyncSession,
        candidates: list[DrawdownCandidate],
        arq_pool: ArqRedis,
    ) -> int:
        """Enqueue full_score jobs for top candidates."""
```

**Debounce:** Skip tickers re-screened within 7 days (query `drawdown_rescreens`
for recent entries before enqueuing).

**Hard cap:** Max 10 re-screens per run, sorted by drawdown magnitude (deepest
first). Prevents flooding the ARQ queue during broad market selloffs.

**Circuit breaker:** >15 candidates/day triggers admin alert via governance event
(unusual market event, likely VIX spike).

**Per-ticker scoring worker (new):** The existing `full_score_v3`/`v4` workers
score the entire universe via `run_scoring_v3()` — they cannot target individual
tickers. Drawdown re-screening requires a new per-ticker worker:

```python
async def rescore_ticker(ctx: dict, ticker: str, trigger_reason: str = "drawdown"):
    """Score a single ticker through v3 + v4 pipeline.

    Extracts the per-ticker scoring logic from run_scoring_v3/v4 into a
    reusable function. Forces full gate re-evaluation (no cached results).
    Records governance event with trigger_reason.
    """
```

This worker is enqueued by `trigger_rescreening()` instead of `full_score`.
The per-ticker function also benefits future use cases (manual re-score,
post-filing re-score, etc.).

**New tracking table:**
```sql
CREATE TABLE drawdown_rescreens (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    drawdown_pct FLOAT NOT NULL,
    high_price FLOAT NOT NULL,
    current_price FLOAT NOT NULL,
    trigger_date DATE NOT NULL,
    prior_conviction TEXT,
    new_conviction TEXT,             -- Populated after re-score completes
    outcome TEXT,                    -- 'rescue', 'downgrade', 'unchanged'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Governance integration:** Re-scored results flow through existing
`staged → approved → published` pipeline. Trigger reason logged as
"drawdown_rescreen" in governance events. No special handling needed beyond
the trigger reason field.

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/services/drawdown_screener.py` | New service |
| `api/src/margin_api/workers.py` | New cron job `screen_drawdown_candidates`, new `rescore_ticker` worker function |
| `api/src/margin_api/services/scoring.py` | Extract per-ticker scoring logic from `run_scoring_v3`/`v4` into reusable function |
| `api/src/margin_api/db/models.py` | New `DrawdownRescreen` ORM model |
| `api/alembic/versions/xxx_add_drawdown_rescreens.py` | Migration |

### Config

- `MARGIN_DRAWDOWN_THRESHOLD = -0.20` (20% decline)
- `MARGIN_DRAWDOWN_MAX_PER_RUN = 10`
- `MARGIN_DRAWDOWN_DEBOUNCE_DAYS = 7`
- `MARGIN_DRAWDOWN_ALERT_THRESHOLD = 15` (circuit breaker)

### Test Strategy

- find_candidates with mock price data, verify threshold filtering
- 52-week high calculation correctness
- Debounce: ticker re-screened 3 days ago → skipped
- Hard cap: 20 candidates found → only top 10 enqueued
- Circuit breaker: 16 candidates → governance alert event created
- Integration: trigger re-screen → full_score job enqueued with force_recount_gates=True
- Edge case: stock with <252 days of history (use available max for high calc)

---

## C1: NLP Pipeline (Filing Analysis)

**Effort: Large | Architecture: Three phases, new EDGAR service + ARQ worker**

### Problem

No qualitative signal extraction exists. The EDGAR pipeline extracts 26 XBRL
financial fields (numbers) but ignores the MD&A, Risk Factors, and Business
Description sections of 10-K/10-Q filings.

### Phase 1: Text Extraction (Filing → Raw Text)

New `api/src/margin_api/services/edgar/text_extractor.py`:

```python
class FilingTextExtractor:
    def extract_sections(self, filing_html: str, filing_type: str) -> dict[str, str]:
        """Extract structured text sections from SEC filing HTML.
        Returns {"business": ..., "risk_factors": ..., "mda": ...}"""
```

**Section mapping per filing type:**

| Section | 10-K Item | 10-Q Item |
|---------|-----------|-----------|
| Business Description | Item 1 | N/A (annual only) |
| Risk Factors | Item 1A | Part II Item 1A |
| MD&A | Item 7 | Part I Item 2 |

New DB table `filing_texts`:
```sql
CREATE TABLE filing_texts (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    cik TEXT NOT NULL,
    filing_type TEXT NOT NULL,         -- '10-K' or '10-Q'
    filing_date DATE NOT NULL,
    period_end DATE NOT NULL,
    business_text TEXT,
    risk_factors_text TEXT,
    mda_text TEXT,
    raw_html_hash TEXT,                -- SHA-256 for dedup
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, filing_type, period_end)
);
```

### Phase 2: Claude API Analysis (Text → Structured Signals)

New ARQ worker `analyze_filing_text`:

```python
async def analyze_filing_text(ctx: dict, ticker: str, filing_id: int):
    """Extract qualitative signals from filing text via Claude API.

    Single prompt extracts ALL structured outputs (keeps cost low):
    - moat_signals: list of {type, confidence, evidence}
    - risk_flags: list of {category, severity, description}
    - management_quality: {tone, forward_guidance, confidence}
    - competitive_position: {improving, threats}
    - segment_revenue: list of {name, type, revenue}  (piggybacked for C2)
    - sentiment_value: float (-5 to +5)
    """
```

**Model & cost:**
- Model: Haiku (configurable via `MARGIN_NLP_MODEL`)
- Temperature: 0 (determinism per project standards)
- Max tokens: 4096 output (structured JSON)
- Cost: ~$0.02/filing (Haiku pricing)
- Ongoing: ~625 filings/quarter × $0.02 = **~$12/quarter**
- One-time backfill: ~2000 filings × $0.02 = **~$40** (rate-limited over weeks)

**Cache table** `filing_sentiment_cache`:
```sql
CREATE TABLE filing_sentiment_cache (
    id SERIAL PRIMARY KEY,
    filing_text_id INT REFERENCES filing_texts(id),
    ticker TEXT NOT NULL,
    analysis_version TEXT NOT NULL,     -- 'v1', 'v2' for reprocessing
    prompt_hash TEXT NOT NULL,          -- SHA-256 of prompt template
    sentiment_value FLOAT,             -- -5 to +5
    moat_signals JSONB,
    risk_flags JSONB,
    management_quality JSONB,
    competitive_position JSONB,
    segment_revenue JSONB,             -- Piggybacked for C2
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (filing_text_id, analysis_version)
);
```

**Config guardrails:**
- `MARGIN_NLP_ENABLED = false` — off by default, opt-in
- `MARGIN_NLP_MODEL = "claude-haiku"` — configurable
- `MARGIN_NLP_MAX_FILINGS_PER_DAY = 50` — hard cap on daily spend
- `MARGIN_NLP_RATE_LIMIT = 10` — max API calls per minute (Anthropic rate limits)
- `MARGIN_NLP_TEMPERATURE = 0` — determinism

### Phase 3: Scoring Integration

NLP-derived sentiment feeds into the **existing `anti_consensus_modifier`** as a
4th signal component. The current weights (40% short interest, 30% analyst
divergence, 30% EPS revision) redistribute to (30% short, 25% analyst, 25% EPS,
20% NLP sentiment). The `fundamental_trajectory` gating applies to all 4 signals
uniformly — NLP sentiment is not exempt.

The `anti_consensus_modifier` function signature gains a new optional parameter:
`nlp_sentiment: float | None = None`. When None (NLP not available), weights
revert to the existing 40/30/30 split. This preserves backward compatibility.

**Relationship to existing `sentiment_score.py`:** The existing
`scoring/quantitative/sentiment_score.py` accepts a pre-computed sentiment value
(-5 to +5) and normalizes it. C1's Claude API output produces exactly this range.
Rather than creating a parallel path, C1's `sentiment_value` feeds through
`anti_consensus_modifier` (which already gates on fundamental trajectory). The
standalone `sentiment_score.py` remains available for direct use but is not wired
into the modifier pipeline — it serves as a utility function.

Moat signals feed into C3 Phase 2 enrichment of `moat_durability.py`.

Management quality metadata available in `FactorScore.metadata` for frontend
display — no separate scoring factor.

**Data flow:**
```
EDGAR daily_update → text extraction → filing_texts table
                                          ↓
                   ARQ: analyze_filing_text → Claude API (Haiku)
                                          ↓
                   filing_sentiment_cache → anti_consensus_modifier (sentiment)
                                         → moat_durability.py (moat signals, Phase 2)
                                         → segment_revenue_history (for C2)
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/services/edgar/text_extractor.py` | New: HTML section extraction |
| `api/src/margin_api/db/models.py` | New: FilingText, FilingSentimentCache ORM models |
| `api/alembic/versions/xxx_add_filing_text_tables.py` | Migration |
| `api/src/margin_api/workers.py` | New: `analyze_filing_text` worker, trigger from daily_update |
| `api/src/margin_api/services/edgar/daily_update.py` | Trigger text extraction after XBRL parse |
| `engine/src/margin_engine/scoring/score_modifiers.py` | Add NLP sentiment as 4th anti-consensus signal |

### Test Strategy

- Text extraction from sample 10-K HTML (Apple 2024 filing as fixture)
- Text extraction from sample 10-Q HTML (different section numbering)
- Claude response parsing into structured schema (mock API response)
- Dedup: same filing HTML → no re-extraction (hash match)
- End-to-end: filing → text → analysis → cache → modifier
- Determinism: same filing → same analysis (temperature=0)
- Cost guardrail: MARGIN_NLP_MAX_FILINGS_PER_DAY respected

---

## C2: TAM Expansion Velocity

**Effort: Medium | Architecture: Score modifier**

### Problem

No measurement of how fast a company is expanding into its total addressable market.
Two companies with identical current ROIC can have vastly different futures if one is
capturing share in a growing market while the other is mature.

### Why Score Modifier (Not Cascade Factor)

While TAM expansion is arguably a structural quality, adding it as a cascade gate
would change `total_gates` from 4 to 5 in Tracks A/B/C. This cascades through all
conviction threshold functions (`assess_track_a_conviction`, etc.) which have
hardcoded logic based on `gates_passed / total_gates` ratios. The blast radius is
too large for the value delivered. As a modifier, TAM adjusts the composite score
without touching the gate architecture.

### Design

**Segment data source (no HTML table parser):**

1. **Primary:** XBRL tags (`us-gaap:RevenueFromContractWithCustomersByReportableSegment`
   and related). Many large-cap filers tag segments in XBRL.
2. **Fallback:** Claude API extraction from C1 Phase 2 analysis. The
   `analyze_filing_text` prompt already includes `segment_revenue` in its structured
   output. Results cached in `filing_sentiment_cache.segment_revenue` JSONB column.

This eliminates the need for a brittle HTML table parser (`SegmentParser` class
from original spec is removed).

**Industry growth rate reference:**

Hardcoded config `engine/src/margin_engine/config/industry_growth_rates.py`:
```python
INDUSTRY_GROWTH_RATES: dict[str, IndustryGrowthRate] = {
    "cloud_computing": IndustryGrowthRate(rate=0.15, last_updated="2026-01-01"),
    "cybersecurity": IndustryGrowthRate(rate=0.12, last_updated="2026-01-01"),
    "electric_vehicles": IndustryGrowthRate(rate=0.25, last_updated="2026-01-01"),
    # ... ~50 sub-industries
}
```

Updated annually from industry reports. No external API.

**Factor:**

New `engine/src/margin_engine/scoring/quantitative/tam_expansion.py`:
```python
def tam_expansion_velocity(
    segment_revenues: list[SegmentRevenue],
    industry_growth_rate: float,
    lookback_years: int = 3,
) -> FactorScore:
    """velocity = company_segment_cagr / industry_growth_rate
    - velocity > 1.5 → gaining share (strong signal)
    - velocity 1.0-1.5 → growing with market (neutral)
    - velocity < 1.0 → losing share (negative)
    Score = min(velocity / 2.0, 1.0) * 10  (0-10 scale)"""
```

**New DB table:**
```sql
CREATE TABLE segment_revenue_history (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    filing_date DATE NOT NULL,
    segment_name TEXT NOT NULL,
    segment_type TEXT NOT NULL,         -- 'product', 'geography', 'business_unit'
    revenue DECIMAL NOT NULL,
    source TEXT NOT NULL,               -- 'xbrl' or 'nlp'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, filing_date, segment_name)
);
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/tam_expansion.py` | New: velocity computation |
| `engine/src/margin_engine/config/industry_growth_rates.py` | New reference data |
| `api/src/margin_api/db/models.py` | New SegmentRevenueHistory ORM model |
| `api/alembic/versions/xxx_add_segment_revenue_history.py` | Migration |
| `engine/src/margin_engine/scoring/score_modifiers.py` | Add `tam_modifier()`, update `apply_all_modifiers()` to accept 5th param |
| `engine/src/margin_engine/scoring/v3_pipeline.py` | Compute TAM modifier, pass to `apply_all_modifiers()` |
| `engine/src/margin_engine/scoring/v4_pipeline.py` | Compute TAM modifier, pass to `apply_all_modifiers()` |

### Data Dependencies

- Segment revenue from XBRL tags (existing EDGAR pipeline) — primary, no C1 dependency
- Fallback: Claude API segment extraction from C1 Phase 2 (not Phase 1)
- C2 can ship with XBRL-only; fallback wired later when C1 Phase 2 is complete
- Industry growth rates: hardcoded config, no external API

### Test Strategy

- Parse segment data from XBRL tags (Apple, Microsoft filings)
- Velocity calculation: company growing at 20% in 10% industry → velocity 2.0 → high score
- Golden value: Apple services segment growing at 2× industry → high score
- Edge case: company with single segment / no segmentation → use total revenue vs industry
- Edge case: industry growth rate not in reference table → fallback to sector-level average
- Fallback: no segment data available → factor returns None (excluded from composite)

---

## Cross-Cutting Concerns

### Config Convention

All new config follows existing pattern in `config/`:
- Pydantic `BaseModel` with typed defaults
- Environment variable overrides for deployment-specific values
- Prefix: `MARGIN_` (e.g., `MARGIN_NLP_ENABLED`, `MARGIN_DRAWDOWN_THRESHOLD`)

### Migration Safety

All new Alembic migrations use idempotent checks per project standards:
- `inspector.has_table()` before `create_table`
- Column existence checks before `add_column`
- Same migration may run on multiple Railway containers

### DateTime Columns

All new `DateTime` columns use `DateTime(timezone=True)` per asyncpg requirements.
Defaults use `datetime.now(UTC)`.

### JSONB Columns

All new JSONB columns use `JSON().with_variant(JSONB(), "postgresql")` for SQLite
test compatibility.
