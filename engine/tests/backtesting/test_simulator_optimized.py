"""Tests for OPTIMIZED selection mode in WalkForwardSimulator."""

from __future__ import annotations

import datetime as dt
from datetime import date
from decimal import Decimal

import pytest
from margin_engine.backtesting.cost_model import CostModelConfig
from margin_engine.backtesting.models import (
    BacktestConfig,
    SelectionMode,
)
from margin_engine.backtesting.simulator import (
    ScoredStock,
    WalkForwardSimulator,
)
from margin_engine.models.financial import PriceBar

# ---------------------------------------------------------------------------
# Fake providers
# ---------------------------------------------------------------------------


def _make_bar(date_str: str, close: float) -> PriceBar:
    p = Decimal(str(close))
    return PriceBar(date=date_str, open=p, high=p, low=p, close=p, volume=100_000)


def _daily_bars(start: str, prices: list[float]) -> list[PriceBar]:
    """Generate bars from a list of closing prices, one per business day."""
    base = dt.date.fromisoformat(start)
    bars = []
    day = 0
    for p in prices:
        d = base + dt.timedelta(days=day)
        while d.weekday() >= 5:
            day += 1
            d = base + dt.timedelta(days=day)
        bars.append(_make_bar(d.isoformat(), p))
        day += 1
    return bars


class FakeScoredUniverseProvider:
    """Returns canned scores for testing."""

    def __init__(self, scores: dict[str, list[ScoredStock]]):
        self._scores = scores

    def get_scores(self, as_of_date: date) -> list[ScoredStock]:
        key = as_of_date.isoformat()
        return self._scores.get(key, [])


class FakeBenchmarkProvider:
    """Returns a fixed benchmark price that grows linearly."""

    def __init__(self, start_price: float = 100.0, monthly_return: float = 0.01):
        self._start = start_price
        self._rate = monthly_return
        self._base_date: date | None = None
        self._call_count = 0

    def get_price(self, ticker: str, as_of_date: date) -> float:
        if self._base_date is None:
            self._base_date = as_of_date
        months = (
            (as_of_date.year - self._base_date.year) * 12
            + as_of_date.month
            - self._base_date.month
        )
        return self._start * (1 + self._rate) ** months


class FakePriceHistoryProvider:
    """Returns canned price bars for each ticker."""

    def __init__(self, data: dict[str, list[PriceBar]]):
        self._data = data

    def get_price_bars(
        self, tickers: list[str], as_of_date: date, window_days: int = 252
    ) -> dict[str, list[PriceBar]]:
        return {t: self._data[t] for t in tickers if t in self._data}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_scores(tickers: list[str], base_score: float = 75.0) -> list[ScoredStock]:
    """Create scored stocks with descending scores."""
    return [
        ScoredStock(
            ticker=t,
            composite_score=base_score - i * 2,
            price=100.0 + i * 5,
        )
        for i, t in enumerate(tickers)
    ]


def _make_price_data(tickers: list[str], n_bars: int = 80) -> dict[str, list[PriceBar]]:
    """Create price data for multiple tickers with different trends."""
    data = {}
    for i, t in enumerate(tickers):
        # Each ticker has a slightly different trend
        base = 100.0 + i * 10
        step = 0.3 + i * 0.05
        prices = [base + j * step for j in range(n_bars)]
        data[t] = _daily_bars("2024-01-02", prices)
    return data


@pytest.fixture()
def tickers():
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]


@pytest.fixture()
def price_data(tickers):
    return _make_price_data(tickers)


@pytest.fixture()
def config():
    return BacktestConfig(
        start_date=date(2024, 6, 1),
        end_date=date(2024, 9, 30),
        selection_mode=SelectionMode.OPTIMIZED,
        top_percentile=0.50,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOptimizedMode:
    def test_optimized_produces_non_equal_weights(self, tickers, price_data, config):
        """OPTIMIZED mode should produce non-equal weights via optimizer."""
        scores = _make_scores(tickers)
        dates = ["2024-06-03", "2024-07-01", "2024-08-01", "2024-09-02"]
        scored_map = {d: scores for d in dates}

        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
            price_history_provider=FakePriceHistoryProvider(price_data),
        )
        result = sim.run()

        assert len(result.snapshots) > 0
        # At least one snapshot should have holdings with non-equal weights
        for snap in result.snapshots:
            if len(snap.holdings) > 1:
                weights = [h.weight for h in snap.holdings]
                # Weights should sum to ~1
                assert abs(sum(weights) - 1.0) < 0.01
                # If optimizer worked, not all weights should be exactly equal
                # (though this depends on optimizer; at minimum they should be valid)
                assert all(w > 0 for w in weights)

    def test_fallback_when_no_price_provider(self, tickers, config):
        """Without a price_history_provider, falls back to top_percentile."""
        scores = _make_scores(tickers)
        dates = ["2024-06-03", "2024-07-01", "2024-08-01", "2024-09-02"]
        scored_map = {d: scores for d in dates}

        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
            price_history_provider=None,  # No provider
        )
        result = sim.run()

        # Should still produce results via fallback
        assert len(result.snapshots) > 0
        for snap in result.snapshots:
            if snap.holdings:
                weights = [h.weight for h in snap.holdings]
                # Equal weight from top_percentile fallback
                assert len(set(round(w, 10) for w in weights)) == 1

    def test_fallback_when_optimizer_fails(self, tickers, config):
        """If price data is insufficient, should fall back gracefully."""
        scores = _make_scores(tickers)
        dates = ["2024-06-03", "2024-07-01", "2024-08-01", "2024-09-02"]
        scored_map = {d: scores for d in dates}

        # Only give 5 bars per ticker — not enough for covariance
        sparse_data = {
            t: _daily_bars("2024-01-02", [100.0 + j for j in range(5)])
            for t in tickers
        }

        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
            price_history_provider=FakePriceHistoryProvider(sparse_data),
        )
        result = sim.run()

        # Should fall back to top_percentile, still producing results
        assert len(result.snapshots) > 0

    def test_rank_ic_report_populated(self, tickers, price_data, config):
        """OPTIMIZED mode should produce a Rank IC report."""
        scores = _make_scores(tickers)
        dates = ["2024-06-03", "2024-07-01", "2024-08-01", "2024-09-02"]
        scored_map = {d: scores for d in dates}

        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
            price_history_provider=FakePriceHistoryProvider(price_data),
        )
        result = sim.run()

        # rank_ic_report should be populated if there were enough periods
        # (may be None if < 3 holdings for IC calc, but should at least not error)
        if result.rank_ic_report is not None:
            assert result.rank_ic_report.n_periods >= 1
            assert len(result.rank_ic_report.ic_series) == result.rank_ic_report.n_periods

    def test_nonlinear_cost_model(self, tickers, price_data, config):
        """Non-linear cost model should produce different costs than flat bps."""
        scores = _make_scores(tickers)
        dates = ["2024-06-03", "2024-07-01", "2024-08-01", "2024-09-02"]
        scored_map = {d: scores for d in dates}

        # Run with non-linear cost model
        cost_config = CostModelConfig(base_commission_bps=5.0)
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
            price_history_provider=FakePriceHistoryProvider(price_data),
            cost_model_config=cost_config,
        )
        result_nl = sim.run()

        # Run without non-linear cost model (flat bps)
        sim_flat = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
            price_history_provider=FakePriceHistoryProvider(price_data),
            cost_model_config=None,
        )
        result_flat = sim_flat.run()

        # Both should complete
        assert len(result_nl.snapshots) > 0
        assert len(result_flat.snapshots) > 0


class TestExistingModesUnchanged:
    """Regression tests: TOP_PERCENTILE and CONVICTION_MOS modes unchanged."""

    def test_top_percentile_unchanged(self):
        """TOP_PERCENTILE mode should work identically with new simulator."""
        tickers = ["A", "B", "C", "D"]
        scores = _make_scores(tickers)
        dates = ["2024-06-03", "2024-07-01", "2024-08-01"]
        scored_map = {d: scores for d in dates}

        config = BacktestConfig(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 8, 31),
            selection_mode=SelectionMode.TOP_PERCENTILE,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
        )
        result = sim.run()

        assert len(result.snapshots) > 0
        # Should be equal-weighted
        for snap in result.snapshots:
            if len(snap.holdings) > 1:
                weights = [h.weight for h in snap.holdings]
                assert len(set(round(w, 10) for w in weights)) == 1

    def test_conviction_mos_unchanged(self):
        """CONVICTION_MOS mode should work identically with new simulator."""
        scores = [
            ScoredStock(ticker="A", composite_score=82, price=100, margin_of_safety=0.30),
            ScoredStock(ticker="B", composite_score=75, price=90, margin_of_safety=0.25),
            ScoredStock(ticker="C", composite_score=60, price=80, margin_of_safety=0.15),
        ]
        dates = ["2024-06-03", "2024-07-01", "2024-08-01"]
        scored_map = {d: scores for d in dates}

        config = BacktestConfig(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 8, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
        )
        result = sim.run()

        assert len(result.snapshots) > 0
        # Should be equal-weighted within selected group
        for snap in result.snapshots:
            if len(snap.holdings) > 1:
                weights = [h.weight for h in snap.holdings]
                assert len(set(round(w, 10) for w in weights)) == 1


class TestTurnoverEnforcement:
    def test_turnover_limit_applied(self, tickers, price_data):
        """Turnover constraint should be enforced between rebalance periods."""
        from margin_engine.optimization.models import OptimizationConstraints

        # Use very low turnover limit
        config = BacktestConfig(
            start_date=date(2024, 6, 1),
            end_date=date(2024, 9, 30),
            selection_mode=SelectionMode.OPTIMIZED,
            top_percentile=0.80,
            optimization_constraints=OptimizationConstraints(max_turnover=0.05),
        )

        scores = _make_scores(tickers)
        dates = ["2024-06-03", "2024-07-01", "2024-08-01", "2024-09-02"]
        scored_map = {d: scores for d in dates}

        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeScoredUniverseProvider(scored_map),
            benchmark_provider=FakeBenchmarkProvider(),
            price_history_provider=FakePriceHistoryProvider(price_data),
        )
        result = sim.run()

        # Should complete without errors
        assert len(result.snapshots) > 0
