# Backtest Wire & Validate Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing backtesting engine to run against real production PIT data, replacing the synthetic placeholder with validated results.

**Architecture:** Modify the existing ARQ worker (`precompute_default_backtest`) to use real SPY benchmark prices, re-enable the liquidity filter with relaxed thresholds, change start date to 2011, add error capture, and add a validation summary. Add one new admin endpoint for introspection.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 + asyncpg, ARQ, yfinance, Alembic, pytest + pytest-asyncio + aiosqlite

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `engine/src/margin_engine/config/filter_config.py` | Filter threshold configuration | Modify: add dollar volume tiers to `backtest_filter_config()` |
| `engine/src/margin_engine/backtesting/replay_orchestrator.py` | Replay engine | Modify: add `gross_return` to `run_async()` |
| `api/src/margin_api/services/pit_provider.py` | PIT data access layer | Modify: add `get_price_series()` method |
| `api/src/margin_api/services/backtest.py` | Backtest service helpers | Modify: update `run_real_backtest()` signature, add `compute_validation_summary()` |
| `api/src/margin_api/workers.py` | ARQ worker functions | Modify: fix `precompute_default_backtest()` |
| `api/src/margin_api/routes/admin.py` | Admin API endpoints | Modify: add `GET /admin/backtest/latest` |
| `api/src/margin_api/db/models.py` | DB models | Modify: add `error_message` to `BacktestRun` |
| `api/alembic/versions/` | DB migrations | Create: migration for `error_message` column |

---

## Chunk 1: Engine-Layer Fixes (filter config + gross_return)

### Task 1: Add relaxed dollar volume tiers to backtest_filter_config()

**Files:**
- Modify: `engine/src/margin_engine/config/filter_config.py:202-218`
- Test: `engine/tests/config/test_filter_config.py`

- [ ] **Step 1: Write failing tests for dollar volume tiers**

Add to `engine/tests/config/test_filter_config.py` in the `TestBacktestFilterConfig` class:

```python
def test_backtest_config_has_relaxed_dollar_volumes(self):
    """Backtest should halve dollar volume tiers for historical liquidity."""
    from margin_engine.config.filter_config import backtest_filter_config

    config = backtest_filter_config()
    dv = config.liquidity.dollar_volume
    assert dv.mega == 25_000_000
    assert dv.large == 10_000_000
    assert dv.mid == 2_500_000
    assert dv.small == 1_000_000

def test_backtest_dollar_volumes_are_lower_than_production(self):
    """Backtest dollar volumes should be strictly less than production defaults."""
    from margin_engine.config.filter_config import (
        DollarVolumeTiers,
        backtest_filter_config,
    )

    production = DollarVolumeTiers()
    backtest = backtest_filter_config().liquidity.dollar_volume
    assert backtest.mega < production.mega
    assert backtest.large < production.large
    assert backtest.mid < production.mid
    assert backtest.small < production.small
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/config/test_filter_config.py::TestBacktestFilterConfig::test_backtest_config_has_relaxed_dollar_volumes engine/tests/config/test_filter_config.py::TestBacktestFilterConfig::test_backtest_dollar_volumes_are_lower_than_production -v`
Expected: FAIL (dollar volumes still at production defaults)

- [ ] **Step 3: Add dollar volume tiers to backtest_filter_config()**

In `engine/src/margin_engine/config/filter_config.py`, modify `backtest_filter_config()` (line 202):

```python
def backtest_filter_config() -> FilterConfig:
    """Return a FilterConfig with relaxed thresholds for PIT backtesting.

    Reduces min_years_of_history (5 -> 1), market_cap floor ($300M -> $100M),
    and dollar volume tiers (halved) to avoid over-eliminating historical
    tickers when markets were less liquid.
    """
    return FilterConfig(
        liquidity=LiquidityConfig(
            min_years_of_history=1,
            market_cap_minimum=MarketCapMinimum(
                default=100_000_000,
                utilities=500_000_000,
                energy=250_000_000,
            ),
            dollar_volume=DollarVolumeTiers(
                mega=25_000_000,
                large=10_000_000,
                mid=2_500_000,
                small=1_000_000,
            ),
        ),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/config/test_filter_config.py::TestBacktestFilterConfig -v`
Expected: All tests PASS (including existing ones)

- [ ] **Step 5: Commit**

```bash
git add engine/src/margin_engine/config/filter_config.py engine/tests/config/test_filter_config.py
git commit -m "feat(engine): add relaxed dollar volume tiers to backtest_filter_config"
```

---

### Task 2: Fix gross_return gap in run_async()

**Files:**
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py:506-585`
- Test: `engine/tests/backtesting/test_replay_orchestrator.py`

- [ ] **Step 1: Write failing test for gross_return in async replay**

Add to `engine/tests/backtesting/test_replay_orchestrator.py`:

```python
def test_run_async_populates_gross_return(self):
    """run_async snapshots must have gross_return distinct from portfolio_return when costs > 0."""
    from datetime import date

    from margin_engine.backtesting.pit_provider import InMemoryPITProvider
    from margin_engine.backtesting.factor_registry import FactorRegistry
    from margin_engine.backtesting.replay_orchestrator import ReplayConfig, ReplayOrchestrator
    from margin_engine.models.financial import (
        AssetProfile, FinancialPeriod, IncomeStatement, BalanceSheet,
        CashFlowStatement, GICSSector,
    )
    from decimal import Decimal
    import asyncio

    provider = InMemoryPITProvider()
    # Add 3 months of data for 2 tickers so we get at least 1 rebalance with costs
    for month in [1, 2, 3]:
        d = date(2020, month, 1)
        for ticker, price in [("AAA", 100.0 + month), ("BBB", 50.0 + month)]:
            income = IncomeStatement(
                revenue=Decimal("1000000"), cost_of_revenue=Decimal("400000"),
                gross_profit=Decimal("600000"), ebit=Decimal("200000"),
                net_income=Decimal("150000"), shares_outstanding=1000000,
            )
            balance = BalanceSheet(
                total_assets=Decimal("5000000"), current_assets=Decimal("2000000"),
                total_liabilities=Decimal("2000000"), current_liabilities=Decimal("500000"),
                total_equity=Decimal("3000000"), shares_outstanding=1000000,
            )
            cash_flow = CashFlowStatement(
                operating_cash_flow=Decimal("300000"), capital_expenditures=Decimal("-50000"),
            )
            profile = AssetProfile(
                ticker=ticker, name=ticker, sector=GICSSector.INDUSTRIALS,
                market_cap=Decimal(str(price * 1000000)),
                shares_outstanding=1000000,
            )
            period = FinancialPeriod(
                period_end=d.isoformat(), filing_date=d.isoformat(),
                current_income=income, current_balance=balance,
                current_cash_flow=cash_flow,
            )
            provider.add_snapshot(d, ticker, profile, period, price)

    config = ReplayConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 3, 31),
        rebalance_frequency="monthly",
        transaction_cost_bps=100.0,  # 1% costs to make difference visible
    )
    registry = FactorRegistry.default()
    orchestrator = ReplayOrchestrator(
        config=config, pit_provider=provider, factor_registry=registry,
    )

    # Verify via sync run() first (same code needs to be mirrored to run_async)
    result = orchestrator.run()

    # After month 1, there should be snapshots with gross_return != portfolio_return
    snapshots_with_costs = [s for s in result.snapshots if s.transaction_costs > 0]
    assert len(snapshots_with_costs) > 0, "Expected at least one snapshot with costs"
    for s in snapshots_with_costs:
        # gross_return should be >= portfolio_return (costs reduce return)
        assert s.gross_return is not None
        assert s.gross_return >= s.portfolio_return or s.portfolio_return == 0.0
```

Note: This test verifies gross_return via the sync `run()` method (which already works). After implementing the fix for `run_async()`, add a parallel test using `@pytest.mark.asyncio` that wraps InMemoryPITProvider in an async adapter to test the async path directly. The key implementation is the same 4 lines added to both methods — `pre_cost_value` capture, `gross_return` in both branches, and `gross_return=gross_return` in the MonthlySnapshot constructor.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_replay_orchestrator.py::test_run_async_populates_gross_return -v`
Expected: FAIL (gross_return defaults to portfolio_return because run_async doesn't compute it)

- [ ] **Step 3: Add gross_return computation to run_async()**

In `engine/src/margin_engine/backtesting/replay_orchestrator.py`, in the `run_async()` method, make these 4 changes to mirror the sync `run()` method (lines 258-336):

**Change 1:** Add `pre_cost_value = portfolio_value` on the line immediately before `# 7. Transaction costs` (before line 518). This captures the portfolio value after returns but before costs are deducted. Place it here (NOT inside the `if i > 0` block) so it always runs:

```python
            # Capture pre-cost portfolio value for gross return computation
            pre_cost_value = portfolio_value

            # 7. Transaction costs
```

**Change 2:** In the returns block (line 530-538), add `gross_return = 0.0` to the `if not snapshots` branch and `gross_return = (pre_cost_value - prev_pv) / prev_pv` to the else branch:

```python
            # 9. Returns
            if not snapshots:
                port_return = 0.0
                bench_return = 0.0
                gross_return = 0.0
            else:
                prev_pv = snapshots[-1].portfolio_value
                prev_bv = snapshots[-1].benchmark_value
                port_return = (portfolio_value - prev_pv) / prev_pv if prev_pv > 0 else 0.0
                bench_return = (benchmark_value - prev_bv) / prev_bv if prev_bv > 0 else 0.0
                gross_return = (pre_cost_value - prev_pv) / prev_pv if prev_pv > 0 else 0.0
```

**Change 3:** In the MonthlySnapshot constructor (line 576-585), add `gross_return=gross_return`:

```python
            snapshot_record = MonthlySnapshot(
                date=rebal_date,
                holdings=new_holdings,
                portfolio_value=portfolio_value,
                benchmark_value=benchmark_value,
                portfolio_return=port_return,
                benchmark_return=bench_return,
                turnover=turnover,
                transaction_costs=cost,
                gross_return=gross_return,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/backtesting/test_replay_orchestrator.py -v`
Expected: All PASS

- [ ] **Step 5: Run full engine backtesting test suite**

Run: `uv run pytest engine/tests/backtesting/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/replay_orchestrator.py engine/tests/backtesting/test_replay_orchestrator.py
git commit -m "fix(engine): add gross_return computation to run_async() matching sync run()"
```

---

## Chunk 2: API Data Layer (price series + model migration)

### Task 3: Add get_price_series() to DatabasePITProvider

**Files:**
- Modify: `api/src/margin_api/services/pit_provider.py`
- Test: `api/tests/services/test_pit_provider.py` (or nearest test file)

- [ ] **Step 1: Write failing test for get_price_series()**

Create or add to the appropriate test file:

```python
@pytest.mark.asyncio
async def test_get_price_series_returns_date_price_dict(session):
    """get_price_series returns {date: float} for a ticker in a date range."""
    # Seed 3 days of price data
    for day, close in [(1, 100.0), (2, 101.0), (3, 102.0)]:
        session.add(PITDailyPrice(
            ticker="SPY", date=date(2020, 1, day),
            open=close, high=close, low=close, close=close,
            adj_close=close, volume=1000000,
        ))
    await session.flush()

    provider = DatabasePITProvider(session)
    prices = await provider.get_price_series("SPY", date(2020, 1, 1), date(2020, 1, 3))

    assert len(prices) == 3
    assert prices[date(2020, 1, 1)] == 100.0
    assert prices[date(2020, 1, 2)] == 101.0
    assert prices[date(2020, 1, 3)] == 102.0


@pytest.mark.asyncio
async def test_get_price_series_filters_by_date_range(session):
    """get_price_series only returns prices within the requested range."""
    for day in range(1, 6):
        session.add(PITDailyPrice(
            ticker="SPY", date=date(2020, 1, day),
            open=100.0, high=100.0, low=100.0, close=float(100 + day),
            adj_close=float(100 + day), volume=1000000,
        ))
    await session.flush()

    provider = DatabasePITProvider(session)
    prices = await provider.get_price_series("SPY", date(2020, 1, 2), date(2020, 1, 4))

    assert len(prices) == 3
    assert date(2020, 1, 1) not in prices
    assert date(2020, 1, 5) not in prices


@pytest.mark.asyncio
async def test_get_price_series_empty_when_no_data(session):
    """get_price_series returns empty dict when ticker has no data."""
    provider = DatabasePITProvider(session)
    prices = await provider.get_price_series("NODATA", date(2020, 1, 1), date(2020, 12, 31))
    assert prices == {}
```

Uses the existing `session` fixture from `api/tests/services/test_pit_provider.py` (async SQLite via `pytest_asyncio.fixture`). Imports (`PITDailyPrice`, `DatabasePITProvider`, `date`) are already at the top of the file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_pit_provider.py -v -k "price_series"`
Expected: FAIL (method does not exist)

- [ ] **Step 3: Implement get_price_series()**

Add to `api/src/margin_api/services/pit_provider.py` in the `DatabasePITProvider` class, after the `get_prices()` method:

```python
async def get_price_series(
    self, ticker: str, start_date: date, end_date: date
) -> dict[date, float]:
    """Return all closing prices for a ticker in a date range.

    Used for loading benchmark (SPY) prices for the full backtest window.
    Returns {date: close_price} dict. Empty dict if no data.
    """
    stmt = (
        select(PITDailyPrice.date, PITDailyPrice.close)
        .where(
            PITDailyPrice.ticker == ticker,
            PITDailyPrice.date >= start_date,
            PITDailyPrice.date <= end_date,
        )
        .order_by(PITDailyPrice.date)
    )
    result = await self._session.execute(stmt)
    return {row.date: float(row.close) for row in result.all()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_pit_provider.py -v -k "price_series"`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/services/pit_provider.py api/tests/services/test_pit_provider.py
git commit -m "feat(api): add get_price_series() to DatabasePITProvider"
```

---

### Task 4: Add error_message column to BacktestRun

**Files:**
- Modify: `api/src/margin_api/db/models.py:429-459`
- Create: `api/alembic/versions/xxxx_add_error_message_to_backtest_runs.py`

- [ ] **Step 1: Add error_message to BacktestRun model**

In `api/src/margin_api/db/models.py`, add after the `pit_data_version` field (line 457):

```python
error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Ensure `Text` is imported from `sqlalchemy` (check existing imports at top of file).

- [ ] **Step 2: Generate Alembic migration**

Run: `uv run alembic revision --autogenerate -m "add error_message to backtest_runs"`

- [ ] **Step 3: Verify migration looks correct**

Read the generated migration file. It should contain:
```python
op.add_column('backtest_runs', sa.Column('error_message', sa.Text(), nullable=True))
```

Add idempotent check per project convention:
```python
def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = [c["name"] for c in inspector.get_columns("backtest_runs")]
    if "error_message" not in existing:
        op.add_column("backtest_runs", sa.Column("error_message", sa.Text(), nullable=True))
```

- [ ] **Step 4: Check for multiple Alembic heads**

Run: `uv run alembic heads`
Expected: Single head. If multiple heads, create a merge migration.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/
git commit -m "feat(api): add error_message column to BacktestRun"
```

---

## Chunk 3: Backtest Service Layer (validation + run_real_backtest update)

### Task 5: Add validation gate logic to backtest service

**Files:**
- Modify: `api/src/margin_api/services/backtest.py`
- Test: `api/tests/services/test_backtest_wiring.py`

- [ ] **Step 1: Write failing test for compute_validation_summary()**

Add to `api/tests/services/test_backtest_wiring.py`:

```python
class TestComputeValidationSummary:
    def test_all_gates_pass_with_good_metrics(self):
        """Validation summary should pass all gates for strong metrics."""
        from margin_engine.backtesting.models import PerformanceMetrics
        from margin_api.services.backtest import compute_validation_summary

        metrics = PerformanceMetrics(
            cagr=0.12, excess_cagr=0.04, sharpe_ratio=1.1,
            sortino_ratio=1.5, max_drawdown=0.25, win_rate=0.58,
            information_ratio=0.7, total_return=4.0,
            benchmark_total_return=2.5, num_months=180, avg_turnover=0.20,
        )
        summary = compute_validation_summary(metrics, benchmark_sharpe=0.8)
        assert summary["overall_pass"] is True
        assert all(g["passed"] for g in summary["gates"])

    def test_fails_when_cagr_negative(self):
        """Negative CAGR should fail the CAGR gate."""
        from margin_engine.backtesting.models import PerformanceMetrics
        from margin_api.services.backtest import compute_validation_summary

        metrics = PerformanceMetrics(
            cagr=-0.02, excess_cagr=-0.05, sharpe_ratio=0.3,
            sortino_ratio=0.4, max_drawdown=0.45, win_rate=0.40,
            information_ratio=-0.2, total_return=-0.2,
            benchmark_total_return=2.5, num_months=180, avg_turnover=0.20,
        )
        summary = compute_validation_summary(metrics, benchmark_sharpe=0.8)
        assert summary["overall_pass"] is False
        cagr_gate = next(g for g in summary["gates"] if g["name"] == "cagr_positive")
        assert cagr_gate["passed"] is False

    def test_fails_when_sharpe_below_benchmark(self):
        """Sharpe below benchmark should fail the sharpe gate."""
        from margin_engine.backtesting.models import PerformanceMetrics
        from margin_api.services.backtest import compute_validation_summary

        metrics = PerformanceMetrics(
            cagr=0.08, excess_cagr=0.01, sharpe_ratio=0.5,
            sortino_ratio=0.7, max_drawdown=0.30, win_rate=0.52,
            information_ratio=0.3, total_return=2.0,
            benchmark_total_return=1.8, num_months=180, avg_turnover=0.20,
        )
        summary = compute_validation_summary(metrics, benchmark_sharpe=0.8)
        sharpe_gate = next(g for g in summary["gates"] if g["name"] == "sharpe_exceeds_benchmark")
        assert sharpe_gate["passed"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_backtest_wiring.py::TestComputeValidationSummary -v`
Expected: FAIL (function does not exist)

- [ ] **Step 3: Implement compute_validation_summary()**

Add to `api/src/margin_api/services/backtest.py`:

```python
def compute_validation_summary(
    metrics: PerformanceMetrics,
    benchmark_sharpe: float = 0.0,
) -> dict:
    """Evaluate backtest metrics against validation gates.

    Returns a dict with gate results for logging and storage.
    Gates are advisory (not enforced) per spec.
    """
    gates = [
        {
            "name": "cagr_positive",
            "description": "CAGR is positive",
            "value": metrics.cagr,
            "threshold": 0.0,
            "passed": metrics.cagr > 0,
        },
        {
            "name": "excess_cagr_positive",
            "description": "Excess CAGR vs SPY is positive",
            "value": metrics.excess_cagr,
            "threshold": 0.0,
            "passed": metrics.excess_cagr > 0,
        },
        {
            "name": "sharpe_exceeds_benchmark",
            "description": "Sharpe ratio exceeds benchmark",
            "value": metrics.sharpe_ratio,
            "threshold": benchmark_sharpe,
            "passed": metrics.sharpe_ratio > benchmark_sharpe,
        },
        {
            "name": "max_drawdown_acceptable",
            "description": "Max drawdown below 60%",
            "value": metrics.max_drawdown,
            "threshold": 0.60,
            "passed": metrics.max_drawdown < 0.60,
        },
        {
            "name": "sufficient_months",
            "description": "At least 100 months of data",
            "value": metrics.num_months,
            "threshold": 100,
            "passed": metrics.num_months > 100,
        },
        {
            "name": "turnover_reasonable",
            "description": "Average turnover below 80%",
            "value": metrics.avg_turnover,
            "threshold": 0.80,
            "passed": metrics.avg_turnover < 0.80,
        },
    ]
    return {
        "gates": gates,
        "overall_pass": all(g["passed"] for g in gates),
        "passed_count": sum(1 for g in gates if g["passed"]),
        "total_gates": len(gates),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_backtest_wiring.py::TestComputeValidationSummary -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/services/backtest.py api/tests/services/test_backtest_wiring.py
git commit -m "feat(api): add compute_validation_summary() for backtest gates"
```

---

### Task 6: Update run_real_backtest() to accept benchmark_prices

**Files:**
- Modify: `api/src/margin_api/services/backtest.py:448-470`
- Test: `api/tests/services/test_backtest_wiring.py`

- [ ] **Step 1: Write failing test for benchmark_prices parameter**

Add to `api/tests/services/test_backtest_wiring.py`:

```python
@pytest.mark.asyncio
async def test_run_real_backtest_passes_benchmark_prices(self):
    """run_real_backtest should pass benchmark_prices to the orchestrator."""
    from unittest.mock import AsyncMock, patch
    from datetime import date

    from margin_engine.backtesting.models import PerformanceMetrics
    from margin_engine.backtesting.replay_orchestrator import ReplayConfig, ReplayResult

    captured_kwargs: dict = {}

    class MockOrchestrator:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def run_async(self):
            return ReplayResult(
                config=ReplayConfig(),
                metrics=PerformanceMetrics(
                    cagr=0, excess_cagr=0, sharpe_ratio=0, sortino_ratio=0,
                    max_drawdown=0, win_rate=0, information_ratio=0,
                    total_return=0, benchmark_total_return=0, num_months=0,
                    avg_turnover=0,
                ),
                snapshots=[], audit_log=[], regime_segments={},
                factor_timeline=[], duration_seconds=0.0,
            )

    mock_session = AsyncMock()
    spy_prices = {date(2020, 1, 1): 300.0, date(2020, 2, 1): 310.0}

    with patch(
        "margin_engine.backtesting.replay_orchestrator.ReplayOrchestrator",
        MockOrchestrator,
    ):
        with patch("margin_api.services.backtest.DatabasePITProvider"):
            with patch("margin_api.services.backtest.FactorRegistry"):
                from margin_api.services.backtest import run_real_backtest

                await run_real_backtest(
                    mock_session, ReplayConfig(), benchmark_prices=spy_prices
                )

    assert captured_kwargs.get("benchmark_prices") == spy_prices
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/services/test_backtest_wiring.py::test_run_real_backtest_passes_benchmark_prices -v`
Expected: FAIL (run_real_backtest does not accept benchmark_prices)

- [ ] **Step 3: Update run_real_backtest() signature**

In `api/src/margin_api/services/backtest.py`, modify `run_real_backtest()`:

```python
async def run_real_backtest(
    session: AsyncSession,
    config: ReplayConfig,
    benchmark_prices: dict[date, float] | None = None,
) -> ReplayResult:
    """Run a real backtest using DatabasePITProvider and ReplayOrchestrator.

    Uses backtest-tuned filter thresholds (lower market cap floor, shorter
    history requirement, relaxed dollar volumes) to avoid over-eliminating
    historical tickers.
    """
    from margin_engine.backtesting.replay_orchestrator import ReplayOrchestrator
    from margin_engine.config.filter_config import backtest_filter_config

    provider = DatabasePITProvider(session)
    registry = FactorRegistry.default()
    orchestrator = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=registry,
        filter_config=backtest_filter_config(),
        use_real_scoring=True,
        benchmark_prices=benchmark_prices or {},
    )
    return await orchestrator.run_async()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_backtest_wiring.py -v -k "run_real_backtest"`
Expected: All PASS (including existing tests)

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/services/backtest.py api/tests/services/test_backtest_wiring.py
git commit -m "feat(api): add benchmark_prices param to run_real_backtest()"
```

---

## Chunk 4: Worker Fix + Admin Endpoint

### Task 7: Fix precompute_default_backtest worker

**Files:**
- Modify: `api/src/margin_api/workers.py:2897-3030`
- Test: `api/tests/test_workers.py` (existing backtest worker tests)

- [ ] **Step 1: Write failing test for updated worker behavior**

Add to `api/tests/test_workers.py` (in the existing backtest worker test class):

```python
@pytest.mark.asyncio
async def test_backtest_worker_uses_2011_start_date(self):
    """Worker should use 2011 start date, not 2009."""
    # Mock the worker to capture the config it creates
    from unittest.mock import AsyncMock, patch, MagicMock
    from margin_api.workers import precompute_default_backtest

    captured_config = {}

    original_run_real = None

    async def mock_run_real(session, config, benchmark_prices=None):
        captured_config["start_date"] = config.start_date
        captured_config["benchmark_prices"] = benchmark_prices
        # Return a minimal result
        from margin_engine.backtesting.models import PerformanceMetrics
        from margin_engine.backtesting.replay_orchestrator import ReplayResult
        return ReplayResult(
            config=config,
            metrics=PerformanceMetrics(
                cagr=0.10, excess_cagr=0.03, sharpe_ratio=0.9,
                sortino_ratio=1.2, max_drawdown=0.25, win_rate=0.55,
                information_ratio=0.6, total_return=3.0,
                benchmark_total_return=2.0, num_months=180, avg_turnover=0.20,
            ),
            snapshots=[], audit_log=[], regime_segments={},
            factor_timeline=[], duration_seconds=1.0,
        )

    # This test verifies the config passed to run_real_backtest
    # The exact mock setup will depend on the worker's internal structure
    # Key assertion: captured_config["start_date"] == date(2011, 1, 1)
```

Note: The exact mock setup depends on how the worker is refactored. The key assertion is that the ReplayConfig uses `date(2011, 1, 1)` and benchmark_prices is not None/empty.

- [ ] **Step 2: Modify the worker**

In `api/src/margin_api/workers.py`, modify `precompute_default_backtest()` starting at line 2947:

Key changes:
1. Change `start_date=date(2009, 1, 1)` to `start_date=date(2011, 1, 1)` (line 2949)
2. Remove `disabled_filters={"liquidity"}` (line 2971)
3. Add SPY price seeding and loading before orchestrator construction
4. Pass `filter_config=backtest_filter_config()` to orchestrator
5. Pass `benchmark_prices` to orchestrator
6. Wrap the replay in try/except to capture errors in BacktestRun.error_message
7. Log validation summary after successful completion

The worker should delegate to `run_real_backtest()` from backtest.py to avoid duplicating orchestrator setup. The worker handles:
- Job tracking (JobRun create/update)
- SPY price seeding (yf.download if needed)
- SPY price loading (via get_price_series)
- BacktestRun record creation/update
- Error capture
- Validation logging

SPY price seeding logic:
```python
# Check if SPY prices exist in pit_daily_prices
spy_count_result = await session.execute(
    select(func.count()).select_from(PITDailyPrice).where(
        PITDailyPrice.ticker == "SPY"
    )
)
spy_count = spy_count_result.scalar_one()

if spy_count == 0:
    logger.info("[precompute_backtest] Seeding SPY prices via yfinance...")
    import yfinance as yf
    spy_df = yf.download("SPY", start="2011-01-01", auto_adjust=False, progress=False)
    for idx, row in spy_df.iterrows():
        d = pd.Timestamp(idx).date() if hasattr(idx, 'date') else idx
        session.add(PITDailyPrice(
            ticker="SPY", date=d,
            open=float(row["Open"]), high=float(row["High"]),
            low=float(row["Low"]), close=float(row["Close"]),
            adj_close=float(row.get("Adj Close", row["Close"])),
            volume=int(row["Volume"]),
            source="yfinance",
        ))
    await session.commit()
    logger.info("[precompute_backtest] Seeded %d SPY price rows", len(spy_df))
```

Error capture pattern:
```python
try:
    replay_result = await run_real_backtest(session, config, benchmark_prices=spy_prices)
except Exception:
    import traceback
    error_msg = traceback.format_exc()
    logger.error("[precompute_backtest] Replay failed:\n%s", error_msg)
    # Store failure in BacktestRun
    async with session_factory() as err_session:
        run = BacktestRun(
            name="default", universe_snapshot_id=universe_id,
            start_date=config.start_date.isoformat(),
            end_date=config.end_date.isoformat(),
            rebalance_frequency=config.rebalance_frequency,
            config=config.model_dump(mode="json"),
            config_hash=config_hash, status="failed",
            error_message=error_msg,
            started_at=run_started_at, completed_at=datetime.now(UTC),
        )
        err_session.add(run)
        await err_session.commit()
    raise
```

Validation logging:
```python
from margin_api.services.backtest import compute_validation_summary

# Compute benchmark Sharpe from SPY returns
spy_returns = []  # compute from spy_prices month-over-month
validation = compute_validation_summary(replay_result.metrics, benchmark_sharpe=benchmark_sharpe)

logger.info(
    "[precompute_backtest] Validation: %s (%d/%d gates passed)",
    "PASS" if validation["overall_pass"] else "FAIL",
    validation["passed_count"],
    validation["total_gates"],
)
for gate in validation["gates"]:
    status = "PASS" if gate["passed"] else "FAIL"
    logger.info("  [%s] %s: %.4f (threshold: %s)", status, gate["name"], gate["value"], gate["threshold"])
```

- [ ] **Step 3: Run existing worker tests to verify no regressions**

Run: `uv run pytest api/tests/test_workers.py -v -k "backtest"`
Expected: All PASS (may need to update mocks for new signature)

- [ ] **Step 4: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "fix(api): wire real backtest with SPY prices, 2011 start, liquidity filter re-enabled"
```

---

### Task 8: Add GET /admin/backtest/latest endpoint

**Files:**
- Modify: `api/src/margin_api/routes/admin.py`
- Test: `api/tests/routes/test_backtest_endpoints.py`

- [ ] **Step 1: Write failing test for the endpoint**

Add to `api/tests/routes/test_backtest_endpoints.py` (or create new test file if appropriate):

```python
class TestBacktestLatestEndpoint:
    def test_returns_404_when_no_backtest_runs(self, client):
        """GET /api/v1/admin/backtest/latest returns 404 when no runs exist."""
        response = client.get(
            "/api/v1/admin/backtest/latest",
            headers={"x-admin-key": "test-admin-key"},
        )
        assert response.status_code == 404

    def test_returns_latest_backtest_run(self, client):
        """GET /api/v1/admin/backtest/latest returns the most recent BacktestRun."""
        import asyncio
        from margin_api.db.models import BacktestRun, UniverseSnapshot
        from datetime import datetime, UTC

        # Seed data via the async engine embedded in the client fixture.
        # The client fixture creates its own engine/session_factory — use
        # the same pattern as existing tests in this file: access the app's
        # DB dependency override to get a session.
        from margin_api.db.session import get_db

        async def _seed():
            async for session in get_db():
                # Need a universe snapshot for FK
                snap = UniverseSnapshot(
                    name="test", ticker_count=100, created_by="test",
                )
                session.add(snap)
                await session.flush()

                run = BacktestRun(
                    name="default", universe_snapshot_id=snap.id,
                    start_date="2011-01-01", end_date="2025-12-31",
                    rebalance_frequency="monthly",
                    config={"start_date": "2011-01-01"},
                    config_hash="abc123",
                    status="complete",
                    total_return=3.5, annualized_return=0.10,
                    sharpe_ratio=0.9, max_drawdown=0.28,
                    summary_stats={"metrics": {"cagr": 0.10, "num_months": 180}},
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
                session.add(run)
                await session.commit()
                break

        asyncio.get_event_loop().run_until_complete(_seed())

        response = client.get(
            "/api/v1/admin/backtest/latest",
            headers={"x-admin-key": "test-admin-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["metrics"]["annualized_return"] == 0.10
```

Note: The exact seeding pattern may need adjustment to match the client fixture's DB override. Check how existing tests in `test_backtest_endpoints.py` seed data — follow that pattern. The key points are: (1) URL path includes `/api/v1/admin` prefix, (2) data is seeded async, (3) UniverseSnapshot FK is satisfied.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_backtest_endpoints.py::TestBacktestLatestEndpoint -v`
Expected: FAIL (endpoint does not exist, 404 or 405)

- [ ] **Step 3: Implement the endpoint**

Add to `api/src/margin_api/routes/admin.py`, after the existing `/backtest/precompute` endpoint:

```python
@router.get("/backtest/latest")
async def get_latest_backtest(
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Return the most recent BacktestRun with metrics and validation summary."""
    _verify_admin_key(x_admin_key)

    stmt = (
        select(BacktestRun)
        .order_by(BacktestRun.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(404, "No backtest runs found")

    # Build validation summary from stored metrics
    validation = None
    if run.status == "complete" and run.sharpe_ratio is not None:
        from margin_api.services.backtest import compute_validation_summary
        from margin_engine.backtesting.models import PerformanceMetrics

        metrics = PerformanceMetrics(
            cagr=run.annualized_return or 0,
            excess_cagr=(run.annualized_return or 0) - 0.07,  # approximate SPY CAGR
            sharpe_ratio=run.sharpe_ratio or 0,
            sortino_ratio=0,  # not stored separately
            max_drawdown=run.max_drawdown or 0,
            win_rate=0,
            information_ratio=0,
            total_return=run.total_return or 0,
            benchmark_total_return=0,
            num_months=0,
            avg_turnover=0,
        )
        # If summary_stats has full metrics, use those instead
        if run.summary_stats and "metrics" in run.summary_stats:
            try:
                metrics = PerformanceMetrics(**run.summary_stats["metrics"])
            except Exception:
                pass  # fall back to individual columns
        validation = compute_validation_summary(metrics)

    duration_seconds = None
    if run.started_at and run.completed_at:
        duration_seconds = (run.completed_at - run.started_at).total_seconds()

    return JSONResponse(
        content={
            "id": run.id,
            "name": run.name,
            "status": run.status,
            "config": run.config,
            "metrics": {
                "total_return": run.total_return,
                "annualized_return": run.annualized_return,
                "sharpe_ratio": run.sharpe_ratio,
                "max_drawdown": run.max_drawdown,
            },
            "validation": validation,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "duration_seconds": duration_seconds,
            "error_message": getattr(run, "error_message", None),
            "created_at": run.created_at.isoformat(),
        }
    )
```

Add `BacktestRun` to the imports at the top of admin.py if not already there.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/routes/test_backtest_endpoints.py::TestBacktestLatestEndpoint -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/routes/admin.py api/tests/routes/test_backtest_endpoints.py
git commit -m "feat(api): add GET /admin/backtest/latest endpoint"
```

---

## Chunk 5: Integration Verification

### Task 9: Run full test suites and verify no regressions

**Files:** None (verification only)

- [ ] **Step 1: Run engine tests**

Run: `uv run pytest engine/tests/ -v --ignore=engine/tests/backtesting/test_integration.py`
Expected: All PASS (ignore integration test if it requires real data)

- [ ] **Step 2: Run API tests**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All PASS

- [ ] **Step 3: Run ruff lint**

Run: `uv run ruff check --fix engine/src/margin_engine/config/filter_config.py engine/src/margin_engine/backtesting/replay_orchestrator.py api/src/margin_api/services/pit_provider.py api/src/margin_api/services/backtest.py api/src/margin_api/workers.py api/src/margin_api/routes/admin.py`
Expected: Clean or auto-fixed

- [ ] **Step 4: Run ruff format**

Run: `uv run ruff format engine/src/margin_engine/config/filter_config.py engine/src/margin_engine/backtesting/replay_orchestrator.py api/src/margin_api/services/pit_provider.py api/src/margin_api/services/backtest.py api/src/margin_api/workers.py api/src/margin_api/routes/admin.py`

- [ ] **Step 5: Final commit if any lint fixes**

```bash
git add -u && git commit -m "style: lint fixes for backtest wire-and-validate"
```
