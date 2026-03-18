# Tier B: Engine v2 — New Factors & Data

Design spec for 4 items introducing new scoring factors, data sources, and sector expansion. All new signals integrate as **post-composite score modifiers** — the 4-factor geometric mean composite is unchanged.

---

## Architecture: Score Modifier Pattern

All 4 items share a common integration: post-composite multipliers applied after the v3/v4 cascade produces a composite score, before conviction gate assessment.

```
Existing pipeline (unchanged):
  Universe → Elimination Filters → v3/v4 Cascade (4 factors) → Composite Score + Conviction

New modifier layer (applied AFTER cascade, affects score for ranking/sizing):
  Composite Score
    × anti_consensus_modifier (B1)    # range: 0.90 - 1.15
    × liquidity_modifier (B3)         # range: 0.85 - 1.00
    × insider_signal_modifier (B4)    # range: 1.00 - 1.15
    = Modified Composite Score → used for ranking, position sizing, and display
```

**Sequencing clarification**: Conviction tier is determined inside the cascade functions (`run_track_a_cascade`, `run_track_b_cascade`) alongside the composite score. Modifiers are applied **after** the cascade returns, so they affect the score used for ranking and position sizing but do **not** change the conviction tier. This is intentional — conviction tiers are a fundamental quality classification, while modifiers capture tactical/timing signals that should influence portfolio weighting without reclassifying the asset.

B2 (Sector Exclusion Removal) is structural — it modifies which assets enter the pipeline and how the cascade computes profitability, not the output score.

**New engine module**: `engine/src/margin_engine/scoring/score_modifiers.py` — all modifier functions. Each returns a float multiplier.

**Modifier bounds** (enforced in the pipeline, not per-modifier):
- Per-modifier floor: 0.80
- Per-modifier ceiling: 1.20
- Combined product floor: 0.75
- Combined product ceiling: 1.25

---

## B1: Anti-Consensus Factor (Modifier)

**Effort: Medium**

### Purpose

Detect divergence between bearish market sentiment and improving fundamentals. Boosts scores when the market is wrong about a company's trajectory.

### Data Sources

Extend the existing `FinnhubProvider` (already in stack at `engine/src/margin_engine/ingestion/providers/finnhub_provider.py`) with two new methods:

```python
def fetch_short_interest(self, ticker: str) -> FetchResult:
    """Finnhub /stock/short-interest — short interest as % of float."""

def fetch_analyst_recommendations(self, ticker: str) -> FetchResult:
    """Finnhub /stock/recommendation — consensus buy/hold/sell counts over time."""
```

**Earnings revision proxy**: Uses existing `fetch_earnings()` EPS surprise data. This is a **proxy** for true analyst estimate revisions — EPS surprise (actual vs estimate) measures whether the company beat expectations, not whether estimates changed directionally. True revision tracking would require ingesting estimate snapshots over time (not currently available). The surprise proxy captures a correlated signal: consistent positive surprises indicate upward estimate trajectory.

**Finnhub rate limits**: Free tier = 60 calls/min. With universe expansion to ~3,500 tickers and 2 new endpoints per ticker (short interest + analyst recs), `ingest_sentiment_signals` needs ~7,000 calls → ~2 hours at free tier. Combined with existing Finnhub jobs (earnings, insider, news), total daily Finnhub volume is ~18,000 calls. **Recommendation**: upgrade to paid Finnhub tier ($149/mo, 300 calls/min) or implement aggressive caching (only re-fetch sentiment signals weekly, not daily, since short interest and analyst ratings change slowly).

### Data Storage

New DB table (API layer):

```sql
CREATE TABLE sentiment_signals (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    signal_date DATE NOT NULL,
    short_interest_pct FLOAT,
    analyst_consensus JSONB,
    eps_revision_direction FLOAT,
    fetched_at TIMESTAMPTZ NOT NULL,
    UNIQUE (ticker, signal_date)
);
```

New ARQ job: `ingest_sentiment_signals` — daily at 23:45 UTC (after `pit_daily_update` at 23:00 and `daily_form4_update` at 23:30). Iterates scored universe, fetches short interest + analyst recs.

### Modifier Function

```python
def anti_consensus_modifier(
    short_interest_percentile: float,    # 0-100, sector-relative rank
    analyst_divergence: float,           # -1 to +1 (negative = bearish consensus)
    eps_revision_strength: float,        # -1 to +1 (positive = upward revision)
    fundamental_trajectory: float,       # 0-1 (ROIC/GM improving)
) -> float:
    """Returns multiplier 0.90 - 1.15.

    Three weighted signal components:
    - Short interest divergence (40%): high short + improving fundamentals
    - Analyst rating divergence (30%): downgrades while fundamentals improve
    - Earnings revision strength (30%): positive revisions during price decline

    Only fires meaningfully when fundamental_trajectory > 0.5 (fundamentals
    are actually improving). Without fundamental backing, bearish sentiment is
    probably correct — modifier stays near 1.0 or slightly penalizes.

    The asymmetric range (0.90-1.15) is intentional: penalization is capped
    conservatively because the modifier is based on external sentiment data
    (noisier than fundamental factors), while the upside is slightly wider
    because anti-consensus signals have demonstrated alpha in literature.
    """
```

**`fundamental_trajectory` computation**: Derived in the pipeline (v3/v4) before modifiers are called, since `FinancialHistory` is in scope during scoring but not at the modifier layer. Computed as:

```python
def compute_fundamental_trajectory(history: FinancialHistory) -> float:
    """Compare latest vs prior period ROIC and gross margin.

    Returns 0-1:
    - 1.0: both ROIC and GM improving for 2+ consecutive periods
    - 0.5: one metric improving, one flat/declining
    - 0.0: both declining
    """
```

Added to `TickerV3Data` and `TickerV4Data` as `fundamental_trajectory: float = 0.5` (neutral default).

### Relationship to Existing Stubs

`contrarian_signal.py` and `sentiment_score.py` both exist as stubs (marked `stub=True`). The anti-consensus modifier replaces their intended purpose. Stubs remain as-is for now — can be deprecated in a future cleanup.

### Files to Modify/Create

| File | Change |
|------|--------|
| `engine/src/margin_engine/ingestion/providers/finnhub_provider.py` | Add `fetch_short_interest()`, `fetch_analyst_recommendations()` |
| `engine/src/margin_engine/scoring/score_modifiers.py` | **New** — `anti_consensus_modifier()`, `compute_fundamental_trajectory()` |
| `engine/src/margin_engine/scoring/v3_pipeline.py` | Add `fundamental_trajectory` to `TickerV3Data` |
| `engine/src/margin_engine/scoring/v4_pipeline.py` | Add `fundamental_trajectory` to `TickerV4Data` |
| `api/src/margin_api/db/models.py` | New `sentiment_signals` table |
| `api/alembic/versions/xxx_add_sentiment_signals.py` | Migration |
| `api/src/margin_api/workers.py` | New `ingest_sentiment_signals` cron job |

### Test Strategy

- Unit tests: modifier with known inputs → known multiplier
- High short interest + improving ROIC → ~1.10-1.15
- Bearish consensus + declining fundamentals → ~0.90-0.95
- All neutral signals → exactly 1.0
- Mock Finnhub responses for integration tests
- Golden-value: "high short interest compounder" archetype

---

## B2: Sector Exclusion Removal + Adaptive Scoring

**Effort: Large**

### Purpose

Unlock Financials (~300-500 tickers) and Real Estate (~80-150 tickers) by removing the exclusion at all three layers and substituting sector-appropriate profitability proxies.

### Current Exclusion Points (3 layers)

1. **Universe builder** — `cli.py:1765`: `excluded_sectors = ["Financial Services", "Real Estate"]` in `screen_us_equities()` call. yfinance screener never fetches these sectors.
2. **Elimination filter** — `liquidity.py:53`: `_EXCLUDED_SECTORS = frozenset({FINANCIALS, REAL_ESTATE})`. Assets in these sectors fail the filter immediately.
3. **Scoring cascade** — all profitability computation uses ROIC, which is inappropriate for banks (no meaningful invested capital) and REITs (depreciation-heavy).

Current universe: 3,056 tickers with zero Financials or Real Estate (confirmed via `assets` table query).

### Layer 1: Universe Builder

```python
# cli.py:1765 — change
# Before
excluded_sectors = ["Financial Services", "Real Estate"]
# After
excluded_sectors = []  # All GICS sectors eligible
```

Update description string and log messages. `screen_us_equities()` already accepts `excluded_sectors` as a parameter.

Expected universe expansion: ~3,056 → ~3,500-3,700 tickers.

### Layer 2: Elimination Filter

Changes to `liquidity.py`:
1. Remove `_EXCLUDED_SECTORS` frozenset
2. Remove sector exclusion check block in `liquidity_check()` (lines 128-142)
3. Remove sector exclusion check block in `liquidity_check_v2()` (lines 240-248)
4. Remove `excluded_sectors` from `LiquidityConfig` in `filter_config.py`
5. Remove `is_excluded_v1` property from `GICSSector` in `financial.py`

New market cap overrides for the new sectors:
```python
_SECTOR_MARKET_CAP = {
    GICSSector.UTILITIES: Decimal("1_000_000_000"),
    GICSSector.ENERGY: Decimal("500_000_000"),
    GICSSector.FINANCIALS: Decimal("500_000_000"),     # New — exclude tiny community banks
    GICSSector.REAL_ESTATE: Decimal("1_000_000_000"),  # New — REITs need scale
}
```

### Layer 3: Sector Adapters

New file `engine/src/margin_engine/scoring/sector_adapters.py`:

```python
class SectorAdapter:
    """Translates sector-specific financials to a common profitability metric."""

    @staticmethod
    def profitability_metric(period: FinancialPeriod, sector: GICSSector) -> float | None:
        """Return the appropriate profitability metric for a sector.

        - Most sectors: ROIC (existing computation)
        - Financials: ROE = net_income / total_equity
        - Real Estate: crude FFO proxy = (net_income + depreciation) / total_equity

        ROE and FFO proxy are computable from existing XBRL fields — no new
        extraction needed. Accuracy can be improved later by adding
        sector-specific XBRL fields (PPNR, AFFO, NIM, etc.).
        """

    @staticmethod
    def metric_name(sector: GICSSector) -> str:
        """Return human-readable metric name for display/audit."""
```

### Layer 4: Downstream Filter Adaptations

Several elimination filters implicitly assume non-financial company financials. Without adaptations, Financials tickers would systematically fail these filters even after the sector exclusion is removed, rendering the inclusion moot.

**Filters requiring sector exemptions for Financials:**

| Filter | Problem for Financials | Solution |
|--------|----------------------|----------|
| **FCF distress** (`fcf_distress.py`) | Bank operating cash flow includes loan originations/repayments — semantically different from industrial FCF. `FcfDistressConfig.sector_margin_overrides` explicitly excludes Financials. | Add `GICSSector.FINANCIALS` to exempt sectors in `FcfDistressConfig` |
| **Beneish M-Score** | Designed for manufacturing/industrial. DSRI, Depreciation Index, Asset Quality Index produce meaningless values for banks. Academic literature confirms it is inappropriate for financial institutions. | Add `GICSSector.FINANCIALS` to exempt sectors |
| **Current ratio** | Banks have structurally low current ratios (deposits are current liabilities). A healthy bank at 0.8 current ratio would be flagged. | Add `GICSSector.FINANCIALS` to exempt sectors in `CurrentRatioConfig` |
| **Interest coverage** | Bank interest expense IS the core business cost, not a solvency indicator. The filter produces meaningless results. | Add `GICSSector.FINANCIALS` to exempt sectors in `InterestCoverageConfig` |
| **Altman Z-Score** | Z'' (service variant) may produce marginally acceptable results but was not designed for banks. `AltmanConfig.exempt_sectors` currently only includes Utilities. | Add `GICSSector.FINANCIALS` to `AltmanConfig.exempt_sectors` |

**Filters for Real Estate:**

| Filter | Problem for REITs | Solution |
|--------|-------------------|----------|
| **FCF distress** | REIT depreciation is enormous (buildings), making FCF look negative when underlying cash flow is healthy. | Add `GICSSector.REAL_ESTATE` to exempt sectors |
| **Beneish M-Score** | Depreciation Index component distorted by REIT accounting. | Add `GICSSector.REAL_ESTATE` to exempt sectors |

Other filters (mediocrity gate, profitability floor) will work correctly once sector adapters provide the right profitability metric.

**Implementation**: Each filter config model already has an `exempt_sectors` or `sector_overrides` pattern. Adding Financials/RE to these lists is a config-only change per filter — no algorithmic changes needed.

**XBRL validation note**: The crude ROE and FFO proxy computations assume that `net_income`, `depreciation`, and `total_equity` parse correctly from bank and REIT 10-K filings. These filings may use a different XBRL taxonomy (`us-gaap:banking`). During implementation, validate parsing against sample filings (e.g., JPM 10-K, AMT 10-K) and add taxonomy-aware fallbacks if needed.

### Percentile Normalization for Conviction Gates

The conviction gates currently use absolute ROIC thresholds. For Financials and Real Estate, these thresholds are meaningless (ROE and ROIC have different normal ranges). Solution: **percentile-normalize within sector for new sectors only**.

```python
def sector_percentile_rank(
    ticker_metric: float,
    sector: GICSSector,
    universe_metrics: dict[GICSSector, list[float]],
) -> float:
    """Rank a ticker's profitability metric within its sector peers. Returns 0-100."""
```

**Gate wiring detail**: `sector_percentile_rank()` is called in `v3_cascade.py` when the sector requires percentile gates. The percentile value replaces the raw metric before being passed to `conviction_gates.py`. Specifically:

- **Track A** (`run_track_a_cascade`): The capital-light bypass at lines 94-103 computes `median_roic` from `_nopat_and_ic()`. For Financials/RE, replace this with `SectorAdapter.profitability_metric()` → `sector_percentile_rank()`, then compare against percentile thresholds instead of absolute 0.25.
- **Track A conviction**: `assess_track_a_conviction()` in `v3_thresholds.py` receives `roic_median`. For Financials/RE, pass the sector percentile (0-100) instead, with a translated config mapping percentile thresholds to conviction tiers.
- **Track B** (`run_track_b_cascade`): `_current_roic()` (line 222) and `_is_roic_improving()` (line 244) compute ROIC directly from EBIT. Replace with `SectorAdapter` for Financials/RE.
- **Track B conviction**: `assess_track_b_conviction()` receives `roic_median`. Same percentile translation as Track A.

Gate translation (Financials/RE only):

| Current (absolute ROIC) | Percentile equivalent |
|---|---|
| ROIC >= 25% → capital-light bypass | >= 90th percentile |
| ROIC >= 15% → exceptional reinvestment | >= 75th percentile |
| ROIC >= 8% → unconditional pass | >= 50th percentile |
| ROIC < 8% → trajectory zone | < 50th percentile |

**Scope guard**: Only Financials and Real Estate use percentile gates. All other sectors continue using raw ROIC against absolute thresholds. This minimizes blast radius.

```python
def should_use_percentile_gates(sector: GICSSector) -> bool:
    return sector in (GICSSector.FINANCIALS, GICSSector.REAL_ESTATE)
```

Config: New `SectorPercentileConfig` in `v3_scoring_config.py` with the percentile thresholds above.

### Files to Modify/Create

| File | Change |
|------|--------|
| `api/src/margin_api/cli.py` | Remove `excluded_sectors` from universe builder |
| `engine/src/margin_engine/scoring/filters/liquidity.py` | Remove `_EXCLUDED_SECTORS`, remove exclusion checks |
| `engine/src/margin_engine/config/filter_config.py` | Remove `excluded_sectors`, add Financials/RE market cap overrides, add exempt sectors to `FcfDistressConfig`, `CurrentRatioConfig`, `InterestCoverageConfig` |
| `engine/src/margin_engine/models/financial.py` | Remove `is_excluded_v1` property and `AssetProfile.is_excluded` |
| `engine/src/margin_engine/scoring/sector_adapters.py` | **New** — profitability metric adapters |
| `engine/src/margin_engine/scoring/v3_cascade.py` | Use `SectorAdapter` for Financials/RE, update `_current_roic()`, `_is_roic_improving()` |
| `engine/src/margin_engine/scoring/v3_thresholds.py` | Accept percentile-based input for Financials/RE |
| `engine/src/margin_engine/config/v3_scoring_config.py` | Add `SectorPercentileConfig` |
| `engine/src/margin_engine/scoring/filters/beneish.py` | Add Financials/RE to exempt sectors |
| `engine/src/margin_engine/scoring/filters/altman.py` | Add Financials to `AltmanConfig.exempt_sectors` |

### Test Strategy

- Unit: `SectorAdapter` — Financials → ROE, Real Estate → FFO proxy, Technology → ROIC
- Unit: `sector_percentile_rank` with known distributions
- Unit: Filter exemptions — verify Financials/RE bypass FCF distress, Beneish, current ratio, interest coverage
- Integration: JPM-like bank data → scores through full pipeline using ROE + percentile gates
- Integration: REIT-like data with depreciation-heavy profile → correct FFO proxy
- Regression: all existing non-financial tests pass unchanged (absolute thresholds preserved)
- Verify all `is_excluded_v1` and `AssetProfile.is_excluded` references cleaned up
- XBRL validation: parse sample bank/REIT 10-K, verify `net_income`, `depreciation`, `total_equity` extract correctly

---

## B3: Market Cap/Liquidity Redesign (Modifier)

**Effort: Medium**

### Purpose

Replace the binary $300M market cap cliff with a lowered hard floor ($100M) plus a continuous liquidity modifier that penalizes illiquid names proportionally.

### Hard Floor Changes

`filter_config.py` — change `MarketCapMinimum.default`:
```python
# Before
default: int = 300_000_000
# After
default: int = 100_000_000
```

Note: `backtest_filter_config()` (line 202-224 of `filter_config.py`) already uses $100M as its default for backtesting. This change aligns production with the backtest floor.

Expands eligible universe by ~200-400 small-cap names. They enter scoring but receive liquidity penalties via the modifier.

### Modifier Function

```python
def liquidity_modifier(
    market_cap: float,
    avg_daily_dollar_volume: float,
    divergence_ratio: float | None,
) -> float:
    """Returns multiplier 0.85 - 1.00. Never boosts, only penalizes.

    Three components (equal weight):

    1. Market cap tier (0-1): log-scaled
       - $100B+ → 1.0
       - $10B   → 0.95
       - $1B    → 0.85
       - $100M  → 0.70

    2. Turnover adequacy (0-1): ADV / market_cap
       - >= 0.5% → 1.0
       - = 0.1%  → 0.7
       - Log-scaled between

    3. Liquidity stability (0-1): from divergence ratio
       - <= 1.5  → 1.0 (stable)
       - = 3.0   → 0.7 (evaporating)
       - > 3.0   → 0.5
       - None    → 0.85 (mild penalty for unknown)

    Combined: 0.85 + 0.15 * weighted_average(components)
    Range: [0.85, 1.00]
    """
```

The modifier only penalizes, never boosts. Liquidity is a risk/cost factor, not a quality indicator. A mega-cap with perfect liquidity gets 1.0 (neutral).

### No VIX Dependency

The original spec proposed regime-aware tightening via VIX. Dropped: VIX isn't ingested, and the existing `detect_regime()` in `market_regime.py` can serve this purpose if regime tightening is needed later.

### Data Sources

All inputs already available — no new ingestion:
- `market_cap`: from `AssetProfile.market_cap`
- `avg_daily_dollar_volume`: from `AssetProfile.avg_daily_volume` or `LiquidityProfile`
- `divergence_ratio`: computed from `PriceBar` via existing `liquidity_divergence_ratio()`

### Files to Modify/Create

| File | Change |
|------|--------|
| `engine/src/margin_engine/config/filter_config.py` | Lower `min_market_cap` to $100M |
| `engine/src/margin_engine/scoring/filters/liquidity.py` | Update `_SECTOR_MARKET_CAP` overrides |
| `engine/src/margin_engine/scoring/score_modifiers.py` | Add `liquidity_modifier()` |

### Test Strategy

- $200B mega-cap + high ADV → 1.0 (no penalty)
- $500M small-cap + low ADV → ~0.88
- $100M micro-cap + thin volume → ~0.85 (floor)
- Divergence ratio 4.0 → heavy stability penalty
- Missing divergence ratio → mild default penalty (0.85)
- Integration: small-cap enters pipeline, gets scored with penalty
- Regression: large-cap scores unchanged (modifier = 1.0)

---

## B4: Insider Signal Upgrade (Modifier)

**Effort: Medium** (upgraded from Small due to EDGAR Form 4 pipeline)

### Purpose

Enhance the existing insider cluster detection with three signal dimensions: drawdown context, conviction magnitude, and first-ever-buy detection. Expose as a post-composite modifier.

### Enhancement 1: Drawdown Context (1.5x raw score boost)

When insider buying clusters occur during a >10% drawdown from 52-week high, apply 1.5x multiplier to the raw cluster score.

New parameter on `insider_cluster_score()`:
```python
def insider_cluster_score(
    transactions: list[InsiderTransaction],
    price_drawdown_pct: float | None = None,
) -> FactorScore:
```

Drawdown computed from existing `pit_daily_prices`. New field on `TickerV3Data` and `TickerV4Data`:
```python
high_52w: float | None = None
```

### Enhancement 2: Conviction Magnitude (tiered boost)

Opt-in via new parameter `apply_magnitude: bool = False` to preserve backward compatibility. When False (default), existing behavior is unchanged — golden-value tests pass without modification.

```python
def _magnitude_boost(total_buy_value: float) -> float:
    if total_buy_value >= 5_000_000:   return 2.0
    if total_buy_value >= 1_000_000:   return 1.5
    if total_buy_value >= 100_000:     return 1.0
    return 0.5
```

`total_buy_value` is already computed in the existing function (line 122 of `insider_cluster.py`). The magnitude boost is only applied when `apply_magnitude=True` is explicitly passed by the caller.

### Enhancement 3: First-Ever-Buy Detection (10x weight)

**New EDGAR Form 4 ingestion pipeline.** The EDGAR infrastructure exists for 10-K/10-Q XBRL filings. Form 4 is a different filing type with a different XML schema.

**New service**: `api/src/margin_api/services/edgar/form4_parser.py`

```python
class Form4Parser:
    """Parse SEC Form 4 XML filings for insider transactions.

    Form 4 XML schema fields:
    - issuer: {issuerCik, issuerName, issuerTradingSymbol}
    - reportingOwner: {rptOwnerCik, rptOwnerName, rptOwnerRelationship}
    - nonDerivativeTransaction: {transactionDate, transactionCode,
        transactionShares, transactionPricePerShare}
    - transactionCode: P=purchase, S=sale, A=grant, M=exercise
    """

    def parse(self, form4_xml: str) -> list[InsiderTransaction]:
        """Extract purchase transactions from Form 4 XML."""
```

**New DB table**:

```sql
CREATE TABLE insider_transaction_history (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    insider_cik VARCHAR(10) NOT NULL,
    insider_name TEXT NOT NULL,
    title TEXT NOT NULL,
    transaction_type VARCHAR(10) NOT NULL,
    transaction_date DATE NOT NULL,
    shares BIGINT NOT NULL,
    price_per_share FLOAT,
    total_value FLOAT,
    accession_number VARCHAR(30) NOT NULL,
    filing_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (accession_number, insider_cik, transaction_date)
);

CREATE INDEX ix_insider_hist_ticker ON insider_transaction_history(ticker);
CREATE INDEX ix_insider_hist_insider ON insider_transaction_history(insider_cik, ticker);
```

**New ARQ jobs**:
- `backfill_form4_history` — one-time backfill via EDGAR full-text search index
- `daily_form4_update` — daily cron at 23:30 UTC, fetches new Form 4 filings

**First-ever-buy detection**:

```python
# Lives in API layer (api/src/margin_api/services/insider_service.py), NOT engine
async def is_first_purchase(
    session: AsyncSession,
    ticker: str,
    insider_cik: str,
) -> bool:
    """Check if this insider has ever purchased this stock before.
    Queries insider_transaction_history for any prior 'P' transaction."""
```

**Architecture boundary**: This DB query runs in the API/worker layer. The boolean result is populated on `InsiderTransaction.is_first_purchase` before the model reaches the engine. The engine package remains pure Python with zero web/DB dependencies.

When `is_first_purchase` returns True, that insider's weight is multiplied by 10x (1.0→10.0 for directors, 2.0→20.0 for C-suite).

### InsiderTransaction Model Extension

```python
class InsiderTransaction(BaseModel):
    date: str
    insider_name: str
    title: str
    transaction_type: str
    shares: int
    price_per_share: Decimal
    value: Decimal
    insider_cik: str | None = None        # New
    is_first_purchase: bool | None = None  # New
```

Backward compatible — existing code doesn't use new fields.

### Modifier Function

```python
def insider_signal_modifier(
    cluster_score: float,
    cluster_detected: bool,
    total_buy_value: float,
    price_drawdown_pct: float | None,
    has_first_ever_buy: bool,
) -> float:
    """Returns multiplier 1.00 - 1.15.

    No cluster → 1.0.
    Cluster detected → base 1.05.
    + drawdown > 10% → +0.03
    + magnitude $5M+ → +0.03
    + first-ever-buy  → +0.04
    Maximum: 1.15.

    Never penalizes. Absence of insider buying is not bearish.
    """
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/insider_cluster.py` | Add drawdown, magnitude, first-buy params |
| `engine/src/margin_engine/models/financial.py` | Extend `InsiderTransaction` with optional fields |
| `engine/src/margin_engine/scoring/score_modifiers.py` | Add `insider_signal_modifier()` |
| `engine/src/margin_engine/scoring/v3_pipeline.py` | Add `high_52w` to `TickerV3Data` |
| `engine/src/margin_engine/scoring/v4_pipeline.py` | Add `high_52w` to `TickerV4Data` |
| `api/src/margin_api/services/edgar/form4_parser.py` | **New** — Form 4 XML parsing |
| `api/src/margin_api/services/insider_service.py` | **New** — `is_first_purchase()` DB query (API layer) |
| `api/src/margin_api/db/models.py` | New `insider_transaction_history` table |
| `api/alembic/versions/xxx_add_insider_history.py` | Migration |
| `api/src/margin_api/workers.py` | New `backfill_form4_history`, `daily_form4_update` jobs |

### Test Strategy

- Drawdown: cluster during -15% drawdown → 1.5x raw score
- Magnitude: $5M buy → 2.0x, $500K → 1.0x, $50K → 0.5x
- First-ever-buy: first purchase → 10x weight in cluster
- Modifier range: output always in [1.0, 1.15]
- No cluster: zero transactions → modifier exactly 1.0
- Backward compat: original params only → identical behavior
- Form 4 parser: real Apple/Microsoft Form 4 XML fixtures
- First-buy query: seed history, new insider → `is_first_purchase=True`

---

## Cross-Cutting Concerns

### Modifier Pipeline Wiring

New function in `score_modifiers.py`:

```python
def apply_all_modifiers(
    composite_score: float,
    anti_consensus: float,   # from anti_consensus_modifier()
    liquidity: float,        # from liquidity_modifier()
    insider: float,          # from insider_signal_modifier()
) -> tuple[float, dict[str, float]]:
    """Apply all modifiers to composite score with combined bounds.

    Returns (modified_score, modifier_breakdown).
    Combined product clamped to [0.75, 1.25].
    """
    combined = anti_consensus * liquidity * insider
    combined = max(0.75, min(1.25, combined))
    return composite_score * combined, {
        "anti_consensus": anti_consensus,
        "liquidity": liquidity,
        "insider": insider,
        "combined": combined,
    }
```

Called from `v3_pipeline.py` and `v4_pipeline.py` after composite score computation, before conviction gate assessment. The breakdown dict is stored in score metadata for audit/transparency.

### New Ingestion Jobs Summary

| Job | Schedule | Source | Purpose |
|-----|----------|--------|---------|
| `ingest_sentiment_signals` | Daily 23:45 UTC | Finnhub | Short interest, analyst recs (B1) |
| `backfill_form4_history` | One-time | EDGAR | Historical insider transactions (B4) |
| `daily_form4_update` | Daily 23:30 UTC | EDGAR | New Form 4 filings (B4) |

### New DB Tables Summary

| Table | Purpose | Est. rows/year |
|-------|---------|----------------|
| `sentiment_signals` | Cached Finnhub sentiment data | ~1M (3500 tickers × 252 days) |
| `insider_transaction_history` | Full Form 4 purchase history | ~500K (historical backfill) + ~50K/year |

### Migration Summary

2 new Alembic migrations:
1. `add_sentiment_signals` — B1 table
2. `add_insider_history` — B4 table

Note: B2's `excluded_sectors` is a Pydantic model field on `LiquidityConfig`, not stored in the database — no migration needed for its removal.

### Ordering Constraints

B2 (Sector Exclusion) should be implemented first — it changes the universe and filter pipeline that other items depend on. B1, B3, B4 are independent of each other and can be parallelized.

```
B2 (Sector Exclusion) → then B1, B3, B4 in parallel
```
