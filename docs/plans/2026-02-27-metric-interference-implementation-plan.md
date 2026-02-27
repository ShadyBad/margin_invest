# Metric Interference Ablation Framework — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an ablation study framework that measures metric interference across the full scoring stack (elimination filters, conviction tracks, ML override) and produces actionable recommendations.

**Architecture:** A new `engine/src/margin_engine/ablation/` package containing: (1) a filter mask system that selectively enables/disables elimination filters, (2) a bootstrap statistics module for confidence intervals and hypothesis testing, (3) an ablation runner that executes backtest variants and collects metrics, (4) interference detection tests, and (5) a Shapley value calculator. The ablation runner wraps `ReplayOrchestrator` and injects masked filter configs.

**Tech Stack:** Python 3.13, numpy, scipy, pydantic, existing `ReplayOrchestrator` + `PerformanceCalculator` + `InMemoryPITProvider` infrastructure.

---

## Task 1: Add `filter_mask` parameter to `run_elimination_filters`

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/pipeline.py`
- Test: `engine/tests/scoring/filters/test_pipeline_mask.py`

**Step 1: Write the failing test**

```python
# engine/tests/scoring/filters/test_pipeline_mask.py
"""Tests for filter mask — selectively disabling elimination filters."""

from margin_engine.scoring.filters.pipeline import run_elimination_filters

from tests.fixtures.golden_apple_2024 import make_apple_period, make_apple_profile


def test_mask_disables_specified_filters():
    """When a filter name is in the mask set, it should be skipped."""
    period = make_apple_period()
    profile = make_apple_profile()

    # Run with all filters
    full = run_elimination_filters(period, profile)
    assert len(full.results) == 6

    # Run with beneish and altman disabled
    masked = run_elimination_filters(
        period, profile, disabled_filters={"beneish_m_score", "altman_z_score"}
    )
    assert len(masked.results) == 4
    names = {r.name for r in masked.results}
    assert "beneish_m_score" not in names
    assert "altman_z_score" not in names


def test_empty_mask_runs_all_filters():
    """An empty disabled set should produce the same results as no mask."""
    period = make_apple_period()
    profile = make_apple_profile()

    full = run_elimination_filters(period, profile)
    masked = run_elimination_filters(period, profile, disabled_filters=set())

    assert len(full.results) == len(masked.results)
    for f, m in zip(full.results, masked.results):
        assert f.name == m.name
        assert f.passed == m.passed


def test_mask_all_filters_returns_empty():
    """Disabling all 6 filters should return an empty results list."""
    period = make_apple_period()
    profile = make_apple_profile()

    all_names = {
        "liquidity", "beneish_m_score", "altman_z_score",
        "fcf_distress", "interest_coverage", "current_ratio",
    }
    masked = run_elimination_filters(period, profile, disabled_filters=all_names)
    assert len(masked.results) == 0
    assert masked.passed is True  # No filters to fail
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/filters/test_pipeline_mask.py -v`
Expected: FAIL — `run_elimination_filters() got an unexpected keyword argument 'disabled_filters'`

**Step 3: Write minimal implementation**

Modify `engine/src/margin_engine/scoring/filters/pipeline.py`:

Add `disabled_filters: set[str] | None = None` parameter to `run_elimination_filters()`. After building the `results` list, filter out any result whose `name` is in `disabled_filters`. The filter functions still have their canonical names:
- `"liquidity"` — from `liquidity_result.name`
- `"beneish_m_score"` — from `beneish_result.name`
- `"altman_z_score"` — from `altman_result.name`
- `"fcf_distress"` — from `fcf_result.name`
- `"interest_coverage"` — from `interest_result.name`
- `"current_ratio"` — from `current_result.name`

Implementation approach: Do NOT skip execution (filters are fast, ~50μs each). Instead, build the full results list as today, then exclude disabled filters before returning. This preserves the no-short-circuit guarantee and keeps the code change minimal.

```python
def run_elimination_filters(
    period: FinancialPeriod,
    profile: AssetProfile,
    config: FilterConfig | None = None,
    history: FinancialHistory | None = None,
    price_bars: list[PriceBar] | None = None,
    disabled_filters: set[str] | None = None,
) -> PipelineResult:
    # ... existing code unchanged ...

    results = [
        liquidity_result,
        beneish_result,
        altman_result,
        fcf_result,
        interest_result,
        current_result,
    ]

    if disabled_filters:
        results = [r for r in results if r.name not in disabled_filters]

    return PipelineResult(results=results)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/filters/test_pipeline_mask.py -v`
Expected: 3 passed

**Step 5: Run existing pipeline tests to verify no regression**

Run: `uv run pytest engine/tests/scoring/filters/test_pipeline.py -v`
Expected: All existing tests pass (default `disabled_filters=None` changes nothing)

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/filters/pipeline.py engine/tests/scoring/filters/test_pipeline_mask.py
git commit -m "feat(engine): add disabled_filters mask to elimination pipeline"
```

---

## Task 2: Add `filter_config` and `disabled_filters` to `ReplayOrchestrator`

**Files:**
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py`
- Test: `engine/tests/backtesting/test_replay_filter_config.py`

**Step 1: Write the failing test**

```python
# engine/tests/backtesting/test_replay_filter_config.py
"""Tests for custom filter configuration in replay orchestrator."""

from datetime import date

from margin_engine.backtesting.replay_orchestrator import (
    ReplayConfig,
    ReplayOrchestrator,
    ReplayResult,
)
from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.pit_provider import InMemoryPITProvider
from margin_engine.config.filter_config import FilterConfig

from tests.backtesting.helpers import build_pit_provider_with_tickers


def test_orchestrator_accepts_filter_config():
    """ReplayOrchestrator should accept a custom FilterConfig."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT"],
        start=date(2020, 1, 1),
        end=date(2020, 3, 1),
    )
    config = ReplayConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 3, 1),
    )
    custom_filter = FilterConfig()

    orch = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
        filter_config=custom_filter,
    )
    result = orch.run()
    assert isinstance(result, ReplayResult)


def test_orchestrator_accepts_disabled_filters():
    """ReplayOrchestrator should accept disabled_filters set."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT"],
        start=date(2020, 1, 1),
        end=date(2020, 3, 1),
    )
    config = ReplayConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 3, 1),
    )

    orch = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
        disabled_filters={"altman_z_score", "current_ratio"},
    )
    result = orch.run()
    assert isinstance(result, ReplayResult)


def test_disabled_filters_increases_survivors():
    """Disabling filters should produce >= as many survivors as full filtering."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        start=date(2020, 1, 1),
        end=date(2020, 2, 1),
    )
    config = ReplayConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 2, 1),
    )

    full = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
    )
    full_result = full.run()

    relaxed = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
        disabled_filters={"beneish_m_score", "altman_z_score", "interest_coverage", "current_ratio"},
    )
    relaxed_result = relaxed.run()

    # With fewer filters, survivor count should be >= full
    if full_result.audit_log and relaxed_result.audit_log:
        assert relaxed_result.audit_log[0].survivor_count >= full_result.audit_log[0].survivor_count
```

Note: `build_pit_provider_with_tickers` is a test helper that creates an `InMemoryPITProvider` with synthetic financial data. If this helper doesn't exist yet, create it in `engine/tests/backtesting/helpers.py` using the golden Apple fixture pattern — construct `AssetProfile` and `FinancialPeriod` objects with plausible values for each ticker. Check `engine/tests/backtesting/` for existing test helpers first.

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_replay_filter_config.py -v`
Expected: FAIL — `ReplayOrchestrator.__init__() got an unexpected keyword argument 'filter_config'`

**Step 3: Write minimal implementation**

Modify `ReplayOrchestrator.__init__()` to accept two new optional parameters:

```python
def __init__(
    self,
    config: ReplayConfig,
    pit_provider: PointInTimeProvider,
    factor_registry: FactorRegistry,
    benchmark_prices: dict[date, float] | None = None,
    filter_config: FilterConfig | None = None,
    disabled_filters: set[str] | None = None,
) -> None:
    self._config = config
    self._provider = pit_provider
    self._registry = factor_registry
    self._benchmark_prices = benchmark_prices or {}
    self._calculator = PerformanceCalculator()
    self._filter_config = filter_config
    self._disabled_filters = disabled_filters
```

Add import: `from margin_engine.config.filter_config import FilterConfig`

Modify the filter call in `run()` (around line 162):

```python
filter_result = run_elimination_filters(
    period=snapshot.period,
    profile=snapshot.profile,
    config=self._filter_config,
    disabled_filters=self._disabled_filters,
)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_replay_filter_config.py -v`
Expected: 3 passed

**Step 5: Run existing backtest tests**

Run: `uv run pytest engine/tests/backtesting/ -v`
Expected: All existing tests pass

**Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/replay_orchestrator.py engine/tests/backtesting/test_replay_filter_config.py
git commit -m "feat(engine): add filter_config and disabled_filters to ReplayOrchestrator"
```

---

## Task 3: Bootstrap statistics module

**Files:**
- Create: `engine/src/margin_engine/ablation/__init__.py`
- Create: `engine/src/margin_engine/ablation/bootstrap.py`
- Test: `engine/tests/ablation/test_bootstrap.py`

**Step 1: Write the failing test**

```python
# engine/tests/ablation/__init__.py
# (empty)

# engine/tests/ablation/test_bootstrap.py
"""Tests for block bootstrap confidence intervals and hypothesis tests."""

import numpy as np

from margin_engine.ablation.bootstrap import (
    block_bootstrap_ci,
    bootstrap_sharpe_difference,
)


def test_block_bootstrap_ci_known_mean():
    """Bootstrap CI of a constant series should be tight around the constant."""
    rng = np.random.default_rng(42)
    data = np.full(120, 0.01)  # 10 years of 1% monthly returns
    low, point, high = block_bootstrap_ci(data, n_resamples=1000, block_size=3, seed=42)
    assert abs(point - 0.01) < 1e-6
    assert abs(high - low) < 1e-4  # Very tight CI for constant data


def test_block_bootstrap_ci_respects_alpha():
    """Wider alpha should produce narrower CI."""
    rng = np.random.default_rng(42)
    data = rng.normal(0.005, 0.04, size=120)

    _, _, wide_high = block_bootstrap_ci(data, alpha=0.01, n_resamples=5000, seed=42)
    _, _, narrow_high = block_bootstrap_ci(data, alpha=0.10, n_resamples=5000, seed=42)
    # 99% CI should be wider than 90% CI
    # (compare high end as proxy)
    assert wide_high >= narrow_high


def test_bootstrap_sharpe_difference_same_series():
    """Sharpe difference between identical series should have CI spanning zero."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.005, 0.04, size=120)

    result = bootstrap_sharpe_difference(returns, returns, n_resamples=5000, seed=42)
    assert result.ci_low <= 0.0 <= result.ci_high
    assert abs(result.point_estimate) < 0.01


def test_bootstrap_sharpe_difference_detects_clear_winner():
    """When one series clearly dominates, CI should not span zero."""
    rng = np.random.default_rng(42)
    good = rng.normal(0.02, 0.03, size=120)   # 2% monthly, low vol
    bad = rng.normal(-0.01, 0.06, size=120)    # -1% monthly, high vol

    result = bootstrap_sharpe_difference(good, bad, n_resamples=5000, seed=42)
    assert result.ci_low > 0  # Good clearly better
    assert result.significant is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/ablation/test_bootstrap.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.ablation'`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/ablation/__init__.py
"""Ablation study framework for metric interference analysis."""

# engine/src/margin_engine/ablation/bootstrap.py
"""Block bootstrap statistics for backtesting comparisons.

Uses block bootstrap (Kunsch 1989) to preserve autocorrelation structure
in monthly return series. All functions are deterministic given a seed.
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel


class SharpeDifferenceResult(BaseModel):
    """Result of a bootstrap Sharpe ratio difference test."""

    point_estimate: float
    ci_low: float
    ci_high: float
    p_value: float
    significant: bool
    n_resamples: int

    model_config = {"arbitrary_types_allowed": True}


def block_bootstrap_ci(
    data: np.ndarray,
    statistic: str = "mean",
    alpha: float = 0.05,
    n_resamples: int = 10_000,
    block_size: int = 3,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Compute block bootstrap confidence interval.

    Args:
        data: 1-D array of observations (e.g., monthly returns).
        statistic: Which statistic to bootstrap ("mean" or "sharpe").
        alpha: Significance level (0.05 = 95% CI).
        n_resamples: Number of bootstrap resamples.
        block_size: Block length for preserving autocorrelation.
        seed: Random seed for reproducibility.

    Returns:
        (ci_low, point_estimate, ci_high) tuple.
    """
    rng = np.random.default_rng(seed)
    n = len(data)
    point = _compute_statistic(data, statistic)

    boot_stats = np.empty(n_resamples)
    for i in range(n_resamples):
        sample = _draw_block_sample(data, n, block_size, rng)
        boot_stats[i] = _compute_statistic(sample, statistic)

    ci_low = float(np.percentile(boot_stats, 100 * alpha / 2))
    ci_high = float(np.percentile(boot_stats, 100 * (1 - alpha / 2)))
    return ci_low, point, ci_high


def bootstrap_sharpe_difference(
    returns_a: np.ndarray,
    returns_b: np.ndarray,
    alpha: float = 0.05,
    n_resamples: int = 10_000,
    block_size: int = 3,
    risk_free_annual: float = 0.04,
    seed: int = 42,
) -> SharpeDifferenceResult:
    """Bootstrap test for difference in annualized Sharpe ratios.

    Uses paired block bootstrap — the same block indices are applied to
    both series to preserve cross-correlation structure.

    Args:
        returns_a: Monthly returns for strategy A.
        returns_b: Monthly returns for strategy B.
        alpha: Significance level.
        n_resamples: Number of bootstrap resamples.
        block_size: Block length.
        risk_free_annual: Annual risk-free rate.
        seed: Random seed.

    Returns:
        SharpeDifferenceResult with CI, p-value, and significance flag.
    """
    rng = np.random.default_rng(seed)
    n = min(len(returns_a), len(returns_b))
    a = returns_a[:n]
    b = returns_b[:n]
    rf_monthly = risk_free_annual / 12.0

    point = _annualized_sharpe(a, rf_monthly) - _annualized_sharpe(b, rf_monthly)

    diffs = np.empty(n_resamples)
    for i in range(n_resamples):
        indices = _block_indices(n, block_size, rng)
        sa = _annualized_sharpe(a[indices], rf_monthly)
        sb = _annualized_sharpe(b[indices], rf_monthly)
        diffs[i] = sa - sb

    ci_low = float(np.percentile(diffs, 100 * alpha / 2))
    ci_high = float(np.percentile(diffs, 100 * (1 - alpha / 2)))

    # Two-sided p-value: proportion of bootstrap samples on the other side of zero
    if point >= 0:
        p_value = float(np.mean(diffs <= 0)) * 2
    else:
        p_value = float(np.mean(diffs >= 0)) * 2
    p_value = min(p_value, 1.0)

    return SharpeDifferenceResult(
        point_estimate=float(point),
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        significant=(ci_low > 0 or ci_high < 0),
        n_resamples=n_resamples,
    )


def _draw_block_sample(
    data: np.ndarray, n: int, block_size: int, rng: np.random.Generator
) -> np.ndarray:
    """Draw a single block bootstrap sample of length n."""
    indices = _block_indices(n, block_size, rng)
    return data[indices]


def _block_indices(
    n: int, block_size: int, rng: np.random.Generator
) -> np.ndarray:
    """Generate block bootstrap indices of length n."""
    n_blocks = math.ceil(n / block_size)
    starts = rng.integers(0, n, size=n_blocks)
    indices = np.concatenate([np.arange(s, s + block_size) % n for s in starts])
    return indices[:n]


def _compute_statistic(data: np.ndarray, name: str) -> float:
    """Compute a named statistic on a 1-D array."""
    if name == "mean":
        return float(np.mean(data))
    if name == "sharpe":
        return _annualized_sharpe(data, 0.04 / 12)
    raise ValueError(f"Unknown statistic: {name}")


def _annualized_sharpe(
    monthly_returns: np.ndarray, rf_monthly: float
) -> float:
    """Compute annualized Sharpe ratio from monthly returns."""
    excess = monthly_returns - rf_monthly
    if len(excess) < 2:
        return 0.0
    std = float(np.std(excess, ddof=1))
    if std < 1e-12:
        return 0.0
    return float(np.mean(excess) / std * math.sqrt(12))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/ablation/test_bootstrap.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ablation/__init__.py engine/src/margin_engine/ablation/bootstrap.py engine/tests/ablation/__init__.py engine/tests/ablation/test_bootstrap.py
git commit -m "feat(engine): add block bootstrap statistics module for ablation studies"
```

---

## Task 4: Ablation runner — single-filter baselines and pairwise combinations

**Files:**
- Create: `engine/src/margin_engine/ablation/runner.py`
- Test: `engine/tests/ablation/test_runner.py`

**Step 1: Write the failing test**

```python
# engine/tests/ablation/test_runner.py
"""Tests for the ablation study runner."""

from datetime import date

from margin_engine.ablation.runner import (
    AblationConfig,
    AblationResult,
    AblationRunner,
    FilterCombination,
)
from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.pit_provider import InMemoryPITProvider

from tests.backtesting.helpers import build_pit_provider_with_tickers

ALL_FILTERS = {
    "liquidity", "beneish_m_score", "altman_z_score",
    "fcf_distress", "interest_coverage", "current_ratio",
}


def test_single_filter_baselines():
    """Phase 1: should run 7 backtests (control + 6 single-filter)."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT", "GOOGL"],
        start=date(2020, 1, 1),
        end=date(2020, 6, 1),
    )
    config = AblationConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 6, 1),
    )
    runner = AblationRunner(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
    )
    results = runner.run_single_filter_baselines()

    # Control (no filters) + 6 single-filter runs
    assert len(results) == 7
    assert results[0].combination.name == "control"
    assert results[0].combination.enabled_filters == set()
    for r in results[1:]:
        assert len(r.combination.enabled_filters) == 1


def test_pairwise_combinations():
    """Phase 2: should run C(6,2) = 15 pairwise backtests."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT", "GOOGL"],
        start=date(2020, 1, 1),
        end=date(2020, 4, 1),
    )
    config = AblationConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 4, 1),
    )
    runner = AblationRunner(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
    )
    results = runner.run_pairwise_combinations()
    assert len(results) == 15
    for r in results:
        assert len(r.combination.enabled_filters) == 2


def test_ablation_result_has_metrics():
    """Each ablation result should contain performance metrics."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT"],
        start=date(2020, 1, 1),
        end=date(2020, 3, 1),
    )
    config = AblationConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 3, 1),
    )
    runner = AblationRunner(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
    )
    results = runner.run_single_filter_baselines()
    for r in results:
        assert r.metrics is not None
        assert hasattr(r.metrics, "sharpe_ratio")
        assert hasattr(r.metrics, "cagr")
        assert r.survivor_counts is not None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/ablation/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.ablation.runner'`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/ablation/runner.py
"""Ablation study runner for metric interference analysis.

Executes backtest variants with different filter combinations and collects
performance metrics for comparison. Wraps ReplayOrchestrator with filter
mask injection.
"""

from __future__ import annotations

from datetime import date
from itertools import combinations

from pydantic import BaseModel, Field

from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.models import PerformanceMetrics
from margin_engine.backtesting.pit_provider import PointInTimeProvider
from margin_engine.backtesting.replay_orchestrator import (
    ReplayConfig,
    ReplayOrchestrator,
)

ALL_FILTER_NAMES: set[str] = {
    "liquidity",
    "beneish_m_score",
    "altman_z_score",
    "fcf_distress",
    "interest_coverage",
    "current_ratio",
}


class FilterCombination(BaseModel):
    """A specific set of enabled filters for one ablation run."""

    name: str
    enabled_filters: set[str]

    @property
    def disabled_filters(self) -> set[str]:
        return ALL_FILTER_NAMES - self.enabled_filters


class AblationConfig(BaseModel):
    """Configuration for an ablation study."""

    start_date: date = Field(default=date(2006, 1, 1))
    end_date: date = Field(default_factory=date.today)
    rebalance_frequency: str = "monthly"
    conviction_threshold: float = 0.10
    weighting: str = "equal"
    transaction_cost_bps: float = 20.0


class AblationResult(BaseModel):
    """Result of a single ablation run."""

    combination: FilterCombination
    metrics: PerformanceMetrics
    survivor_counts: list[int] = Field(default_factory=list)
    monthly_returns: list[float] = Field(default_factory=list)


class AblationRunner:
    """Executes backtest variants with different filter combinations."""

    def __init__(
        self,
        config: AblationConfig,
        pit_provider: PointInTimeProvider,
        factor_registry: FactorRegistry,
        benchmark_prices: dict[date, float] | None = None,
    ) -> None:
        self._config = config
        self._provider = pit_provider
        self._registry = factor_registry
        self._benchmark_prices = benchmark_prices

    def run_single_filter_baselines(self) -> list[AblationResult]:
        """Phase 1: Control (no filters) + each filter in isolation."""
        combinations_list = [
            FilterCombination(name="control", enabled_filters=set()),
        ]
        for f in sorted(ALL_FILTER_NAMES):
            combinations_list.append(
                FilterCombination(name=f"only_{f}", enabled_filters={f})
            )
        return [self._run_combination(c) for c in combinations_list]

    def run_pairwise_combinations(self) -> list[AblationResult]:
        """Phase 2: All C(6,2) = 15 pairwise filter combinations."""
        results = []
        for pair in combinations(sorted(ALL_FILTER_NAMES), 2):
            combo = FilterCombination(
                name=f"{pair[0]}+{pair[1]}",
                enabled_filters=set(pair),
            )
            results.append(self._run_combination(combo))
        return results

    def run_incremental_stack(
        self, order: list[str] | None = None,
    ) -> list[AblationResult]:
        """Phase 3: Incremental stacking in specified order.

        Returns N+1 results: empty set, then adding one filter at a time.
        """
        if order is None:
            order = [
                "liquidity", "beneish_m_score", "altman_z_score",
                "fcf_distress", "interest_coverage", "current_ratio",
            ]

        results = []
        enabled: set[str] = set()

        # Baseline: no filters
        combo = FilterCombination(name="stack_0", enabled_filters=set())
        results.append(self._run_combination(combo))

        for i, f in enumerate(order, 1):
            enabled = enabled | {f}
            combo = FilterCombination(
                name=f"stack_{i}_{f}",
                enabled_filters=set(enabled),
            )
            results.append(self._run_combination(combo))

        return results

    def run_combination(self, combination: FilterCombination) -> AblationResult:
        """Run a single arbitrary filter combination."""
        return self._run_combination(combination)

    def _run_combination(self, combination: FilterCombination) -> AblationResult:
        """Execute a single backtest with the specified filter combination."""
        replay_config = ReplayConfig(
            start_date=self._config.start_date,
            end_date=self._config.end_date,
            rebalance_frequency=self._config.rebalance_frequency,
            conviction_threshold=self._config.conviction_threshold,
            weighting=self._config.weighting,
            transaction_cost_bps=self._config.transaction_cost_bps,
        )

        orchestrator = ReplayOrchestrator(
            config=replay_config,
            pit_provider=self._provider,
            factor_registry=self._registry,
            benchmark_prices=self._benchmark_prices,
            disabled_filters=combination.disabled_filters if combination.enabled_filters else ALL_FILTER_NAMES,
        )

        # Special case: "control" means NO filters active → disable ALL
        if not combination.enabled_filters:
            orchestrator = ReplayOrchestrator(
                config=replay_config,
                pit_provider=self._provider,
                factor_registry=self._registry,
                benchmark_prices=self._benchmark_prices,
                disabled_filters=ALL_FILTER_NAMES,
            )

        result = orchestrator.run()

        survivor_counts = [a.survivor_count for a in result.audit_log]
        monthly_returns = [s.portfolio_return for s in result.snapshots]

        return AblationResult(
            combination=combination,
            metrics=result.metrics,
            survivor_counts=survivor_counts,
            monthly_returns=monthly_returns,
        )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/ablation/test_runner.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ablation/runner.py engine/tests/ablation/test_runner.py
git commit -m "feat(engine): add ablation runner for single-filter and pairwise backtest variants"
```

---

## Task 5: Interference detection tests

**Files:**
- Create: `engine/src/margin_engine/ablation/detection.py`
- Test: `engine/tests/ablation/test_detection.py`

**Step 1: Write the failing test**

```python
# engine/tests/ablation/test_detection.py
"""Tests for interference detection algorithms."""

import numpy as np

from margin_engine.ablation.detection import (
    InterferenceReport,
    detect_degradation,
    detect_negative_marginal,
    detect_pairwise_destruction,
    detect_universe_collapse,
    detect_volatility_injection,
    compute_failure_correlation,
)


def test_detect_degradation_when_stack_worse():
    """Should detect interference when full stack underperforms best single."""
    full_stack_sharpe = 0.6
    single_sharpes = {"liquidity": 0.8, "beneish": 0.5, "altman": 0.4}

    result = detect_degradation(full_stack_sharpe, single_sharpes)
    assert result.detected is True
    assert result.severity > 0
    assert result.best_single == "liquidity"


def test_detect_degradation_when_stack_better():
    """Should not detect interference when full stack outperforms."""
    full_stack_sharpe = 1.0
    single_sharpes = {"liquidity": 0.8, "beneish": 0.5}

    result = detect_degradation(full_stack_sharpe, single_sharpes)
    assert result.detected is False


def test_detect_negative_marginal():
    """Should identify filters with negative marginal contribution."""
    # Stack: [0.5, 0.6, 0.55, 0.7, 0.65, 0.68, 0.60]
    # MC:    [  -,  0.1, -0.05, 0.15, -0.05, 0.03, -0.08]
    stack_sharpes = [0.5, 0.6, 0.55, 0.7, 0.65, 0.68, 0.60]
    filter_order = ["liq", "ben", "alt", "fcf", "int", "cur"]

    negatives = detect_negative_marginal(stack_sharpes, filter_order, threshold=-0.02)
    names = {n.filter_name for n in negatives}
    assert "ben" in names   # MC = -0.05
    assert "fcf" in names   # MC = -0.05
    assert "cur" in names   # MC = -0.08


def test_detect_pairwise_destruction():
    """Should identify destructive filter pairs."""
    single_sharpes = {"a": 0.8, "b": 0.7, "c": 0.5}
    pair_sharpes = {("a", "b"): 0.6, ("a", "c"): 0.9, ("b", "c"): 0.4}

    destructive = detect_pairwise_destruction(single_sharpes, pair_sharpes, threshold=-0.03)
    pair_names = {(d.filter_a, d.filter_b) for d in destructive}
    assert ("a", "b") in pair_names  # 0.6 - max(0.8,0.7) = -0.2
    assert ("b", "c") in pair_names  # 0.4 - max(0.7,0.5) = -0.3
    assert ("a", "c") not in pair_names  # 0.9 - max(0.8,0.5) = +0.1


def test_detect_universe_collapse():
    """Should flag filters with <1% unique kill rate."""
    # Universe of 1000, filter results per ticker
    fail_vectors = {
        "filter_a": np.array([1] * 200 + [0] * 800),  # 200 fail
        "filter_b": np.array([1] * 195 + [0] * 805),   # 195 fail, mostly same as A
    }
    # filter_b's unique kills: those that fail B but pass A
    # If overlap is 190, unique_b = 5/1000 = 0.5% → flagged

    result = detect_universe_collapse(fail_vectors, threshold=0.01)
    # At least one should be flagged if overlap is high
    assert isinstance(result, list)


def test_failure_correlation():
    """Should compute pairwise failure correlation matrix."""
    rng = np.random.default_rng(42)
    # Highly correlated failure patterns
    base = rng.integers(0, 2, size=500)
    vectors = {
        "a": base.copy(),
        "b": base.copy(),  # Perfect correlation with a
        "c": rng.integers(0, 2, size=500),  # Independent
    }

    corr_matrix = compute_failure_correlation(vectors)
    assert abs(corr_matrix["a"]["b"] - 1.0) < 0.01  # Near-perfect
    assert abs(corr_matrix["a"]["c"]) < 0.3  # Low correlation
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/ablation/test_detection.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.ablation.detection'`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/ablation/detection.py
"""Interference detection tests for the ablation framework.

Implements the 5 detection tests from the design document:
1. Performance degradation vs. best single gate
2. Negative marginal contribution
3. Pairwise destructive interaction
4. Universe collapse / redundancy
5. Volatility injection without return improvement
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel


class DegradationResult(BaseModel):
    """Result of Test 1: full-stack vs. best single gate."""

    detected: bool
    severity: float
    best_single: str
    best_single_sharpe: float
    full_stack_sharpe: float


class NegativeMarginalResult(BaseModel):
    """Result of Test 2: a filter with negative marginal contribution."""

    filter_name: str
    marginal_contribution: float
    position_in_stack: int


class PairwiseDestructionResult(BaseModel):
    """Result of Test 3: a destructive filter pair."""

    filter_a: str
    filter_b: str
    pair_sharpe: float
    best_single_sharpe: float
    interaction_effect: float


class CollapseResult(BaseModel):
    """Result of Test 4: a filter with low unique kill rate."""

    filter_name: str
    total_kills: int
    unique_kills: int
    unique_kill_rate: float


class VolatilityInjectionResult(BaseModel):
    """Result of Test 5: volatility increased without return improvement."""

    filter_name: str
    vol_with: float
    vol_without: float
    return_with: float
    return_without: float
    detected: bool


class InterferenceReport(BaseModel):
    """Aggregate report of all interference detection tests."""

    degradation: DegradationResult | None = None
    negative_marginals: list[NegativeMarginalResult] = []
    destructive_pairs: list[PairwiseDestructionResult] = []
    collapse_flags: list[CollapseResult] = []
    volatility_injections: list[VolatilityInjectionResult] = []


def detect_degradation(
    full_stack_sharpe: float,
    single_sharpes: dict[str, float],
) -> DegradationResult:
    """Test 1: Does the full stack underperform the best single filter?"""
    best_name = max(single_sharpes, key=single_sharpes.get)
    best_sharpe = single_sharpes[best_name]
    delta = full_stack_sharpe - best_sharpe
    severity = abs(delta) / best_sharpe if best_sharpe != 0 else 0.0

    return DegradationResult(
        detected=delta < 0,
        severity=severity if delta < 0 else 0.0,
        best_single=best_name,
        best_single_sharpe=best_sharpe,
        full_stack_sharpe=full_stack_sharpe,
    )


def detect_negative_marginal(
    stack_sharpes: list[float],
    filter_order: list[str],
    threshold: float = -0.02,
) -> list[NegativeMarginalResult]:
    """Test 2: Identify filters with negative marginal Sharpe contribution.

    Args:
        stack_sharpes: Sharpe ratios at each incremental step.
            Index 0 = no filters (control), index i = filters 0..i-1 enabled.
        filter_order: Filter names in stacking order (length = len(stack_sharpes) - 1).
        threshold: Minimum negative MC to flag (default -0.02).
    """
    results = []
    for i, name in enumerate(filter_order):
        mc = stack_sharpes[i + 1] - stack_sharpes[i]
        if mc < threshold:
            results.append(NegativeMarginalResult(
                filter_name=name,
                marginal_contribution=mc,
                position_in_stack=i,
            ))
    return results


def detect_pairwise_destruction(
    single_sharpes: dict[str, float],
    pair_sharpes: dict[tuple[str, str], float],
    threshold: float = -0.03,
) -> list[PairwiseDestructionResult]:
    """Test 3: Identify destructive filter pairs.

    A pair is destructive when Sharpe(A+B) < max(Sharpe(A), Sharpe(B)).
    """
    results = []
    for (a, b), pair_sharpe in pair_sharpes.items():
        best = max(single_sharpes.get(a, 0.0), single_sharpes.get(b, 0.0))
        interaction = pair_sharpe - best
        if interaction < threshold:
            results.append(PairwiseDestructionResult(
                filter_a=a,
                filter_b=b,
                pair_sharpe=pair_sharpe,
                best_single_sharpe=best,
                interaction_effect=interaction,
            ))
    return results


def detect_universe_collapse(
    fail_vectors: dict[str, np.ndarray],
    threshold: float = 0.01,
) -> list[CollapseResult]:
    """Test 4: Identify filters with low unique kill rate.

    Args:
        fail_vectors: Dict of filter_name -> binary array (1=fail, 0=pass)
            for every ticker in the universe.
        threshold: Minimum unique kill rate to avoid flagging.
    """
    n = len(next(iter(fail_vectors.values())))
    filter_names = list(fail_vectors.keys())
    results = []

    for name in filter_names:
        fails = fail_vectors[name]
        total_kills = int(np.sum(fails))

        # Unique kills: fail this filter AND pass ALL others
        others_fail = np.zeros(n, dtype=bool)
        for other_name, other_fails in fail_vectors.items():
            if other_name != name:
                others_fail |= other_fails.astype(bool)

        unique = fails.astype(bool) & ~others_fail
        unique_kills = int(np.sum(unique))
        unique_rate = unique_kills / n if n > 0 else 0.0

        if unique_rate < threshold:
            results.append(CollapseResult(
                filter_name=name,
                total_kills=total_kills,
                unique_kills=unique_kills,
                unique_kill_rate=unique_rate,
            ))

    return results


def detect_volatility_injection(
    returns_with: dict[str, np.ndarray],
    returns_without: dict[str, np.ndarray],
) -> list[VolatilityInjectionResult]:
    """Test 5: Identify filters that increase vol without improving return.

    Args:
        returns_with: filter_name -> monthly returns WITH this filter active.
        returns_without: filter_name -> monthly returns WITHOUT this filter.
    """
    results = []
    for name in returns_with:
        with_arr = returns_with[name]
        without_arr = returns_without[name]

        vol_with = float(np.std(with_arr, ddof=1)) if len(with_arr) > 1 else 0.0
        vol_without = float(np.std(without_arr, ddof=1)) if len(without_arr) > 1 else 0.0
        ret_with = float(np.mean(with_arr))
        ret_without = float(np.mean(without_arr))

        detected = vol_with > vol_without and ret_with <= ret_without

        results.append(VolatilityInjectionResult(
            filter_name=name,
            vol_with=vol_with,
            vol_without=vol_without,
            return_with=ret_with,
            return_without=ret_without,
            detected=detected,
        ))

    return results


def compute_failure_correlation(
    fail_vectors: dict[str, np.ndarray],
) -> dict[str, dict[str, float]]:
    """Compute pairwise Pearson correlation of filter failure vectors.

    Args:
        fail_vectors: Dict of filter_name -> binary array (1=fail, 0=pass).

    Returns:
        Nested dict: corr[filter_a][filter_b] = Pearson r.
    """
    names = sorted(fail_vectors.keys())
    matrix = np.column_stack([fail_vectors[n].astype(float) for n in names])

    # Handle constant columns (all-pass or all-fail)
    corr = {}
    for i, a in enumerate(names):
        corr[a] = {}
        for j, b in enumerate(names):
            if i == j:
                corr[a][b] = 1.0
            else:
                col_a = matrix[:, i]
                col_b = matrix[:, j]
                std_a = np.std(col_a)
                std_b = np.std(col_b)
                if std_a < 1e-12 or std_b < 1e-12:
                    corr[a][b] = 0.0
                else:
                    corr[a][b] = float(np.corrcoef(col_a, col_b)[0, 1])

    return corr
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/ablation/test_detection.py -v`
Expected: 6 passed

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ablation/detection.py engine/tests/ablation/test_detection.py
git commit -m "feat(engine): add 5 interference detection tests for ablation framework"
```

---

## Task 6: Shapley value calculator

**Files:**
- Create: `engine/src/margin_engine/ablation/shapley.py`
- Test: `engine/tests/ablation/test_shapley.py`

**Step 1: Write the failing test**

```python
# engine/tests/ablation/test_shapley.py
"""Tests for Shapley value decomposition of filter contributions."""

import math

from margin_engine.ablation.shapley import (
    ShapleyResult,
    compute_shapley_values,
)


def test_shapley_values_sum_to_grand_coalition():
    """Shapley values should sum to v(N) - v(empty)."""
    # 3 filters for tractability
    # v(S) = number of filters in S (linear, no interaction)
    def value_fn(enabled: frozenset[str]) -> float:
        return float(len(enabled))

    filters = ["a", "b", "c"]
    result = compute_shapley_values(filters, value_fn)

    total = sum(result.values.values())
    grand = value_fn(frozenset(filters))
    empty = value_fn(frozenset())
    assert abs(total - (grand - empty)) < 1e-6


def test_shapley_symmetric_players():
    """Symmetric filters should have equal Shapley values."""
    def value_fn(enabled: frozenset[str]) -> float:
        return float(len(enabled))

    filters = ["a", "b", "c"]
    result = compute_shapley_values(filters, value_fn)

    vals = list(result.values.values())
    assert all(abs(v - vals[0]) < 1e-6 for v in vals)


def test_shapley_null_player():
    """A filter that never changes v(S) should have Shapley value = 0."""
    def value_fn(enabled: frozenset[str]) -> float:
        # "c" contributes nothing
        return float(len(enabled - {"c"}))

    filters = ["a", "b", "c"]
    result = compute_shapley_values(filters, value_fn)
    assert abs(result.values["c"]) < 1e-6
    assert result.values["a"] > 0


def test_shapley_records_coalition_values():
    """Should record all 2^N coalition values for auditability."""
    def value_fn(enabled: frozenset[str]) -> float:
        return float(len(enabled))

    filters = ["a", "b"]
    result = compute_shapley_values(filters, value_fn)
    # 2^2 = 4 coalitions
    assert len(result.coalition_values) == 4
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/ablation/test_shapley.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.ablation.shapley'`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/ablation/shapley.py
"""Exact Shapley value computation for filter contribution decomposition.

For N filters, computes all 2^N coalition values and derives each filter's
marginal contribution averaged over all orderings. Tractable for N <= 8
(256 coalitions). For larger sets, restrict to a subset of filters.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from itertools import combinations

from pydantic import BaseModel


class ShapleyResult(BaseModel):
    """Shapley value decomposition result."""

    values: dict[str, float]
    coalition_values: dict[str, float]  # frozenset key as comma-joined string
    n_coalitions: int


def compute_shapley_values(
    filters: list[str],
    value_fn: Callable[[frozenset[str]], float],
) -> ShapleyResult:
    """Compute exact Shapley values for a set of filters.

    Args:
        filters: List of filter names.
        value_fn: Function mapping a frozenset of enabled filters to a
            scalar performance metric (e.g., Sharpe ratio). Called once
            per coalition (2^N times).

    Returns:
        ShapleyResult with per-filter Shapley values and all coalition values.
    """
    n = len(filters)
    filter_set = set(filters)

    # Pre-compute all coalition values
    coalition_values: dict[frozenset[str], float] = {}
    for size in range(n + 1):
        for combo in combinations(filters, size):
            key = frozenset(combo)
            coalition_values[key] = value_fn(key)

    # Also compute empty coalition
    coalition_values[frozenset()] = value_fn(frozenset())

    # Compute Shapley values
    shapley: dict[str, float] = {}
    for i in filters:
        phi = 0.0
        others = [f for f in filters if f != i]
        n_others = len(others)

        for size in range(n_others + 1):
            for combo in combinations(others, size):
                s = frozenset(combo)
                s_with_i = s | {i}
                marginal = coalition_values[s_with_i] - coalition_values[s]

                # Shapley weight: |S|!(N-|S|-1)! / N!
                weight = (
                    math.factorial(len(s))
                    * math.factorial(n - len(s) - 1)
                    / math.factorial(n)
                )
                phi += weight * marginal

        shapley[i] = phi

    # Convert frozenset keys to strings for serialization
    coalition_str = {
        ",".join(sorted(k)) if k else "(empty)": v
        for k, v in coalition_values.items()
    }

    return ShapleyResult(
        values=shapley,
        coalition_values=coalition_str,
        n_coalitions=len(coalition_values),
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/ablation/test_shapley.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ablation/shapley.py engine/tests/ablation/test_shapley.py
git commit -m "feat(engine): add exact Shapley value calculator for filter decomposition"
```

---

## Task 7: Full ablation study orchestrator

**Files:**
- Create: `engine/src/margin_engine/ablation/study.py`
- Test: `engine/tests/ablation/test_study.py`

This task ties together the runner, detection, bootstrap, and Shapley modules into a single `AblationStudy` that executes all phases and produces an `InterferenceReport`.

**Step 1: Write the failing test**

```python
# engine/tests/ablation/test_study.py
"""Tests for the full ablation study orchestrator."""

from datetime import date

import numpy as np

from margin_engine.ablation.study import AblationStudy, StudyReport
from margin_engine.ablation.runner import AblationConfig
from margin_engine.backtesting.factor_registry import FactorRegistry

from tests.backtesting.helpers import build_pit_provider_with_tickers


def test_full_study_produces_report():
    """A complete ablation study should produce a StudyReport."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN"],
        start=date(2020, 1, 1),
        end=date(2020, 6, 1),
    )
    config = AblationConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 6, 1),
    )

    study = AblationStudy(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
    )
    report = study.run()

    assert isinstance(report, StudyReport)
    assert len(report.single_baselines) == 7  # control + 6
    assert len(report.pairwise_results) == 15
    assert len(report.incremental_stacks) >= 1
    assert report.interference is not None
    assert report.shapley_values is not None


def test_study_report_has_recommendations():
    """StudyReport should include action recommendations per filter."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT"],
        start=date(2020, 1, 1),
        end=date(2020, 4, 1),
    )
    config = AblationConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 4, 1),
    )

    study = AblationStudy(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
    )
    report = study.run()

    assert isinstance(report.recommendations, dict)
    # Should have a recommendation for each filter
    for f in ["liquidity", "beneish_m_score", "altman_z_score",
              "fcf_distress", "interest_coverage", "current_ratio"]:
        assert f in report.recommendations
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/ablation/test_study.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.ablation.study'`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/ablation/study.py
"""Full ablation study orchestrator.

Ties together the runner, detection, bootstrap, and Shapley modules
into a single workflow that executes all phases and produces an
InterferenceReport with action recommendations.
"""

from __future__ import annotations

from datetime import date

import numpy as np
from pydantic import BaseModel, Field

from margin_engine.ablation.bootstrap import bootstrap_sharpe_difference
from margin_engine.ablation.detection import (
    InterferenceReport,
    detect_degradation,
    detect_negative_marginal,
    detect_pairwise_destruction,
    detect_universe_collapse,
    compute_failure_correlation,
)
from margin_engine.ablation.runner import (
    ALL_FILTER_NAMES,
    AblationConfig,
    AblationResult,
    AblationRunner,
    FilterCombination,
)
from margin_engine.ablation.shapley import ShapleyResult, compute_shapley_values
from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.pit_provider import PointInTimeProvider


class StudyReport(BaseModel):
    """Complete ablation study output."""

    single_baselines: list[AblationResult]
    pairwise_results: list[AblationResult]
    incremental_stacks: dict[str, list[AblationResult]]
    full_stack: AblationResult | None = None
    interference: InterferenceReport
    shapley_values: ShapleyResult | None = None
    failure_correlations: dict[str, dict[str, float]] = Field(default_factory=dict)
    recommendations: dict[str, str] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class AblationStudy:
    """Executes the full 4-phase ablation study."""

    def __init__(
        self,
        config: AblationConfig,
        pit_provider: PointInTimeProvider,
        factor_registry: FactorRegistry,
        benchmark_prices: dict[date, float] | None = None,
        bootstrap_resamples: int = 1000,
    ) -> None:
        self._runner = AblationRunner(
            config=config,
            pit_provider=pit_provider,
            factor_registry=factor_registry,
            benchmark_prices=benchmark_prices,
        )
        self._bootstrap_n = bootstrap_resamples

    def run(self) -> StudyReport:
        """Execute all phases and produce the study report."""

        # Phase 1: Single-filter baselines
        single_baselines = self._runner.run_single_filter_baselines()

        # Phase 2: Pairwise combinations
        pairwise_results = self._runner.run_pairwise_combinations()

        # Phase 3: Incremental stacking (4 orderings)
        stacks = {}
        # Default order
        stacks["default"] = self._runner.run_incremental_stack()
        # Reverse order
        stacks["reverse"] = self._runner.run_incremental_stack(
            order=list(reversed([
                "liquidity", "beneish_m_score", "altman_z_score",
                "fcf_distress", "interest_coverage", "current_ratio",
            ]))
        )
        # Best-first order (sorted by single-filter Sharpe descending)
        single_sharpes = {
            r.combination.enabled_filters.copy().pop(): r.metrics.sharpe_ratio
            for r in single_baselines[1:]  # skip control
        }
        best_first = sorted(single_sharpes, key=single_sharpes.get, reverse=True)
        stacks["best_first"] = self._runner.run_incremental_stack(order=best_first)
        # Worst-first order
        stacks["worst_first"] = self._runner.run_incremental_stack(
            order=list(reversed(best_first))
        )

        # Full stack result (last entry of default stack)
        full_stack = stacks["default"][-1] if stacks["default"] else None

        # Phase 4: Shapley values using cached backtest results
        # Build value function from pairwise + single results
        cached_values: dict[frozenset[str], float] = {}

        # Control (empty)
        cached_values[frozenset()] = single_baselines[0].metrics.sharpe_ratio

        # Singles
        for r in single_baselines[1:]:
            cached_values[frozenset(r.combination.enabled_filters)] = r.metrics.sharpe_ratio

        # Pairs
        for r in pairwise_results:
            cached_values[frozenset(r.combination.enabled_filters)] = r.metrics.sharpe_ratio

        # Full stack
        if full_stack:
            cached_values[frozenset(ALL_FILTER_NAMES)] = full_stack.metrics.sharpe_ratio

        def value_fn(enabled: frozenset[str]) -> float:
            if enabled in cached_values:
                return cached_values[enabled]
            # Run missing coalitions on demand
            combo = FilterCombination(
                name=",".join(sorted(enabled)),
                enabled_filters=set(enabled),
            )
            result = self._runner.run_combination(combo)
            cached_values[enabled] = result.metrics.sharpe_ratio
            return result.metrics.sharpe_ratio

        shapley = compute_shapley_values(sorted(ALL_FILTER_NAMES), value_fn)

        # Detection tests
        full_sharpe = full_stack.metrics.sharpe_ratio if full_stack else 0.0

        degradation = detect_degradation(full_sharpe, single_sharpes)

        default_stack = stacks["default"]
        stack_sharpes = [r.metrics.sharpe_ratio for r in default_stack]
        filter_order = [
            "liquidity", "beneish_m_score", "altman_z_score",
            "fcf_distress", "interest_coverage", "current_ratio",
        ]
        negative_marginals = detect_negative_marginal(stack_sharpes, filter_order)

        pair_sharpes = {}
        for r in pairwise_results:
            filters = sorted(r.combination.enabled_filters)
            pair_sharpes[(filters[0], filters[1])] = r.metrics.sharpe_ratio
        destructive = detect_pairwise_destruction(single_sharpes, pair_sharpes)

        interference = InterferenceReport(
            degradation=degradation,
            negative_marginals=negative_marginals,
            destructive_pairs=destructive,
        )

        # Recommendations
        recommendations = self._generate_recommendations(
            shapley, interference, single_sharpes
        )

        return StudyReport(
            single_baselines=single_baselines,
            pairwise_results=pairwise_results,
            incremental_stacks=stacks,
            full_stack=full_stack,
            interference=interference,
            shapley_values=shapley,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        shapley: ShapleyResult,
        interference: InterferenceReport,
        single_sharpes: dict[str, float],
    ) -> dict[str, str]:
        """Apply the decision framework to produce per-filter recommendations."""
        recs: dict[str, str] = {}

        neg_names = {n.filter_name for n in interference.negative_marginals}
        destructive_filters = set()
        for d in interference.destructive_pairs:
            destructive_filters.add(d.filter_a)
            destructive_filters.add(d.filter_b)

        shapley_values = shapley.values
        if shapley_values:
            median_sv = sorted(shapley_values.values())[len(shapley_values) // 2]
        else:
            median_sv = 0.0

        for f in sorted(ALL_FILTER_NAMES):
            sv = shapley_values.get(f, 0.0)
            is_negative_marginal = f in neg_names
            is_destructive = f in destructive_filters
            is_low_shapley = sv < median_sv

            if is_negative_marginal and is_low_shapley:
                recs[f] = "remove"
            elif is_destructive and sv > 0:
                recs[f] = "merge"
            elif is_negative_marginal and sv > 0:
                recs[f] = "convert_to_scoring_input"
            else:
                recs[f] = "retain"

        return recs
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/ablation/test_study.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ablation/study.py engine/tests/ablation/test_study.py
git commit -m "feat(engine): add full ablation study orchestrator with recommendations"
```

---

## Task 8: Test helper for synthetic PIT data

**Files:**
- Create or modify: `engine/tests/backtesting/helpers.py`
- Test: `engine/tests/backtesting/test_helpers.py`

This task creates the `build_pit_provider_with_tickers` helper used by Tasks 2, 4, and 7. If `helpers.py` already exists, add the function; otherwise create it.

**Step 1: Write the failing test**

```python
# engine/tests/backtesting/test_helpers.py
"""Tests for backtesting test helpers."""

from datetime import date

from tests.backtesting.helpers import build_pit_provider_with_tickers


def test_build_provider_returns_correct_universe_size():
    """Provider should return snapshots for all requested tickers."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT", "GOOGL"],
        start=date(2020, 1, 1),
        end=date(2020, 3, 1),
    )
    universe = provider.get_universe(date(2020, 2, 1))
    assert len(universe) == 3
    tickers = {s.ticker for s in universe}
    assert tickers == {"AAPL", "MSFT", "GOOGL"}


def test_build_provider_snapshots_have_valid_financials():
    """Each snapshot should have populated AssetProfile and FinancialPeriod."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL"],
        start=date(2020, 1, 1),
        end=date(2020, 2, 1),
    )
    universe = provider.get_universe(date(2020, 1, 15))
    assert len(universe) == 1
    snap = universe[0]
    assert snap.profile.market_cap > 0
    assert snap.profile.sector is not None
    assert snap.period.current_income is not None
    assert snap.price > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_helpers.py -v`
Expected: FAIL (either module not found or function not found)

**Step 3: Write minimal implementation**

Check `engine/tests/backtesting/` for existing helpers first. Create the function that builds an `InMemoryPITProvider` with synthetic but filter-passable financial data for each ticker. Use realistic values (market cap > $10B, positive gross profit, reasonable ratios) so the elimination filters don't reject everything — this is critical for the ablation tests to produce meaningful survivor counts.

```python
# engine/tests/backtesting/helpers.py
"""Test helpers for backtesting modules."""

from __future__ import annotations

from datetime import date

from margin_engine.backtesting.pit_provider import InMemoryPITProvider
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)

# Synthetic profiles: large-cap, healthy companies that should pass filters
_TICKER_PROFILES = {
    "AAPL": ("Technology", 3_000_000_000_000, 100_000_000, 190.0),
    "MSFT": ("Technology", 2_800_000_000_000, 80_000_000, 380.0),
    "GOOGL": ("Technology", 2_000_000_000_000, 60_000_000, 140.0),
    "AMZN": ("Consumer Discretionary", 1_800_000_000_000, 50_000_000, 180.0),
    "META": ("Technology", 1_200_000_000_000, 40_000_000, 500.0),
    "JNJ": ("Health Care", 400_000_000_000, 20_000_000, 155.0),
    "XOM": ("Energy", 500_000_000_000, 30_000_000, 105.0),
    "PG": ("Consumer Staples", 380_000_000_000, 15_000_000, 160.0),
}


def build_pit_provider_with_tickers(
    tickers: list[str],
    start: date,
    end: date,
    monthly_return: float = 0.005,
) -> InMemoryPITProvider:
    """Build an InMemoryPITProvider with synthetic financial data.

    Each ticker gets a monthly snapshot from start to end with plausible
    financials designed to pass all 6 elimination filters.
    """
    provider = InMemoryPITProvider()

    current = date(start.year, start.month, 1)
    month_idx = 0

    while current <= end:
        for ticker in tickers:
            sector, market_cap, volume, base_price = _TICKER_PROFILES.get(
                ticker, ("Technology", 500_000_000_000, 20_000_000, 100.0)
            )

            price = base_price * (1 + monthly_return) ** month_idx
            revenue = market_cap * 0.15  # ~15% revenue/market_cap
            gross_profit = revenue * 0.45
            net_income = revenue * 0.20
            ebit = revenue * 0.25

            profile = AssetProfile(
                ticker=ticker,
                sector=sector,
                market_cap=market_cap,
                avg_daily_dollar_volume=volume,
                years_of_history=20,
                shares_outstanding=int(market_cap / price),
            )

            income = IncomeStatement(
                revenue=revenue,
                cost_of_revenue=revenue - gross_profit,
                gross_profit=gross_profit,
                operating_income=ebit,
                ebit=ebit,
                net_income=net_income,
                interest_expense=revenue * 0.02,
                depreciation=revenue * 0.03,
                sga=revenue * 0.10,
                research_and_development=revenue * 0.08,
            )

            balance = BalanceSheet(
                total_assets=market_cap * 0.5,
                current_assets=market_cap * 0.15,
                current_liabilities=market_cap * 0.10,
                total_liabilities=market_cap * 0.25,
                stockholders_equity=market_cap * 0.25,
                retained_earnings=market_cap * 0.20,
                total_receivables=revenue * 0.10,
                inventory=revenue * 0.05,
                cash_and_equivalents=market_cap * 0.05,
            )

            cashflow = CashFlowStatement(
                operating_cash_flow=net_income * 1.2,
                capital_expenditures=revenue * 0.05,
                free_cash_flow=net_income * 1.2 - revenue * 0.05,
            )

            period = FinancialPeriod(
                current_income=income,
                current_balance=balance,
                current_cashflow=cashflow,
                prior_income=income,  # Same as current for simplicity
                prior_balance=balance,
            )

            provider.add_snapshot(
                as_of_date=current,
                ticker=ticker,
                profile=profile,
                period=period,
                price=price,
            )

        # Advance to next month
        month = current.month + 1
        year = current.year
        if month > 12:
            month = 1
            year += 1
        current = date(year, month, 1)
        month_idx += 1

    return provider
```

Note: The exact field names on `IncomeStatement`, `BalanceSheet`, `CashFlowStatement`, and `AssetProfile` depend on the actual model definitions. Check `engine/src/margin_engine/models/financial.py` for the correct field names and adjust accordingly. The key requirement is that the synthetic data produces companies that **pass** all 6 elimination filters (large market cap, positive EBIT, strong current ratio, etc.).

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_helpers.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add engine/tests/backtesting/helpers.py engine/tests/backtesting/test_helpers.py
git commit -m "test(engine): add synthetic PIT data helper for ablation study tests"
```

---

## Task 9: CLI command to run the ablation study

**Files:**
- Modify: `api/src/margin_api/cli.py`
- Test: `api/tests/test_cli_ablation.py`

**Step 1: Write the failing test**

```python
# api/tests/test_cli_ablation.py
"""Tests for the ablation study CLI command."""

from click.testing import CliRunner

from margin_api.cli import cli


def test_ablation_command_exists():
    """The 'ablation' command should be registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["ablation", "--help"])
    assert result.exit_code == 0
    assert "ablation" in result.output.lower() or "interference" in result.output.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_cli_ablation.py -v`
Expected: FAIL — no such command 'ablation'

**Step 3: Write minimal implementation**

Add a new `ablation` command to the CLI that:
1. Accepts `--start-date`, `--end-date`, `--output` options
2. Constructs an `AblationStudy` using the DB-backed PIT provider (or synthetic for now)
3. Runs the study and prints a summary
4. Optionally saves the full report as JSON

Check `api/src/margin_api/cli.py` for the existing CLI structure and follow the same patterns (Click group, decorators, etc.).

```python
@cli.command()
@click.option("--start-date", default="2015-01-01", help="Backtest start date (YYYY-MM-DD)")
@click.option("--end-date", default=None, help="Backtest end date (default: today)")
@click.option("--output", default=None, help="Path to save JSON report")
@click.option("--bootstrap-n", default=1000, help="Bootstrap resamples (default: 1000)")
def ablation(start_date: str, end_date: str | None, output: str | None, bootstrap_n: int):
    """Run metric interference ablation study on the filter architecture."""
    from datetime import date as date_cls
    from margin_engine.ablation.runner import AblationConfig
    from margin_engine.ablation.study import AblationStudy
    from margin_engine.backtesting.factor_registry import FactorRegistry

    # Parse dates
    start = date_cls.fromisoformat(start_date)
    end = date_cls.fromisoformat(end_date) if end_date else date_cls.today()

    config = AblationConfig(start_date=start, end_date=end)

    click.echo(f"Running ablation study: {start} to {end}")
    click.echo(f"Bootstrap resamples: {bootstrap_n}")

    # For now, use synthetic provider. When real PIT data is available,
    # wire to DB-backed provider.
    from tests.backtesting.helpers import build_pit_provider_with_tickers
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "META", "JNJ", "XOM", "PG"],
        start=start,
        end=end,
    )

    study = AblationStudy(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
        bootstrap_resamples=bootstrap_n,
    )
    report = study.run()

    # Print summary
    click.echo("\n=== Ablation Study Results ===\n")

    click.echo("Single-filter Sharpe ratios:")
    for r in report.single_baselines:
        click.echo(f"  {r.combination.name:30s}  Sharpe={r.metrics.sharpe_ratio:.4f}")

    click.echo(f"\nFull stack Sharpe: {report.full_stack.metrics.sharpe_ratio:.4f}" if report.full_stack else "")

    if report.interference.degradation:
        d = report.interference.degradation
        click.echo(f"\nDegradation detected: {'YES' if d.detected else 'NO'}")
        click.echo(f"  Best single: {d.best_single} (Sharpe={d.best_single_sharpe:.4f})")

    click.echo("\nShapley values:")
    if report.shapley_values:
        for name, val in sorted(report.shapley_values.values.items(), key=lambda x: -x[1]):
            click.echo(f"  {name:25s}  φ={val:+.4f}")

    click.echo("\nRecommendations:")
    for name, action in sorted(report.recommendations.items()):
        click.echo(f"  {name:25s}  → {action}")

    if output:
        import json
        with open(output, "w") as f:
            json.dump(report.model_dump(), f, indent=2, default=str)
        click.echo(f"\nFull report saved to {output}")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_cli_ablation.py -v`
Expected: PASS

**Step 5: Run existing CLI tests**

Run: `uv run pytest api/tests/test_cli*.py -v`
Expected: All existing tests pass

**Step 6: Commit**

```bash
git add api/src/margin_api/cli.py api/tests/test_cli_ablation.py
git commit -m "feat(api): add 'ablation' CLI command for metric interference study"
```

---

## Task 10: Integration test — full ablation study end-to-end

**Files:**
- Create: `engine/tests/ablation/test_integration.py`

**Step 1: Write the integration test**

```python
# engine/tests/ablation/test_integration.py
"""End-to-end integration test for the ablation study framework."""

from datetime import date

from margin_engine.ablation.runner import AblationConfig, ALL_FILTER_NAMES
from margin_engine.ablation.study import AblationStudy
from margin_engine.backtesting.factor_registry import FactorRegistry

from tests.backtesting.helpers import build_pit_provider_with_tickers


def test_ablation_study_end_to_end():
    """Full ablation study runs without error and produces coherent results."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        start=date(2019, 1, 1),
        end=date(2020, 6, 1),
    )
    config = AblationConfig(
        start_date=date(2019, 1, 1),
        end_date=date(2020, 6, 1),
    )

    study = AblationStudy(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
        bootstrap_resamples=100,  # Low for speed in tests
    )
    report = study.run()

    # Phase 1 checks
    assert len(report.single_baselines) == 7
    control = report.single_baselines[0]
    assert control.combination.name == "control"

    # Phase 2 checks
    assert len(report.pairwise_results) == 15

    # Phase 3 checks
    assert "default" in report.incremental_stacks
    assert "reverse" in report.incremental_stacks
    assert "best_first" in report.incremental_stacks
    assert "worst_first" in report.incremental_stacks
    for stack in report.incremental_stacks.values():
        assert len(stack) == 7  # 0 filters through 6 filters

    # Phase 4 checks (Shapley)
    assert report.shapley_values is not None
    assert len(report.shapley_values.values) == 6
    # Shapley efficiency: values sum to v(N) - v(empty)
    total_sv = sum(report.shapley_values.values.values())
    grand = report.full_stack.metrics.sharpe_ratio if report.full_stack else 0.0
    empty = control.metrics.sharpe_ratio
    assert abs(total_sv - (grand - empty)) < 0.01  # Allow small float error

    # Detection checks
    assert report.interference is not None
    assert report.interference.degradation is not None

    # Recommendation checks
    assert len(report.recommendations) == 6
    valid_actions = {"retain", "remove", "merge", "convert_to_scoring_input"}
    for action in report.recommendations.values():
        assert action in valid_actions


def test_ablation_preserves_determinism():
    """Running the same study twice should produce identical results."""
    provider = build_pit_provider_with_tickers(
        tickers=["AAPL", "MSFT"],
        start=date(2020, 1, 1),
        end=date(2020, 4, 1),
    )
    config = AblationConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 4, 1),
    )

    study1 = AblationStudy(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
        bootstrap_resamples=100,
    )
    study2 = AblationStudy(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
        bootstrap_resamples=100,
    )

    report1 = study1.run()
    report2 = study2.run()

    # Same Sharpe ratios
    for r1, r2 in zip(report1.single_baselines, report2.single_baselines):
        assert r1.metrics.sharpe_ratio == r2.metrics.sharpe_ratio

    # Same Shapley values
    if report1.shapley_values and report2.shapley_values:
        for f in ALL_FILTER_NAMES:
            assert abs(
                report1.shapley_values.values[f] - report2.shapley_values.values[f]
            ) < 1e-10

    # Same recommendations
    assert report1.recommendations == report2.recommendations
```

**Step 2: Run integration test**

Run: `uv run pytest engine/tests/ablation/test_integration.py -v`
Expected: 2 passed

**Step 3: Run full test suite**

Run: `uv run pytest engine/tests/ablation/ -v`
Expected: All ablation tests pass (bootstrap, runner, detection, shapley, study, integration)

Run: `uv run pytest engine/tests/ -v --timeout=120`
Expected: All engine tests pass (no regressions)

**Step 4: Commit**

```bash
git add engine/tests/ablation/test_integration.py
git commit -m "test(engine): add end-to-end integration test for ablation study framework"
```

---

## Dependency Graph

```
Task 8 (test helper) ──────────────────┐
                                        ├─→ Task 2 (orchestrator filter config)
Task 1 (pipeline mask) ────────────────┤
                                        ├─→ Task 4 (ablation runner)
Task 3 (bootstrap) ───────────────────┐│
                                       ├┤
Task 5 (detection) ───────────────────┤├─→ Task 7 (study orchestrator) ──→ Task 9 (CLI)
                                       ││                                        │
Task 6 (shapley) ─────────────────────┘│                                        │
                                        └──────────────────────────→ Task 10 (integration)
```

**Parallel groups:**
- **Group A (independent):** Tasks 1, 3, 5, 6, 8 — no dependencies between them
- **Group B (after Group A):** Tasks 2, 4 — depend on Task 1 and Task 8
- **Group C (after Group B):** Task 7 — depends on Tasks 3, 4, 5, 6
- **Group D (after Group C):** Tasks 9, 10 — depend on Task 7
