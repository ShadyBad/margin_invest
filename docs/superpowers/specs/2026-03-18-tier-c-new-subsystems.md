# Tier C: Engine v2 — New Subsystems

Technical design doc for 6 items introducing new scoring subsystems.
Each is a standalone project needing its own implementation cycle.

---

## C1: NLP Pipeline (Filing Analysis)

**Effort: Very Large**

### Problem

No qualitative signal extraction exists. The EDGAR pipeline extracts 26 XBRL financial
fields (numbers) but ignores the MD&A, Risk Factors, and Business Description sections
of 10-K/10-Q filings — where management discusses moat sources, competitive threats,
growth plans, and risk factors in plain text.

### Current State

**EDGAR infrastructure** (`api/src/margin_api/services/edgar/`):
- `xbrl_parser.py`: Extracts 26 financial fields from XBRL-tagged filings
- `index_builder.py`: Ticker → CIK mapping from SEC index
- `backfill.py`: Historical XBRL backfill
- `daily_update.py`: Daily/weekly XBRL filing checks

**Scoring integration point** — `sentiment_score.py`:
- Accepts pre-computed `sentiment_value` (-5 to +5)
- Has `has_contrarian_signal` boolean for bonus boost
- Ready to consume NLP output — just needs the pipeline to produce it

**Missing:** No text extraction, no NLP analysis, no filing text storage.

### Design

**Phase 1: Text Extraction (filing → raw text)**

Extend EDGAR pipeline to extract text sections from 10-K/10-Q filings:
- Item 1 (Business Description)
- Item 1A (Risk Factors)
- Item 7 (MD&A — Management's Discussion and Analysis)

New service `api/src/margin_api/services/edgar/text_extractor.py`:
```python
class FilingTextExtractor:
    """Extract structured text sections from SEC filing HTML."""

    def extract_sections(self, filing_html: str) -> dict[str, str]:
        """Returns {"business": ..., "risk_factors": ..., "mda": ...}"""
        # HTML parsing with section boundary detection
        # Handle both XBRL-tagged and plain HTML filings
```

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

**Phase 2: Claude API Analysis (text → structured signals)**

New ARQ worker `analyze_filing_text`:
```python
async def analyze_filing_text(ctx: dict, ticker: str, filing_id: int):
    """Extract qualitative signals from filing text via Claude API.

    Structured output schema:
    - moat_signals: list of {type: str, confidence: float, evidence: str}
    - risk_flags: list of {category: str, severity: str, description: str}
    - management_quality: {tone: str, forward_guidance: str, confidence: float}
    - competitive_position: {improving: bool, threats: list[str]}
    """
```

Configuration:
- Model: Claude Sonnet (cost-effective for structured extraction)
- Temperature: 0 (determinism per project standards)
- Max tokens: 4096 output (structured JSON)
- Cost estimate: ~$0.15/filing → ~$300/quarter for 2000 filings

Cache results in `filing_sentiment_cache`:
```sql
CREATE TABLE filing_sentiment_cache (
    id SERIAL PRIMARY KEY,
    filing_text_id INT REFERENCES filing_texts(id),
    ticker TEXT NOT NULL,
    analysis_version TEXT NOT NULL,     -- 'v1', 'v2' etc for reprocessing
    sentiment_value FLOAT,             -- -5 to +5 (feeds sentiment_score.py)
    moat_signals JSONB,
    risk_flags JSONB,
    management_quality JSONB,
    competitive_position JSONB,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (filing_text_id, analysis_version)
);
```

**Phase 3: Scoring Integration**

Wire cached analysis into existing scoring pipeline:
- `sentiment_score.py` consumes `sentiment_value` from cache
- `moat_durability.py` consumes `moat_signals` for moat source classification (see C3)
- New factor: `management_quality_score.py` from management quality signals

**Data flow:**
```
EDGAR daily_update → text extraction → filing_texts table
                                          ↓
                   ARQ: analyze_filing_text → Claude API
                                          ↓
                   filing_sentiment_cache → scoring pipeline
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/services/edgar/text_extractor.py` | New text extraction service |
| `api/src/margin_api/db/models.py` | New tables: filing_texts, filing_sentiment_cache |
| `api/alembic/versions/xxx_add_filing_text_tables.py` | Migration |
| `api/src/margin_api/workers.py` | New worker: analyze_filing_text |
| `api/src/margin_api/services/edgar/daily_update.py` | Trigger text extraction after XBRL |
| `engine/src/margin_engine/scoring/quantitative/sentiment_score.py` | Consume cached analysis |

### Config/Data Dependencies

- **Anthropic API key** for Claude calls (environment variable)
- Compute: ~5 sec/filing for Claude analysis, 2000 filings/quarter
- Storage: ~10MB/quarter for text + analysis cache
- Must handle filing format variations (old filings have different HTML structure)

### Test Strategy

- Unit test: text extraction from sample 10-K HTML (use Apple 2024 filing as fixture)
- Unit test: Claude response parsing into structured schema (mock API response)
- Integration test: end-to-end filing → text → analysis → cache → scoring
- Determinism test: same filing → same analysis (temperature=0)

---

## C2: TAM Expansion Velocity

**Effort: Large**

### Problem

No measurement of how fast a company is expanding into its total addressable market.
Two companies with identical current ROIC can have vastly different futures if one is
capturing share in a growing market while the other is mature.

### Current State

- XBRL extracts total revenue only — no segment or geographic breakdown
- No industry growth rate reference data
- No segment revenue tracking

### Design

**Dependency: C1 Phase 1 (text extraction)** — 10-K segment tables are in Item 8
(Financial Statements), which requires HTML table parsing from filing text.

**Step 1: Segment Revenue Extraction**

New parser in `api/src/margin_api/services/edgar/segment_parser.py`:
```python
class SegmentParser:
    """Parse segment revenue tables from 10-K Item 8."""

    def parse_segments(self, financial_statements_html: str) -> list[SegmentRevenue]:
        """Extract revenue by segment (product line, geography, business unit).

        Returns list of SegmentRevenue(name, revenue, year).
        Handles common table formats:
        - "Revenue by Segment", "Revenue by Geography"
        - Nested tables, footnotes, restated figures
        """
```

New DB table:
```sql
CREATE TABLE segment_revenue_history (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    filing_date DATE NOT NULL,
    segment_name TEXT NOT NULL,
    segment_type TEXT NOT NULL,         -- 'product', 'geography', 'business_unit'
    revenue DECIMAL NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker, filing_date, segment_name)
);
```

**Step 2: Industry Growth Rate Reference**

Hardcoded reference table for GICS sub-industry growth rates:
```python
INDUSTRY_GROWTH_RATES: dict[str, float] = {
    "cloud_computing": 0.15,      # ~15% CAGR
    "cybersecurity": 0.12,
    "electric_vehicles": 0.25,
    "traditional_auto": 0.02,
    "payments": 0.10,
    "enterprise_software": 0.08,
    # ... ~50 sub-industries
}
```

Updated annually from industry reports. Stored in config, not external API.

**Step 3: TAM Expansion Velocity Factor**

New `scoring/quantitative/tam_expansion.py`:
```python
def tam_expansion_velocity(
    segment_revenues: list[SegmentRevenue],
    industry_growth_rate: float,
    lookback_years: int = 3,
) -> FactorScore:
    """Compute TAM expansion velocity.

    velocity = company_segment_cagr / industry_growth_rate
    - velocity > 1.5 → gaining share in growing market (strong signal)
    - velocity 1.0-1.5 → growing with market (neutral)
    - velocity < 1.0 → losing share (negative signal)

    Score = min(velocity / 2.0, 1.0) * 10  (0-10 scale)
    """
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/services/edgar/segment_parser.py` | New segment extraction |
| `api/src/margin_api/db/models.py` | New segment_revenue_history table |
| `engine/src/margin_engine/scoring/quantitative/tam_expansion.py` | New factor |
| `engine/src/margin_engine/config/industry_growth_rates.py` | Reference data |

### Test Strategy

- Unit test: parse segment table from real 10-K HTML (Apple, Microsoft)
- Unit test: velocity calculation with known CAGR and industry rate
- Golden value: Apple services segment growing at 2x industry → high score
- Edge case: company with single segment, no segmentation in filing

---

## C3: Moat Source Classification

**Effort: Medium**

### Problem

`moat_durability.py` detects 4 quantitative signatures (operating_leverage, pricing_power,
scale_economics, capital_efficiency) but cannot distinguish moat *types* (network effects,
switching costs, brand, regulatory). Moat type matters for durability prediction —
network effects are more durable than pricing power alone.

### Current State

**`scoring/quantitative/moat_durability.py`:**
```python
_SIGNATURE_WEIGHTS = {
    "operating_leverage": 1.5,
    "pricing_power": 1.25,
    "scale_economics": 1.0,
    "capital_efficiency": 0.75,
}
```
Each signature is boolean (detected or not). Raw value = weighted sum normalized to 0-4.

### Design

**Phase 1: Quantitative Moat Proxies (no C1 dependency)**

Extend `moat_durability.py` with quantitative proxy detection:

```python
def _detect_switching_costs(history: FinancialHistory) -> float:
    """Proxy: High SGA/Revenue ratio (support-intensive) + low revenue churn.
    Revenue retention > 95% for 3+ years with SGA > 20% → 0.8 confidence."""

def _detect_regulatory_moat(sector: GICSSector) -> float:
    """Deterministic: Utilities, Insurance → 1.0. Pharma with patents → 0.7.
    Other sectors → 0.0."""

def _detect_brand_moat(history: FinancialHistory, profile: AssetProfile) -> float:
    """Proxy: Gross margin >> sector median (sustained 5+ years) + P/E premium.
    Luxury/consumer staples with GM > sector_median + 15pp → 0.7 confidence."""
```

**Phase 2: NLP-Derived Moat Types (depends on C1)**

Add Claude API extraction for moat keywords from MD&A:
- "switching costs", "customer lock-in", "ecosystem", "platform"
- "network effects", "marketplace", "two-sided", "flywheel"
- "brand equity", "premium pricing", "customer loyalty"
- "regulatory barrier", "license", "patent portfolio"

Confidence from NLP = mention frequency × context relevance.

**Return enhanced metadata:**
```python
class MoatClassification(BaseModel):
    primary_moat: str         # "switching_costs", "network_effects", "brand", "regulatory", "none"
    confidence: float         # 0-1
    secondary_moats: list[str]
    quantitative_score: float # Existing 0-4 score
    nlp_score: float | None   # From Phase 2
```

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/moat_durability.py` | Add proxy detectors, classification |
| `engine/src/margin_engine/models/scoring.py` | Add MoatClassification model (optional) |

### Test Strategy

- Test regulatory moat: Utilities sector → confidence 1.0
- Test brand moat: consumer staples with 50% GM (sector median 35%) → high confidence
- Test switching costs: high SGA/Revenue + stable revenue → detected
- Test no moat: commodity producer → all proxies return 0

---

## C4: Inflection Detection Factor

**Effort: Medium — No external data dependencies**

### Problem

No factor detects when a company crosses a fundamental inflection point — margin
expansion, FCF turning positive, or operating leverage kicking in. These are
high-alpha events that predict future outperformance.

### Current State

- `operating_leverage.py` exists: `rev_growth / opex_growth`, capped at 10.0
- Quarterly financial data available in `FinancialHistory.periods`
- `FinancialPeriod` contains income, balance, cash flow statements with all needed fields
- No structured inflection detection combining multiple signals

### Design

New `engine/src/margin_engine/scoring/quantitative/inflection_detection.py`:

```python
def inflection_score(history: FinancialHistory) -> FactorScore:
    """Detect margin, FCF, and leverage inflection points.

    Returns 0-10 score based on recency + magnitude of inflections.
    """
```

**Three signal components:**

**Signal 1: Operating Expense Deleverage (0-4 points)**
- Detect OpEx/Revenue ratio declining for 2+ consecutive periods
- Score by magnitude: each 100bps/period decline = 1 point, max 4
```python
def _opex_deleverage(history: FinancialHistory) -> float:
    """OpEx/Revenue declining 2+ consecutive periods.
    Score = min(consecutive_declines * magnitude_per_period / 0.01, 4.0)"""
```

**Signal 2: FCF Crossover (0-3 points)**
- Detect free cash flow turning positive after negative streak
- Higher score for longer prior negative streak (deeper turnaround)
```python
def _fcf_crossover(history: FinancialHistory) -> float:
    """FCF positive in last 2 periods after prior negatives.
    Score = min(prior_negative_streak_length, 3.0)"""
```

**Signal 3: Margin Expansion Toward Historical Highs (0-3 points)**
- Gross margin trending toward all-time high with consistent improvement
- Score by proximity: within 200bps of ATH after 3+ periods of expansion
```python
def _margin_expansion(history: FinancialHistory) -> float:
    """GM expanding toward historical high.
    Score by proximity to ATH * consistency of expansion."""
```

**Composite:** `score = opex_deleverage + fcf_crossover + margin_expansion` (0-10 scale)

**Metadata includes:**
```python
{
    "opex_deleverage_detected": bool,
    "fcf_crossover_detected": bool,
    "margin_expansion_magnitude": float,
    "periods_since_inflection": int,
}
```

### Files to Create

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/inflection_detection.py` | New factor |

### Config/Data Dependencies

None — pure quantitative, uses existing `FinancialHistory.periods` data.

### Test Strategy

- Test OpEx deleverage: OpEx/Rev declining 0.35 → 0.33 → 0.31 → score > 0
- Test FCF crossover: FCF goes [-100, -50, -20, 10, 30] → detected
- Test margin expansion: GM goes [0.30, 0.32, 0.34, 0.36] toward ATH 0.37 → detected
- Test no inflection: stable company with flat margins → score 0
- Test single period history → graceful fallback, score 0

---

## C5: Drawdown-Triggered Re-Screening

**Effort: Medium**

### Problem

No event-driven re-evaluation when quality companies drop 20-30%+. The scoring pipeline
runs on a fixed schedule (daily batch). A high-conviction compounder that drops 25%
on earnings miss should be immediately re-evaluated — the drawdown may create a buying
opportunity if fundamentals remain intact.

### Current State

- No drawdown detection in scoring pipeline
- `drift_monitor.py` monitors score drift (not price action)
- 7 ARQ cron jobs exist in `workers.py`
- `pit_daily_prices` table has daily price data for the scored universe
- `full_score` worker can re-score individual tickers

### Design

**New ARQ cron job** in `workers.py`:
```python
cron(screen_drawdown_candidates, hour=23, minute=30)  # Daily after pit_update
```

**New service** `api/src/margin_api/services/drawdown_screener.py`:
```python
class DrawdownScreener:
    """Screen scored universe for significant drawdowns."""

    async def find_candidates(
        self,
        session: AsyncSession,
        min_drawdown_pct: float = -0.20,  # 20% decline from 52-week high
    ) -> list[DrawdownCandidate]:
        """Query pit_daily_prices for stocks down >= threshold from 52-week high.

        Only considers stocks in the currently scored universe (have active v4 scores).
        Returns candidates sorted by drawdown magnitude.
        """

    async def trigger_rescreening(
        self,
        session: AsyncSession,
        candidates: list[DrawdownCandidate],
        arq_pool: ArqRedis,
    ) -> int:
        """Enqueue full_score jobs for each candidate.

        Sets force_recount_gates=True so conviction gates are fully re-evaluated
        (not cached from previous run).
        """
```

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

**Governance integration:**
- Drawdown re-screens generate governance events for audit trail
- If conviction changes, the new score follows staged → approved → published pipeline
- Circuit breaker: if >5 re-screens trigger in a day, alert admin (unusual market event)

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/services/drawdown_screener.py` | New service |
| `api/src/margin_api/workers.py` | New cron job, new worker function |
| `api/src/margin_api/db/models.py` | New drawdown_rescreens table |
| `api/alembic/versions/xxx_add_drawdown_rescreens.py` | Migration |

### Config/Data Dependencies

- `pit_daily_prices` table (existing, populated by daily_pit_update)
- `full_score` worker (existing, needs optional `force_recount_gates` param)
- Config: `MARGIN_DRAWDOWN_THRESHOLD=-0.20`, `MARGIN_DRAWDOWN_MAX_DAILY=10`

### Test Strategy

- Unit test: find_candidates with mock price data, verify threshold filtering
- Unit test: 52-week high calculation correctness
- Integration test: trigger re-screen → full_score job enqueued
- Edge case: stock with <252 days of history (use available max)
- Edge case: already re-screened within 7 days → skip (debounce)

---

## C6: Kelly Criterion Position Sizing

**Effort: Small**

### Problem

`v3_position_sizing.py` uses fixed conviction-tier-to-percentage mapping (EXCEPTIONAL
compounder → 15%, HIGH mispricing → 8%). This ignores the actual expected return/risk
profile of each position. Kelly criterion provides mathematically optimal sizing based
on edge and odds.

### Current State

**`scoring/v3_position_sizing.py`:**
```python
_SIZING = {
    "compounder": {CompositeTier.EXCEPTIONAL: 15.0, HIGH: 10.0, MEDIUM: 5.0},
    "mispricing": {CompositeTier.EXCEPTIONAL: 12.0, HIGH: 8.0, MEDIUM: 4.0},
    "both": {CompositeTier.EXCEPTIONAL: 20.0, HIGH: 12.0, MEDIUM: 6.0},
    ...
}
MAX_POSITIONS = 10
```

### Design

New `engine/src/margin_engine/scoring/kelly_position_sizing.py`:

```python
def kelly_position_size(
    win_probability: float,         # From backtest hit rate per conviction tier
    expected_gain: float,           # Mean gain on winning trades (from backtest)
    expected_loss: float,           # Mean loss on losing trades (absolute value)
    volatility: float,              # Historical annualized volatility
    kelly_fraction: float = 0.25,   # Conservative: 25% of full Kelly
    max_position_pct: float = 15.0, # Hard cap
) -> float:
    """Compute position size using fractional Kelly criterion.

    Full Kelly: f* = (p * b - q) / b
    where p = win_probability, b = expected_gain/expected_loss, q = 1 - p

    Fractional Kelly reduces to: kelly_fraction * f*
    Then capped at max_position_pct.
    """
    b = expected_gain / max(expected_loss, 0.01)
    q = 1.0 - win_probability
    full_kelly = (win_probability * b - q) / b
    position = kelly_fraction * max(0, full_kelly) * 100  # Convert to percentage
    return min(position, max_position_pct)
```

**Integration with backtesting:**

Backtest `metrics.py` already computes win_rate. Add:
- `avg_winner_return` and `avg_loser_return` per conviction tier
- Cache these in `backtest_stats` table for real-time position sizing

**Safety constraints:**
```python
class KellyConstraints(BaseModel):
    max_single_position: float = 15.0    # Hard cap per position
    max_top_3_combined: float = 50.0     # Top 3 can't exceed 50%
    max_sector_concentration: float = 30.0  # Per-sector cap
    min_positions: int = 5               # Minimum diversification
```

**Fallback:** When backtest stats unavailable (new factor combos), fall back to
existing fixed tier-based sizing.

### Files to Create/Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/kelly_position_sizing.py` | New Kelly sizing |
| `engine/src/margin_engine/backtesting/metrics.py` | Add avg_winner/loser per tier |
| `engine/src/margin_engine/scoring/v3_position_sizing.py` | Optional: delegate to Kelly |

### Config/Data Dependencies

- Backtest win rate and avg returns per conviction tier (from `backtesting/metrics.py`)
- Historical volatility from `pit_daily_prices`
- No external data — all computable from existing infrastructure

### Test Strategy

- Unit test: Kelly formula with known inputs (p=0.6, b=2.0 → expected f*)
- Unit test: constraints enforcement (cap at 15%, sector at 30%)
- Unit test: kelly_fraction=0.25 produces 25% of full Kelly
- Edge case: win_probability < 0.5 → position size 0 (negative edge)
- Edge case: no backtest stats → fallback to fixed sizing
- Backtest comparison: Kelly vs fixed sizing, measure Sharpe difference
