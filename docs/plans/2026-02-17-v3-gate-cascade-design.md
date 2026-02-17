# V3 Gate Cascade Pipeline Design

## Goal

Build the complete "glue" layer that connects raw financial data to the v3 conviction engine's scoring components, producing fully scored, conviction-assessed, position-sized results through a gate cascade architecture.

## Context

The v3 conviction engine components (Tasks 1-13) are implemented: moat durability, reverse DCF, ensemble valuation, asset floor, market regime, capital allocation, thresholds, multiplicative composites, position sizing, timing overlay, and orchestrator. What's missing is the pipeline that:

1. Assembles multi-year financial history from the database
2. Computes intermediate metrics (compounding power, catalyst strength, etc.)
3. Runs the sequential gate cascade for each track
4. Applies market regime adjustments to thresholds
5. Produces V3TrackResult objects for the orchestrator
6. Enforces portfolio concentration caps
7. Exposes results through API endpoints and CLI commands

## Architecture: Layered Cascade

Five independent layers, each testable in isolation:

```
Layer 1: Intermediate Calculators (pure functions)
    ↓
Layer 2: Track Cascade Runners (gate evaluation + scoring)
    ↓
Layer 3: Universe Pipeline (batch scoring + peer aggregation + portfolio cap)
    ↓
Layer 4: Data Prerequisites (WACC lookup, FRED CAPE, FinancialHistory assembly)
    ↓
Layer 5: API/CLI Integration (endpoints, DB model, CLI command)
```

## Layer 1: Intermediate Value Calculators

**New file: `engine/src/margin_engine/scoring/v3_intermediates.py`**

Seven pure functions that convert raw financial data into v3 metric inputs:

### `compute_compounding_power(history: FinancialHistory) -> float`
- Computes incremental_ROIC from earliest to latest period
- Gets reinvestment_rate from latest period (1 - payout ratio, approximated from FCF/net_income)
- Gets ROIC CV from roic_stability module
- Formula: `incremental_ROIC * reinvestment_rate * (1 - roic_cv)`
- Returns 0.0 if insufficient data

### `compute_capital_allocation_composite(period: FinancialPeriod, history: FinancialHistory, buyback_yield: float | None, insider_ownership_pct: float | None, sbc_pct: float | None, recent_acquisition_count: int) -> float`
- Runs all 6 sub-factors: buyback_effectiveness, debt_discipline, organic_reinvestment_ratio, insider_ownership_score, sbc_dilution_tax, ma_discipline
- Each sub-factor produces a FactorScore with raw_value
- Normalizes each to 0-1 range (sub-factor specific)
- Returns simple average of available sub-factors (skip if data missing)

### `compute_catalyst_strength(insider_percentile: float, institutional_percentile: float, sue_percentile: float) -> float`
- Returns max() of the three signals
- If all are 0.0, returns 0.0

### `compute_quality_floor_factor(roic: float, roic_improving: bool) -> float`
- ROIC > 0.08: return 1.0
- ROIC <= 0.08 but improving: return 0.5 + 0.5 * min(roic / 0.08, 1.0)
- Otherwise: return 0.0

### `compute_valuation_convergence_factor(converging_count: int) -> float`
- Returns max(converging_count / 4, 0.75) capped at 1.0
- Minimum 0.75 so it doesn't zero out the multiplicative score

### `compute_downside_protection(current_price: float, asset_floor_per_share: float) -> tuple[float, bool]`
- max_loss_pct = max(0, (current_price - asset_floor_per_share) / current_price)
- passed = max_loss_pct < 0.50
- Returns (max_loss_pct, passed)

### `compute_owner_earnings_iv(owner_earnings_per_share: float, wacc: float, terminal_growth: float = 0.03) -> float`
- Gordon growth model: OE * (1 + g) / (wacc - g)
- Returns 0.0 if wacc <= terminal_growth (invalid)

## Layer 2: Track Cascade Runners

**New file: `engine/src/margin_engine/scoring/v3_cascade.py`**

### TrackAInputs (Pydantic model)
```
history: FinancialHistory
period: FinancialPeriod          # latest period
profile: AssetProfile
current_price: float
current_fcf_per_share: float
wacc: float
terminal_growth: float           # default 0.03
sustainable_growth_rate: float
buyback_yield: float | None
insider_ownership_pct: float | None
sbc_pct: float | None
recent_acquisition_count: int
regime_adjustments: RegimeAdjustments | None
```

### `run_track_a_cascade(inputs: TrackAInputs) -> V3TrackResult`
1. **Gate 1 — Moat Evidence**: `moat_durability_score(history)` → pass if raw_value >= 2
2. **Gate 2 — Reinvestment Engine**: `compute_compounding_power(history)` → pass if > 0.04
3. **Gate 3 — Capital Allocation**: `compute_capital_allocation_composite(...)` → pass if > 0.5
4. **Gate 4 — Valuation Reasonableness**: `reverse_dcf_growth_gap(...)` → pass if growth_gap > 0 (adjusted by regime: growth_gap > 0 + adjustment)
5. Count gates passed (total = 4)
6. Multiplicative score via `compute_track_a_score(moat, compounding, cap_alloc, growth_gap)`
7. Conviction via `assess_track_a_conviction(gates_passed, compounding_power, moat_durability, growth_gap)` — with regime adjustments forwarded
8. Return `V3TrackResult(track="compounder", qualifies=gates_passed>=3, ...)`

### TrackBInputs (Pydantic model)
```
history: FinancialHistory
period: FinancialPeriod
profile: AssetProfile
current_price: float
dcf_iv: float
owner_earnings_iv: float
asset_floor_iv: float
peer_comparison_iv: float
insider_percentile: float
institutional_percentile: float
sue_percentile: float
wacc: float
regime_adjustments: RegimeAdjustments | None
```

### `run_track_b_cascade(inputs: TrackBInputs) -> V3TrackResult`
1. **Gate 1 — Ensemble Valuation**: `compute_ensemble_valuation(4 IVs)` → pass if converged AND price < 0.60 * ensemble_IV
2. **Gate 2 — Downside Protection**: `compute_downside_protection(price, floor)` → pass if max_loss < 50%
3. **Gate 3 — Catalyst**: `compute_catalyst_strength(...)` → pass if > 60th percentile (regime-adjusted: override to 90 in EUPHORIA)
4. **Gate 4 — Quality Floor**: `compute_quality_floor_factor(roic, improving)` → pass if > 0
5. Count gates, compute multiplicative score, assess conviction
6. Return `V3TrackResult(track="mispricing", qualifies=gates_passed>=3, ...)`

## Layer 3: Universe Pipeline

**New file: `engine/src/margin_engine/scoring/v3_pipeline.py`**

### `TickerV3Data` (Pydantic model)
All data needed for one ticker's v3 scoring:
```
ticker: str
history: FinancialHistory
latest_period: FinancialPeriod
profile: AssetProfile
current_price: float
current_fcf_per_share: float
sustainable_growth_rate: float
buyback_yield: float | None
insider_ownership_pct: float | None
sbc_pct: float | None
recent_acquisition_count: int
insider_percentile: float
institutional_percentile: float
sue_percentile: float
momentum_percentile: float
dcf_iv: float
```

### `score_universe_v3(tickers_data: list[TickerV3Data], shiller_cape: float) -> list[V3Result]`
1. **Regime detection**: `detect_regime(shiller_cape)` → `regime_adjustments(regime)`
2. **Sector WACC**: Look up sector WACC for each ticker
3. **Peer comparison IV**: Compute sector median EV/EBIT from universe, then per-ticker peer IV
4. **Owner earnings IV**: `compute_owner_earnings_iv()` per ticker
5. **Asset floor IV**: `asset_floor_valuation()` per ticker
6. **For each ticker**: Build `TrackAInputs` + `TrackBInputs`, run both cascades
7. **Orchestrate**: `orchestrate_v3()` per ticker with timing signal
8. **Portfolio cap**: Sort qualifiers by conviction tier (EXCEPTIONAL > HIGH > WATCHLIST), then by score within tier. Keep top `MAX_POSITIONS` (10). Set remaining to NONE conviction / 0% position.
9. Return final list

## Layer 4: Data Prerequisites

### Sector WACC Lookup
**New file: `engine/src/margin_engine/scoring/quantitative/wacc_sector.py`**

Damodaran-style sector average WACCs, keyed by `GICSSector`:
- Technology: 10.0%
- Healthcare: 9.5%
- Financials: 8.5%
- Consumer Discretionary: 9.0%
- Consumer Staples: 7.5%
- Industrials: 8.5%
- Energy: 10.5%
- Utilities: 6.5%
- Real Estate: 7.0%
- Materials: 9.0%
- Communication Services: 9.0%

Function: `get_sector_wacc(sector: GICSSector) -> float`

### FRED Client for Shiller CAPE
**New file: `api/src/margin_api/data/fred_client.py`**

- Async httpx client fetching from FRED API
- Series ID: Shiller PE ratio
- Requires `FRED_API_KEY` environment variable
- 1-day TTL cache (in-memory)
- Fallback: return 25.0 (NORMAL regime) if API unavailable

### FinancialHistory Assembly
**Modify: `api/src/margin_api/services/scoring.py`**

New function: `build_financial_history(ticker: str, db_session) -> FinancialHistory`
- Query last 5 years of financial periods from `financial_data` table
- Sort chronologically (oldest first)
- Return `FinancialHistory(ticker=ticker, periods=periods)`

### Peer Comparison IV
**Helper in `v3_pipeline.py`**

`_compute_sector_peer_ivs(tickers_data: list[TickerV3Data]) -> dict[str, float]`
- Group tickers by sector
- Compute median EV/EBIT within each sector
- For each ticker: peer_iv = sector_median_ev_ebit * company_ebit / shares_outstanding

## Layer 5: API/CLI Integration

### DB Model
**New file: `api/src/margin_api/models/v3_score.py`**

```python
class V3ScoreRecord(Base):
    __tablename__ = "v3_scores"
    id: int (PK)
    ticker: str (indexed)
    scored_at: DateTime(timezone=True)
    opportunity_type: str
    conviction: str
    track_a: JSON  # V3TrackResult serialized
    track_b: JSON  # V3TrackResult serialized
    timing_signal: str
    max_position_pct: float
    regime: str
    composite_score: float
```

### Alembic Migration
- New `v3_scores` table

### CLI Command
`uv run python -m margin_api.cli score-v3 --tickers AAPL MSFT [--cape 30.5]`
- If `--cape` omitted, fetch from FRED API
- Runs full v3 pipeline on specified tickers
- Stores results in v3_scores table
- Prints summary table

### API Endpoints
- `GET /api/v3/scores` — List latest v3 scores, filterable by conviction level
- `GET /api/v3/scores/{ticker}` — Latest v3 score for a ticker

## Regime Integration

The cascade runners accept `RegimeAdjustments` as optional input. When provided:
- **Track A Gate 4**: growth_gap threshold becomes `0 + track_a_growth_gap_adjustment`
- **Track B Gate 3**: catalyst threshold becomes `60 + track_b_asymmetry_adjustment` (and override to 90 in EUPHORIA)
- **Track B conviction**: asymmetry thresholds adjusted by `track_b_asymmetry_adjustment`

The `assess_track_a_conviction` and `assess_track_b_conviction` functions in `v3_thresholds.py` will be extended with optional `growth_gap_adjustment` and `asymmetry_adjustment` parameters that offset their hardcoded thresholds.

## Key Design Decisions

1. **Sector WACC lookup** (not CAPM) — Deterministic, no external data dependency for beta
2. **FRED API for CAPE** — Most accurate regime detection, with graceful fallback to NORMAL
3. **5-year history** — Balances signal quality with data requirements
4. **Peer comparison IV computed at scoring time** — Natural batch operation, no extra DB tables
5. **Layered architecture** — Each layer independently testable with synthetic data
6. **Portfolio cap at pipeline level** — Not in orchestrator (which handles single tickers)
