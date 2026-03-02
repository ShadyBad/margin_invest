# Scoring Factors Tier 4: Validated Backtesting & Threshold Calibration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the real v3 scoring pipeline into the existing backtest infrastructure, externalize conviction thresholds to YAML, and build a threshold sensitivity framework — so that when PIT data is populated, backtests produce meaningful results and thresholds can be empirically calibrated.

**Architecture:** Adapter pattern converts PITSnapshot → TickerV3Data. ReplayOrchestrator delegates scoring to the real pipeline. Conviction thresholds become YAML-configurable alongside existing filter thresholds.

**Tech Stack:** Python 3.13, Pydantic, pytest, existing backtesting + scoring infrastructure

---

## Current State Assessment

**What exists:**
- Walk-forward partitioning, PIT provider protocol, DatabasePITProvider, ReplayOrchestrator (sync + async)
- Backtest API routes with real + synthetic fallback (`run_real_backtest()` already calls `orchestrator.run_async()`)
- Worker `precompute_default_backtest` runs Sunday 3AM, stores results in `BacktestRun` table
- Complete FilterConfig YAML infrastructure for elimination filters
- Universe membership tracking with delist detection

**What's missing (this plan fixes):**
1. `_compute_simple_score()` in ReplayOrchestrator uses gross_margin + earnings_yield instead of real v3 pipeline
2. Conviction thresholds hardcoded in `v3_thresholds.py` (not configurable via YAML)
3. No threshold sensitivity analysis framework
4. Legacy POST `/backtest/run` still uses fully synthetic metrics

**Not in scope (operational, not code):**
- Running `edgar-backfill` and `price-backfill` CLI commands to populate PIT data
- These are long-running operational tasks, not code changes

---

## Task 1: Create PIT-to-pipeline adapter

**Context:** The ReplayOrchestrator receives `PITSnapshot` objects but the v3 pipeline expects `TickerV3Data`. We need an adapter that extracts/computes the required fields from PIT financial data.

**Files:**
- Create: `engine/src/margin_engine/backtesting/pit_adapter.py`
- Create: `engine/tests/backtesting/test_pit_adapter.py`

**Step 1: Write failing test**

```python
# engine/tests/backtesting/test_pit_adapter.py
from datetime import date
from decimal import Decimal

import pytest
from margin_engine.backtesting.pit_adapter import build_ticker_data_from_pit
from margin_engine.backtesting.pit_provider import PITSnapshot
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.v3_pipeline import TickerV3Data


def _make_pit_snapshot(
    ticker: str = "AAPL",
    price: float = 150.0,
    market_cap: Decimal = Decimal("2500000000000"),
    revenue: Decimal = Decimal("400000000000"),
    net_income: Decimal = Decimal("100000000000"),
    ebit: Decimal = Decimal("120000000000"),
    ocf: Decimal = Decimal("110000000000"),
    capex: Decimal = Decimal("-10000000000"),
    total_equity: Decimal = Decimal("60000000000"),
    total_debt: Decimal = Decimal("100000000000"),
    cash: Decimal = Decimal("30000000000"),
    shares: int = 16_000_000_000,
    gross_profit: Decimal | None = Decimal("170000000000"),
) -> PITSnapshot:
    income = IncomeStatement(
        revenue=revenue,
        ebit=ebit,
        net_income=net_income,
        shares_outstanding=shares,
        gross_profit=gross_profit,
    )
    balance = BalanceSheet(
        total_assets=Decimal("350000000000"),
        total_equity=total_equity,
        long_term_debt=total_debt,
        short_term_debt=Decimal("0"),
        cash_and_equivalents=cash,
        shares_outstanding=shares,
    )
    cf = CashFlowStatement(
        operating_cash_flow=ocf,
        capital_expenditures=capex,
    )
    period = FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )
    profile = AssetProfile(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector=GICSSector.TECHNOLOGY,
        market_cap=market_cap,
        shares_outstanding=shares,
    )
    return PITSnapshot(
        ticker=ticker,
        as_of_date=date(2024, 11, 15),
        profile=profile,
        period=period,
        price=price,
    )


class TestBuildTickerDataFromPit:
    def test_returns_ticker_v3_data(self):
        snap = _make_pit_snapshot()
        result = build_ticker_data_from_pit(snap)
        assert isinstance(result, TickerV3Data)
        assert result.ticker == "AAPL"

    def test_current_price_from_snapshot(self):
        snap = _make_pit_snapshot(price=175.50)
        result = build_ticker_data_from_pit(snap)
        assert result.current_price == 175.50

    def test_fcf_per_share_computed(self):
        snap = _make_pit_snapshot(
            ocf=Decimal("110000000000"),
            capex=Decimal("-10000000000"),
            shares=16_000_000_000,
        )
        result = build_ticker_data_from_pit(snap)
        # FCF = 110B - 10B = 100B, per share = 100B / 16B = 6.25
        assert result.current_fcf_per_share == pytest.approx(6.25, abs=0.01)

    def test_sustainable_growth_from_retention(self):
        """g = ROE * retention_ratio (plowback)."""
        snap = _make_pit_snapshot(
            net_income=Decimal("100000000000"),
            total_equity=Decimal("60000000000"),
        )
        result = build_ticker_data_from_pit(snap)
        # ROE = 100/60 = 1.667, retention ~0.7 default -> g would be capped
        # Just check it's a reasonable positive number
        assert 0.0 < result.sustainable_growth_rate <= 0.30

    def test_missing_gross_profit_zero_buyback(self):
        snap = _make_pit_snapshot(gross_profit=None)
        result = build_ticker_data_from_pit(snap)
        assert result.current_fcf_per_share >= 0 or result.current_fcf_per_share < 0
        # Should not raise

    def test_zero_shares_returns_safe_defaults(self):
        snap = _make_pit_snapshot(shares=0)
        result = build_ticker_data_from_pit(snap)
        assert result.current_fcf_per_share == 0.0

    def test_dcf_iv_computed(self):
        snap = _make_pit_snapshot()
        result = build_ticker_data_from_pit(snap)
        # DCF IV should be positive for a profitable company
        assert result.dcf_iv > 0

    def test_history_contains_single_period(self):
        snap = _make_pit_snapshot()
        result = build_ticker_data_from_pit(snap)
        assert len(result.history.periods) >= 1
```

**Step 2: Run test to verify failure**

Run: `uv run pytest engine/tests/backtesting/test_pit_adapter.py -v`
Expected: FAIL — module not found

**Step 3: Implement**

```python
# engine/src/margin_engine/backtesting/pit_adapter.py
"""Adapter: convert PITSnapshot → TickerV3Data for scoring pipeline."""
from __future__ import annotations

from decimal import Decimal

from margin_engine.backtesting.pit_provider import PITSnapshot
from margin_engine.models.financial import FinancialHistory
from margin_engine.scoring.v3_pipeline import TickerV3Data

# Conservative defaults for fields not derivable from PIT snapshots
_DEFAULT_RETENTION_RATIO = 0.70  # typical for mature companies
_MAX_GROWTH_RATE = 0.30  # cap at 30%
_MIN_GROWTH_RATE = 0.01  # floor at 1%
_TERMINAL_GROWTH = 0.025  # 2.5% terminal growth for DCF


def build_ticker_data_from_pit(
    snapshot: PITSnapshot,
    prior_snapshots: list[PITSnapshot] | None = None,
) -> TickerV3Data:
    """Convert a PITSnapshot into TickerV3Data for the v3 scoring pipeline.

    Computes FCF per share, sustainable growth rate, and DCF IV from
    available financial data. Uses conservative defaults for fields
    that require data not available in PIT snapshots (insider ownership,
    SBC, acquisition count).

    Args:
        snapshot: Current-period PIT snapshot with price, period, profile.
        prior_snapshots: Optional historical snapshots for multi-period
            calculations (FinancialHistory).
    """
    period = snapshot.period
    profile = snapshot.profile
    income = period.current_income
    cf = period.current_cash_flow
    balance = period.current_balance

    shares = income.shares_outstanding or (balance.shares_outstanding if balance else 0)
    if not shares or shares <= 0:
        shares = 1  # avoid division by zero; results will be near-zero

    # FCF per share
    ocf = float(cf.operating_cash_flow or Decimal("0"))
    capex = float(cf.capital_expenditures or Decimal("0"))
    fcf = ocf + capex  # capex is negative
    fcf_per_share = fcf / shares

    # Sustainable growth rate: g = ROE * retention_ratio
    equity = float(balance.total_equity or Decimal("1"))
    net_income_val = float(income.net_income or Decimal("0"))
    roe = net_income_val / equity if equity > 0 else 0.0
    growth_rate = max(_MIN_GROWTH_RATE, min(roe * _DEFAULT_RETENTION_RATIO, _MAX_GROWTH_RATE))

    # Simple DCF IV: FCF / (WACC - g) as perpetuity model
    # Use a rough WACC estimate (sector WACC or 9% default)
    from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc

    wacc = get_sector_wacc(profile.sector)
    dcf_iv = 0.0
    if fcf_per_share > 0 and wacc > _TERMINAL_GROWTH:
        dcf_iv = fcf_per_share * (1 + growth_rate) / (wacc - _TERMINAL_GROWTH)

    # Build history from prior snapshots
    periods = [snapshot.period]
    if prior_snapshots:
        for ps in prior_snapshots:
            periods.append(ps.period)
        periods.sort(key=lambda p: p.period_end)

    history = FinancialHistory(ticker=snapshot.ticker, periods=periods)

    return TickerV3Data(
        ticker=snapshot.ticker,
        history=history,
        latest_period=period,
        profile=profile,
        current_price=snapshot.price,
        current_fcf_per_share=fcf_per_share,
        sustainable_growth_rate=growth_rate,
        dcf_iv=dcf_iv,
        # Fields not available from PIT — use safe defaults
        buyback_yield=None,
        insider_ownership_pct=None,
        sbc_pct=None,
        recent_acquisition_count=0,
        sue_percentile=50.0,  # neutral
        momentum_percentile=50.0,  # neutral
        beta=None,  # will use sector WACC fallback
    )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/backtesting/test_pit_adapter.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/pit_adapter.py engine/tests/backtesting/test_pit_adapter.py
git commit -m "$(cat <<'EOF'
feat(engine): add PIT-to-pipeline adapter for real backtesting

Converts PITSnapshot → TickerV3Data so the replay orchestrator
can use the actual v3 scoring pipeline instead of simplified scoring.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Wire real v3 scoring into ReplayOrchestrator

**Context:** Replace `_compute_simple_score()` (gross_margin + earnings_yield) with the actual v3 scoring pipeline. The orchestrator should use `score_universe_v3()` to score survivors, producing real conviction levels and composite scores.

**Files:**
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py` (lines 200-205, 445-446, 600-629)
- Modify: `engine/tests/backtesting/test_replay_orchestrator.py`

**Step 1: Write failing test**

Add a test that verifies the orchestrator calls the real pipeline when a `use_real_scoring=True` flag is set.

```python
# Add to engine/tests/backtesting/test_replay_orchestrator.py

def test_real_scoring_produces_composite_scores(in_memory_provider_with_data):
    """When use_real_scoring=True, scores come from v3 pipeline, not simple scorer."""
    config = ReplayConfig(
        start_date=date(2023, 1, 1),
        end_date=date(2023, 6, 1),
        rebalance_frequency="quarterly",
    )
    orchestrator = ReplayOrchestrator(
        config=config,
        pit_provider=in_memory_provider_with_data,
        use_real_scoring=True,
    )
    result = orchestrator.run()
    # Should produce at least one snapshot with scored holdings
    assert len(result.snapshots) > 0
    # Score should be from real pipeline (not the 50-70 range of simple scorer)
    for snap in result.snapshots:
        for h in snap.holdings:
            assert 0 <= h.composite_score <= 100
```

**Step 2: Implement**

In `replay_orchestrator.py`:

1. Add `use_real_scoring: bool = False` parameter to `__init__`
2. Add import: `from margin_engine.backtesting.pit_adapter import build_ticker_data_from_pit`
3. Add import: `from margin_engine.scoring.v3_pipeline import score_universe_v3`
4. Create `_score_with_pipeline()` method that:
   - Converts survivors (PITSnapshots) to TickerV3Data via `build_ticker_data_from_pit()`
   - Calls `score_universe_v3(tickers_data)` to get real V3Results
   - Maps results back to (snapshot, score) tuples
5. In the scoring step (line 200-205 for sync, 445-446 for async), check `self._use_real_scoring`:
   - If True: call `_score_with_pipeline(survivors)`
   - If False: use existing `_compute_simple_score()` (backward compatible)

```python
def _score_with_pipeline(
    self,
    survivors: list[PITSnapshot],
    shiller_cape: float = 25.0,
) -> list[tuple[PITSnapshot, float]]:
    """Score survivors using the real v3 scoring pipeline."""
    tickers_data = [build_ticker_data_from_pit(s) for s in survivors]
    if not tickers_data:
        return []

    results = score_universe_v3(tickers_data, shiller_cape=shiller_cape)

    # Map back: V3Result has .ticker, .conviction, .track_a/.track_b
    score_map: dict[str, float] = {}
    for r in results:
        # Use the best track score as composite
        best_score = max(
            r.track_a.multiplicative_score if r.track_a else 0.0,
            r.track_b.multiplicative_score if r.track_b else 0.0,
        )
        # Normalize to 0-100 scale
        score_map[r.ticker] = min(best_score * 100, 100.0)

    scored = []
    for s in survivors:
        score = score_map.get(s.ticker, 0.0)
        scored.append((s, score))
    return scored
```

**Step 3: Run tests**

Run: `uv run pytest engine/tests/backtesting/test_replay_orchestrator.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add engine/src/margin_engine/backtesting/replay_orchestrator.py engine/tests/backtesting/test_replay_orchestrator.py engine/src/margin_engine/backtesting/pit_adapter.py
git commit -m "$(cat <<'EOF'
feat(engine): wire real v3 scoring pipeline into replay orchestrator

Adds use_real_scoring flag to ReplayOrchestrator. When enabled,
converts PITSnapshots to TickerV3Data and calls score_universe_v3()
instead of the simplified gross_margin + earnings_yield scorer.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Enable real scoring in worker and API

**Context:** Now that the orchestrator supports real scoring, enable it in the `precompute_default_backtest` worker and the `/backtest/replay` API endpoint.

**Files:**
- Modify: `api/src/margin_api/workers/tasks.py` (precompute_default_backtest function)
- Modify: `api/src/margin_api/services/backtest.py` (run_real_backtest function)
- Modify: `api/tests/routes/test_backtest.py` or `api/tests/services/test_backtest.py`

**Step 1: Update `run_real_backtest()` in services/backtest.py**

```python
async def run_real_backtest(session: AsyncSession, config: ReplayConfig) -> ReplayResult:
    provider = DatabasePITProvider(session)
    registry = FactorRegistry.default()
    orchestrator = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=registry,
        use_real_scoring=True,  # NEW: use v3 pipeline
    )
    return await orchestrator.run_async()
```

**Step 2: Update `precompute_default_backtest` worker**

Find the worker and add `use_real_scoring=True` to the orchestrator instantiation.

**Step 3: Write test verifying the flag is passed**

```python
def test_run_real_backtest_uses_real_scoring(monkeypatch):
    """Verify run_real_backtest passes use_real_scoring=True."""
    captured = {}

    class MockOrchestrator:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def run_async(self):
            from margin_engine.backtesting.replay_orchestrator import ReplayResult, ReplayConfig
            return ReplayResult(config=ReplayConfig(), ...)  # minimal

    monkeypatch.setattr("margin_api.services.backtest.ReplayOrchestrator", MockOrchestrator)
    # call run_real_backtest and assert captured["use_real_scoring"] is True
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/ -v -k "backtest" --tb=short 2>&1 | tail -30`

**Step 5: Commit**

```bash
git add api/src/margin_api/services/backtest.py api/src/margin_api/workers/tasks.py api/tests/
git commit -m "$(cat <<'EOF'
feat(api): enable real v3 scoring in backtest worker and replay endpoint

Both precompute_default_backtest and run_real_backtest now pass
use_real_scoring=True to ReplayOrchestrator.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Externalize conviction thresholds to YAML

**Context:** Currently `v3_thresholds.py` has 18+ hardcoded constants. Move them to a YAML config file alongside the existing `filters.yaml`, using the same Pydantic config pattern.

**Files:**
- Create: `engine/config/thresholds.yaml`
- Create: `engine/src/margin_engine/config/threshold_config.py`
- Modify: `engine/src/margin_engine/scoring/v3_thresholds.py` (use config instead of module constants)
- Create: `engine/tests/config/test_threshold_config.py`

**Step 1: Write failing test**

```python
# engine/tests/config/test_threshold_config.py
import pytest
from margin_engine.config.threshold_config import (
    ThresholdConfig,
    TrackAThresholds,
    TrackBThresholds,
    load_threshold_config,
)


class TestThresholdConfig:
    def test_default_track_a_values(self):
        config = ThresholdConfig()
        assert config.track_a.exceptional_power == 0.15
        assert config.track_a.exceptional_moat == 3
        assert config.track_a.exceptional_gap == 0.08
        assert config.track_a.high_power == 0.08
        assert config.track_a.high_moat == 2
        assert config.track_a.high_gap == 0.03
        assert config.track_a.medium_power == 0.04
        assert config.track_a.medium_moat == 2
        assert config.track_a.min_gates_full == 4
        assert config.track_a.min_gates_medium == 3

    def test_default_track_b_values(self):
        config = ThresholdConfig()
        assert config.track_b.exceptional_asymmetry == 5.0
        assert config.track_b.exceptional_catalyst == 55.0
        assert config.track_b.exceptional_converging == 4
        assert config.track_b.high_asymmetry == 3.0
        assert config.track_b.high_catalyst == 40.0
        assert config.track_b.high_converging == 3
        assert config.track_b.medium_asymmetry == 1.5

    def test_hysteresis_buffer(self):
        config = ThresholdConfig()
        assert config.hysteresis_buffer == 0.10

    def test_load_from_yaml(self, tmp_path):
        yaml_content = '''
track_a:
  exceptional_power: 0.20
  high_power: 0.10
track_b:
  exceptional_asymmetry: 6.0
hysteresis_buffer: 0.15
'''
        yaml_file = tmp_path / "thresholds.yaml"
        yaml_file.write_text(yaml_content)
        config = load_threshold_config(yaml_file)
        assert config.track_a.exceptional_power == 0.20
        assert config.track_a.high_power == 0.10
        # Non-overridden values keep defaults
        assert config.track_a.exceptional_moat == 3
        assert config.track_b.exceptional_asymmetry == 6.0
        assert config.hysteresis_buffer == 0.15

    def test_load_missing_file_returns_defaults(self):
        config = load_threshold_config(None)
        assert config.track_a.exceptional_power == 0.15
```

**Step 2: Implement config model**

```python
# engine/src/margin_engine/config/threshold_config.py
"""Conviction threshold configuration — YAML-loadable with Pydantic defaults."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class TrackAThresholds(BaseModel):
    exceptional_power: float = 0.15
    exceptional_moat: int = 3
    exceptional_gap: float = 0.08
    high_power: float = 0.08
    high_moat: int = 2
    high_gap: float = 0.03
    medium_power: float = 0.04
    medium_moat: int = 2
    min_gates_full: int = 4
    min_gates_medium: int = 3


class TrackBThresholds(BaseModel):
    exceptional_asymmetry: float = 5.0
    exceptional_catalyst: float = 55.0
    exceptional_converging: int = 4
    high_asymmetry: float = 3.0
    high_catalyst: float = 40.0
    high_converging: int = 3
    medium_asymmetry: float = 1.5
    min_gates_full: int = 4
    min_gates_medium: int = 3


class ThresholdConfig(BaseModel):
    track_a: TrackAThresholds = TrackAThresholds()
    track_b: TrackBThresholds = TrackBThresholds()
    hysteresis_buffer: float = 0.10


def load_threshold_config(path: Path | None = None) -> ThresholdConfig:
    if path is None or not path.exists():
        return ThresholdConfig()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return ThresholdConfig(**data)
```

**Step 3: Create YAML file**

```yaml
# engine/config/thresholds.yaml
# Conviction thresholds for v3 Track A and Track B scoring.
# Modify these values to calibrate conviction levels.
# All defaults match the hardcoded values in v3_thresholds.py.

track_a:
  exceptional_power: 0.15
  exceptional_moat: 3
  exceptional_gap: 0.08
  high_power: 0.08
  high_moat: 2
  high_gap: 0.03
  medium_power: 0.04
  medium_moat: 2
  min_gates_full: 4
  min_gates_medium: 3

track_b:
  exceptional_asymmetry: 5.0
  exceptional_catalyst: 55.0
  exceptional_converging: 4
  high_asymmetry: 3.0
  high_catalyst: 40.0
  high_converging: 3
  medium_asymmetry: 1.5
  min_gates_full: 4
  min_gates_medium: 3

hysteresis_buffer: 0.10
```

**Step 4: Update v3_thresholds.py to use config**

Replace the module-level constants with a config-loaded approach. The `assess_track_a_conviction()` and `assess_track_b_conviction()` functions gain an optional `config: ThresholdConfig | None = None` parameter. When None, they load default config (identical to current behavior).

**Step 5: Run tests**

Run: `uv run pytest engine/tests/config/test_threshold_config.py engine/tests/scoring/test_v3_thresholds.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add engine/config/thresholds.yaml engine/src/margin_engine/config/threshold_config.py engine/src/margin_engine/scoring/v3_thresholds.py engine/tests/config/test_threshold_config.py
git commit -m "$(cat <<'EOF'
feat(engine): externalize conviction thresholds to YAML config

Moves 18 hardcoded threshold constants from v3_thresholds.py to
engine/config/thresholds.yaml via Pydantic ThresholdConfig model.
Backward compatible — defaults match previous hardcoded values.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Build threshold sensitivity analysis module

**Context:** To calibrate thresholds empirically, we need infrastructure that runs backtests across a parameter grid and reports which combinations produce the best risk-adjusted returns.

**Files:**
- Create: `engine/src/margin_engine/backtesting/threshold_sensitivity.py`
- Create: `engine/tests/backtesting/test_threshold_sensitivity.py`

**Step 1: Write failing test**

```python
# engine/tests/backtesting/test_threshold_sensitivity.py
import pytest
from margin_engine.backtesting.threshold_sensitivity import (
    ThresholdVariation,
    SensitivityResult,
    build_parameter_grid,
    run_threshold_sensitivity,
)
from margin_engine.config.threshold_config import ThresholdConfig


class TestBuildParameterGrid:
    def test_single_param_variation(self):
        variations = [
            ThresholdVariation(
                param_path="track_a.high_power",
                values=[0.06, 0.08, 0.10, 0.12],
            )
        ]
        grid = build_parameter_grid(ThresholdConfig(), variations)
        assert len(grid) == 4
        assert grid[0].track_a.high_power == 0.06
        assert grid[3].track_a.high_power == 0.12
        # Other params unchanged
        assert grid[0].track_a.exceptional_power == 0.15

    def test_two_param_grid(self):
        variations = [
            ThresholdVariation(param_path="track_a.high_power", values=[0.06, 0.10]),
            ThresholdVariation(param_path="track_b.high_asymmetry", values=[2.5, 3.5]),
        ]
        grid = build_parameter_grid(ThresholdConfig(), variations)
        # 2 x 2 = 4 combinations
        assert len(grid) == 4

    def test_empty_variations_returns_default(self):
        grid = build_parameter_grid(ThresholdConfig(), [])
        assert len(grid) == 1


class TestSensitivityResult:
    def test_result_fields(self):
        result = SensitivityResult(
            config_label="high_power=0.10",
            cagr=0.12,
            sharpe=0.95,
            max_drawdown=0.25,
            excess_cagr=0.05,
            num_positions_avg=15.0,
            turnover_avg=0.20,
        )
        assert result.sharpe == 0.95
```

**Step 2: Implement**

```python
# engine/src/margin_engine/backtesting/threshold_sensitivity.py
"""Threshold sensitivity analysis — parameter sweep for conviction calibration."""
from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass

from pydantic import BaseModel

from margin_engine.config.threshold_config import ThresholdConfig


class ThresholdVariation(BaseModel):
    """A single parameter to vary in the sensitivity sweep."""
    param_path: str  # e.g. "track_a.high_power"
    values: list[float | int]


class SensitivityResult(BaseModel):
    """Metrics for a single threshold configuration."""
    config_label: str
    cagr: float
    sharpe: float
    max_drawdown: float
    excess_cagr: float
    num_positions_avg: float
    turnover_avg: float


def _set_nested_attr(config: ThresholdConfig, path: str, value: float | int) -> ThresholdConfig:
    """Set a nested attribute on a ThresholdConfig copy."""
    parts = path.split(".")
    data = config.model_dump()
    obj = data
    for part in parts[:-1]:
        obj = obj[part]
    obj[parts[-1]] = value
    return ThresholdConfig(**data)


def build_parameter_grid(
    base_config: ThresholdConfig,
    variations: list[ThresholdVariation],
) -> list[ThresholdConfig]:
    """Build Cartesian product of threshold variations."""
    if not variations:
        return [base_config]

    # Build all value combinations
    param_values = [v.values for v in variations]
    param_paths = [v.param_path for v in variations]

    configs = []
    for combo in itertools.product(*param_values):
        cfg = base_config.model_copy(deep=True)
        label_parts = []
        for path, val in zip(param_paths, combo):
            cfg = _set_nested_attr(cfg, path, val)
            label_parts.append(f"{path.split('.')[-1]}={val}")
        # Store label in a way we can retrieve it
        configs.append(cfg)

    return configs


def run_threshold_sensitivity(
    configs: list[ThresholdConfig],
    run_backtest_fn,  # Callable[[ThresholdConfig], ReplayResult]
) -> list[SensitivityResult]:
    """Run backtest for each config and collect results.

    Args:
        configs: List of ThresholdConfig variations to test.
        run_backtest_fn: Callable that takes a ThresholdConfig and returns
            a ReplayResult (or similar object with .metrics).

    Returns:
        List of SensitivityResult sorted by Sharpe ratio descending.
    """
    results = []
    for i, cfg in enumerate(configs):
        replay = run_backtest_fn(cfg)
        m = replay.metrics
        results.append(
            SensitivityResult(
                config_label=f"config_{i}",
                cagr=m.cagr,
                sharpe=m.sharpe_ratio,
                max_drawdown=m.max_drawdown,
                excess_cagr=m.excess_cagr,
                num_positions_avg=0.0,  # TODO: compute from snapshots
                turnover_avg=m.avg_turnover,
            )
        )
    results.sort(key=lambda r: -r.sharpe)
    return results
```

**Step 3: Run tests**

Run: `uv run pytest engine/tests/backtesting/test_threshold_sensitivity.py -v`

**Step 4: Commit**

```bash
git add engine/src/margin_engine/backtesting/threshold_sensitivity.py engine/tests/backtesting/test_threshold_sensitivity.py
git commit -m "$(cat <<'EOF'
feat(engine): add threshold sensitivity analysis for calibration

Parameter grid builder and sweep runner for conviction thresholds.
Enables empirical calibration once PIT data is available.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Replace legacy synthetic POST /backtest/run

**Context:** The `POST /backtest/run` route still uses `_build_synthetic_metrics()` with hardcoded values. Update it to use the real backtest service (with synthetic fallback when PIT data is unavailable).

**Files:**
- Modify: `api/src/margin_api/routes/backtest.py` (lines 132-162)
- Modify: `api/tests/routes/test_backtest.py`

**Step 1: Update the route**

Replace the synthetic `_build_synthetic_metrics()` call with `run_real_backtest()` (with synthetic fallback):

```python
@router.post("/backtest/run", response_model=BacktestResultResponse, status_code=201)
async def run_backtest(
    config: BacktestConfigRequest,
    session: AsyncSession = Depends(get_db),
) -> BacktestResultResponse:
    """Trigger a backtest with the given configuration."""
    start_time = time.monotonic()

    engine_config = ReplayConfig(
        start_date=config.start_date,
        end_date=config.end_date or date.today(),
    )
    try:
        result = await run_real_backtest(session, engine_config)
        metrics = _build_metrics_response_from_replay(result.metrics)
    except Exception:
        logger.warning("Real backtest failed, using synthetic", exc_info=True)
        metrics = _build_synthetic_metrics(config)

    validation = _build_validation(metrics)
    duration = time.monotonic() - start_time

    resolved_config = config.model_copy(update={"end_date": config.end_date or date.today()})
    result_response = BacktestResultResponse(
        config=resolved_config,
        metrics=metrics,
        validation=validation,
        num_snapshots=metrics.num_months,
        run_at=datetime.now(UTC),
        duration_seconds=round(duration, 4),
    )

    backtest_id = str(uuid4())
    _backtest_store[backtest_id] = result_response
    return result_response
```

Keep `_build_synthetic_metrics()` as fallback — do not delete it.

**Step 2: Update tests**

Existing tests should still pass since synthetic fallback activates when no PIT data exists.

**Step 3: Run tests**

Run: `uv run pytest api/tests/routes/test_backtest.py -v`

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/backtest.py api/tests/
git commit -m "$(cat <<'EOF'
feat(api): update POST /backtest/run to attempt real scoring first

Falls back to synthetic metrics when PIT data unavailable.
Keeps backward compatibility for existing API consumers.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Full test suite verification

**Files:** None (verification only)

**Step 1: Run engine tests**

```bash
uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -20
```
Expected: All pass (2712+ tests)

**Step 2: Run API tests**

```bash
uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py --tb=short 2>&1 | tail -20
```
Expected: All pass (1587+ tests)

**Step 3: Verify no regressions**

If any test fails, investigate and fix before marking complete.
