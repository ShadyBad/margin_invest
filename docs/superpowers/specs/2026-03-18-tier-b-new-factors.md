# Tier B: Engine v2 — New Factors & Data

Technical design doc for 4 items introducing new scoring factors and data sources.
These need adaptation to the actual stack (PostgreSQL + SQLAlchemy + ARQ, not Supabase/LangGraph).

---

## B1: Anti-Consensus Factor

**Effort: Medium**

### Problem

No factor captures the divergence between bearish market sentiment and improving
fundamentals — the core "buy when others are fearful" signal. The existing
`contrarian_signal.py` is a stub that combines negative momentum with quality
percentiles, and `sentiment_score.py` accepts pre-computed LLM sentiment but no LLM
pipeline exists.

### Current State

**`scoring/quantitative/contrarian_signal.py`:**
```python
def contrarian_signal(momentum_percentile: float, quality_percentile: float) -> float:
    """signal = (100 - momentum_percentile) * (quality_percentile / 100)
    Returns 0 if momentum >= 50 (no contrarian signal)."""
```
No real data sources — uses pre-computed percentiles.

**`scoring/quantitative/sentiment_score.py`:**
- Accepts pre-computed sentiment value (-5 to +5 range)
- Normalizes to 0-10 scale
- Has `has_contrarian_signal` boolean for bonus boost (+2.0)
- LLM analysis layer is stubbed — no NLP pipeline (see C1)

**Data providers** (registry.py fallback chain): FMP → yfinance → SEC EDGAR XBRL.
No short interest or analyst rating data currently ingested.

### Design

New factor `scoring/quantitative/anti_consensus.py` combining three signal components:

**Signal 1: Short Interest Divergence (40% weight)**
- Short interest as % of float, ranked vs sector peers
- High short interest + improving fundamentals (ROIC trajectory up) = strong signal
- Data source: Finnhub `/stock/short-interest` (requires API key)
- Fallback: FINRA short sale volume data (free, daily aggregates)

**Signal 2: Analyst Rating Divergence (30% weight)**
- Gap between consensus rating direction (downgrades) and fundamental improvement
- Specifically: analyst downgrades in last 90d while ROIC/GM improving
- Data source: Finnhub `/stock/recommendation` (consensus buy/hold/sell counts)
- FMP alternative: `analyst-estimates` endpoint (already in fallback chain)

**Signal 3: Earnings Revision Strength (30% weight)**
- Direction and magnitude of EPS estimate revisions vs price action
- Positive revisions during price decline = strong anti-consensus signal
- Data source: yfinance has limited estimate data; Finnhub `/stock/eps-surprise`

**Composite formula:**
```python
def anti_consensus_score(
    short_interest_percentile: float,    # 0-100, sector-relative
    analyst_divergence: float,            # -1 to +1 (negative = bearish consensus)
    revision_strength: float,             # -1 to +1 (positive = upward revision)
    fundamental_trajectory: float,        # 0-1 (from ROIC/GM trajectory)
) -> FactorScore:
    signal = (
        0.40 * min(short_interest_percentile / 100, 1.0) * fundamental_trajectory
        + 0.30 * max(-analyst_divergence, 0) * fundamental_trajectory
        + 0.30 * max(revision_strength, 0)
    )
    return FactorScore(raw_value=signal * 10, percentile=None)  # 0-10 scale
```

**Data ingestion changes:**
- Add Finnhub client to `ingestion/providers/` (or extend existing if partial)
- New fields in `AssetProfile` or separate `SentimentData` model:
  `short_interest_pct`, `analyst_consensus`, `eps_revision_3m`
- New ARQ job: `ingest_sentiment_data` (daily, after market close)

### Files to Modify/Create

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/anti_consensus.py` | New factor |
| `engine/src/margin_engine/ingestion/providers/finnhub_provider.py` | New/extend provider |
| `api/src/margin_api/db/models.py` | New `sentiment_data` table or extend asset_data |
| `api/src/margin_api/workers.py` | New `ingest_sentiment_data` cron job |

### Config/Data Dependencies

- **Finnhub API key** required (environment variable `FINNHUB_API_KEY`)
- New DB table for sentiment data cache
- Rate limits: Finnhub free tier = 60 calls/min (sufficient for ~500 universe)

### Test Strategy

- Unit tests for anti_consensus_score with known inputs
- Test signal components independently (divergence calc, revision strength)
- Mock Finnhub responses for integration tests
- Golden-value test: stock with high short interest + improving ROIC → high score

---

## B2: Sector Exclusion Removal + Adaptive Scoring

**Effort: Large**

### Problem

Financials and Real Estate are completely excluded from scoring. This eliminates banks
(JPM, BAC), insurance (BRK, PGR), and REITs (AMT, PLD) — sectors that represent ~16% of
S&P 500 market cap. The exclusion exists because standard ROIC/FCF metrics don't apply to
these sectors, but the right approach is sector-specific factor substitution.

### Current State

**Exclusion logic** in `scoring/filters/liquidity.py`:
```python
_EXCLUDED_SECTORS: frozenset[GICSSector] = frozenset({
    GICSSector.FINANCIALS,
    GICSSector.REAL_ESTATE,
})
```

Also in `config/filter_config.py`:
```python
excluded_sectors: list[str] = Field(default_factory=lambda: ["Financials", "Real Estate"])
```

**GICS sectors** in `models/financial.py` — 11 sectors, all represented in enum.

**Sector-specific overrides** that already exist:
- Market cap: Utilities $1B, Energy $500M (in `liquidity.py`)
- Gross margin: sector-specific thresholds in `mediocrity_gate.py`
- Cyclical normalization: 7-year median for Energy/Materials (in `cyclical_normalizer.py`)

### Design

**Phase 1: Sector factor substitution config**

New config in `v3_scoring_config.py`:
```python
class SectorFactorOverrides(BaseModel):
    """Sector-specific factor substitutions."""
    profitability_metric: str = "roic"         # Default
    cash_flow_metric: str = "fcf"              # Default
    reinvestment_metric: str = "reinvestment_rate"  # Default
    moat_proxy: str = "standard"               # Default moat detection

SECTOR_OVERRIDES: dict[GICSSector, SectorFactorOverrides] = {
    GICSSector.FINANCIALS: SectorFactorOverrides(
        profitability_metric="roe",
        cash_flow_metric="ppnr",          # Pre-Provision Net Revenue
        reinvestment_metric="deposit_growth",
        moat_proxy="regulatory_franchise",
    ),
    GICSSector.REAL_ESTATE: SectorFactorOverrides(
        profitability_metric="ffo_yield",
        cash_flow_metric="affo",
        reinvestment_metric="occupancy_rate",
        moat_proxy="asset_scarcity",
    ),
}
```

**Phase 2: Adapter functions**

New `scoring/sector_adapters.py`:
```python
def get_profitability(period: FinancialPeriod, sector: GICSSector) -> float:
    """Return ROIC for most sectors, ROE for Financials, FFO yield for REITs."""
    overrides = SECTOR_OVERRIDES.get(sector)
    if overrides is None or overrides.profitability_metric == "roic":
        return compute_roic(period)
    if overrides.profitability_metric == "roe":
        return compute_roe(period)
    if overrides.profitability_metric == "ffo_yield":
        return compute_ffo_yield(period)
    return compute_roic(period)
```

**Phase 3: XBRL extraction for sector metrics**

Add to `xbrl_parser.py` tag mapping:
- ROE: already computable from `net_income / total_equity`
- AFFO: Needs `depreciation + amortization` (have depreciation, need amortization)
- NIM: Needs `interest_income`, `interest_expense` (have expense, need income)
- FFO: `net_income + depreciation - gains_on_sale` (partially available)

**Phase 4: Remove exclusion**

Remove `_EXCLUDED_SECTORS` from `liquidity.py` and `excluded_sectors` from
`filter_config.py`. Replace with sector-aware scoring via adapters.

### Files to Modify/Create

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/sector_adapters.py` | New adapter functions |
| `engine/src/margin_engine/config/v3_scoring_config.py` | Add SectorFactorOverrides |
| `engine/src/margin_engine/scoring/filters/liquidity.py` | Remove _EXCLUDED_SECTORS |
| `engine/src/margin_engine/config/filter_config.py` | Remove excluded_sectors |
| `api/src/margin_api/services/edgar/xbrl_parser.py` | Add sector-specific XBRL tags |
| `engine/src/margin_engine/scoring/v3_cascade.py` | Use adapters for profitability metrics |

### Config/Data Dependencies

- New XBRL tags for interest_income, amortization (EDGAR data, no API cost)
- ROE computable from existing data (net_income / equity)
- AFFO/FFO require additional balance sheet items
- No new external APIs — all from SEC EDGAR

### Test Strategy

- Unit tests for each adapter function with known financial data
- Integration test: score a bank (JPM-like data), verify ROE used instead of ROIC
- Integration test: score a REIT (AMT-like data), verify FFO yield used
- Regression test: non-financial sectors still use ROIC (no change)
- Backtest: compare universe with/without Financials+RE inclusion

---

## B3: Market Cap/Liquidity Redesign

**Effort: Medium**

### Problem

The current $300M market cap floor is a binary pass/fail filter. A $299M company is fully
excluded while a $301M company gets full treatment. This misses high-quality small caps
and doesn't penalize illiquid large-caps. Liquidity v2 exists with tiered dollar-volume
thresholds but is still binary.

### Current State

**`config/filter_config.py`:**
```python
min_market_cap: Decimal = Decimal("300_000_000")  # $300M
```

**`scoring/filters/liquidity.py`:**
- `_DEFAULT_MARKET_CAP = Decimal("300_000_000")`
- Sector overrides: Utilities $1B, Energy $500M
- `DollarVolumeTiers`: mega $50M, large $20M, mid $5M, small $2M
- `liquidity_check_v2()`: position fill test (5 days at 5% participation),
  divergence ratio (90d/20d median <= 3.0)

### Design

**Replace binary filter with continuous liquidity score** (0-100).

New `scoring/quantitative/liquidity_score.py`:
```python
def liquidity_score(
    market_cap: float,
    avg_daily_volume: float,
    divergence_ratio: float,  # 90d/20d median volume ratio
    sector: GICSSector,
) -> FactorScore:
    """Continuous liquidity score replacing binary filter.

    Components (equal weight):
    1. Market cap tier score (0-100): log-scaled, 100 at $200B+, 0 at <$100M
    2. Turnover ratio (0-100): ADV / market_cap, ranked vs peers
    3. Liquidity stability (0-100): 100 - min(divergence_ratio * 20, 100)
    """
```

**Integrate as scoring factor** (not elimination filter):
- Remove from `run_elimination_filters()` pipeline
- Add as 5th factor in Track A or as a score modifier
- Alternatively: keep as filter but with continuous penalty applied to composite score

**Regime-aware tightening:**
- When VIX > 25: tighten divergence_ratio threshold from 3.0 → 2.0
- When market cap < $500M: require higher ADV/market_cap ratio
- Wire through existing `RegimeAdjustments` mechanism

### Files to Modify/Create

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/liquidity_score.py` | New continuous score |
| `engine/src/margin_engine/scoring/filters/liquidity.py` | Keep as backstop, soften threshold |
| `engine/src/margin_engine/config/filter_config.py` | Add liquidity score params |

### Config/Data Dependencies

- Market cap: already in `AssetProfile.market_cap`
- ADV: already in `avg_daily_volume` (PIT pipeline computes this)
- Divergence ratio: computed from `PriceBar` data (already available)
- VIX: not currently ingested — would need external source or proxy (Shiller CAPE ≥ 30
  as proxy for tightening)

### Test Strategy

- Unit tests: market cap $100M → low score, $200B → high score
- Unit tests: high divergence ratio → low stability score
- Integration: small-cap with excellent fundamentals gets non-zero score (currently excluded)
- Backtest: compare universe expansion with continuous scoring vs binary cutoff

---

## B4: Insider Signal Upgrade

**Effort: Small**

### Problem

`insider_cluster.py` detects coordinated buying (3+ insiders in 90d) but misses
important signal dimensions: drawdown context, purchase magnitude, and first-ever-buy
detection. These are well-documented alpha signals in academic literature.

### Current State

**`scoring/quantitative/insider_cluster.py`:**
```python
def insider_cluster_score(transactions: list[InsiderTransaction]) -> FactorScore:
    """Detects coordinated insider purchasing:
    - 3+ distinct insiders buying within 90 days
    - Purchases >= $100K
    - CEO/CFO weighted 2x vs directors/others
    Returns weighted_score on raw scale (0-inf)."""
```

**`InsiderTransaction` model** (in `models/financial.py` or similar):
- `insider_name`, `title`, `transaction_type`, `shares`, `price_per_share`,
  `total_value`, `filing_date`

**Data source**: SEC Form 4 filings (already fetched via EDGAR pipeline).

### Design

**Enhancement 1: Drawdown Context (1.5x boost)**

Add `price_drawdown_pct` parameter to scoring function. When stock is down >10% from
recent high during the insider buy window, apply 1.5x multiplier to cluster score.

```python
def insider_cluster_score(
    transactions: list[InsiderTransaction],
    price_drawdown_pct: float | None = None,  # New param
) -> FactorScore:
    # ... existing cluster detection ...
    if price_drawdown_pct is not None and price_drawdown_pct < -0.10:
        weighted_score *= 1.5
```

Price data already available from `pit_daily_prices`. Compute drawdown = current price
vs 52-week high. Pass to scoring function from pipeline.

**Enhancement 2: Conviction Magnitude (tiered boost)**

Replace flat $100K minimum with tiered magnitude scoring:
```python
def _magnitude_boost(total_buy_value: float) -> float:
    if total_buy_value >= 5_000_000:
        return 2.0   # $5M+ = very high conviction
    if total_buy_value >= 1_000_000:
        return 1.5   # $1M-$5M = high conviction
    if total_buy_value >= 100_000:
        return 1.0   # $100K-$1M = baseline
    return 0.5        # <$100K = low conviction
```

**Enhancement 3: First-Ever-Buy Detection (10x weight)**

Query full Form 4 history for each insider. If this is their first purchase in this
stock, apply 10x weighting (extremely rare and high-signal event).

Requires extending the Form 4 data retention window beyond 90 days. Store all
transactions and flag `is_first_ever_buy` during ingestion.

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/insider_cluster.py` | Add drawdown context, magnitude tiers, first-buy flag |
| `engine/src/margin_engine/models/financial.py` | Extend InsiderTransaction with optional fields |
| Pipeline call site (v3_pipeline/v4_pipeline) | Pass drawdown_pct from price data |

### Config/Data Dependencies

- Price drawdown: computable from existing `pit_daily_prices` (52-week high vs current)
- Magnitude: already available in `InsiderTransaction.total_value`
- First-ever-buy: requires expanded Form 4 history retention (currently 90d window).
  Extend `ingest_insider_transactions` to store full history.

### Test Strategy

- Test drawdown boost: cluster during -15% drawdown → 1.5x score vs baseline
- Test magnitude tiers: $5M buy → 2x, $500K → 1x, $50K → 0.5x
- Test first-buy: first-ever purchase → 10x weight
- Test backward compat: no new params → identical to current behavior
