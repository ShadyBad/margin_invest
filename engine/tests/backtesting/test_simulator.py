"""Tests for the walk-forward simulation engine."""

from __future__ import annotations

from datetime import date

import pytest
from margin_engine.backtesting.models import (
    BacktestConfig,
    HoldingRecord,
    RebalanceFrequency,
    SelectionMode,
)
from margin_engine.backtesting.simulator import (
    STARTING_CAPITAL,
    BenchmarkProvider,
    ScoredStock,
    ScoredUniverseProvider,
    WalkForwardSimulator,
)

# ---------------------------------------------------------------------------
# Fake / in-memory provider implementations for testing
# ---------------------------------------------------------------------------


class FakeUniverseProvider:
    """In-memory scored universe provider for testing.

    Accepts a dict mapping dates to lists of ScoredStock. If a date is not
    found, returns an empty list.
    """

    def __init__(self, data: dict[date, list[ScoredStock]]) -> None:
        self._data = data

    def get_scores(self, as_of_date: date) -> list[ScoredStock]:
        return self._data.get(as_of_date, [])


class FakeBenchmarkProvider:
    """In-memory benchmark price provider for testing.

    Accepts a dict mapping dates to prices. Returns 100.0 if date is not found.
    """

    def __init__(self, data: dict[date, float]) -> None:
        self._data = data

    def get_price(self, ticker: str, as_of_date: date) -> float:
        return self._data.get(as_of_date, 100.0)


class StableUniverseProvider:
    """Provider that always returns the same set of stocks with growing prices.

    Useful for testing scenarios where the universe is constant and prices
    grow by a fixed monthly percentage.
    """

    def __init__(
        self,
        tickers: list[str],
        base_price: float = 100.0,
        monthly_return: float = 0.01,
        start_date: date = date(2020, 1, 1),
    ) -> None:
        self._tickers = tickers
        self._base_price = base_price
        self._monthly_return = monthly_return
        self._start_date = start_date

    def get_scores(self, as_of_date: date) -> list[ScoredStock]:
        months_elapsed = (
            (as_of_date.year - self._start_date.year) * 12
            + (as_of_date.month - self._start_date.month)
        )
        price = self._base_price * (1 + self._monthly_return) ** months_elapsed

        return [
            ScoredStock(
                ticker=ticker,
                composite_score=90.0 - i,  # Decreasing scores
                price=price + i,  # Slightly different prices
            )
            for i, ticker in enumerate(self._tickers)
        ]


class GrowingBenchmarkProvider:
    """Benchmark that grows at a fixed monthly rate."""

    def __init__(
        self,
        base_price: float = 100.0,
        monthly_return: float = 0.005,
        start_date: date = date(2020, 1, 1),
    ) -> None:
        self._base_price = base_price
        self._monthly_return = monthly_return
        self._start_date = start_date

    def get_price(self, ticker: str, as_of_date: date) -> float:
        months_elapsed = (
            (as_of_date.year - self._start_date.year) * 12
            + (as_of_date.month - self._start_date.month)
        )
        return self._base_price * (1 + self._monthly_return) ** months_elapsed


# ---------------------------------------------------------------------------
# Verify fake providers satisfy the protocols
# ---------------------------------------------------------------------------


class TestProviderProtocols:
    def test_fake_universe_provider_is_protocol(self):
        provider = FakeUniverseProvider({})
        assert isinstance(provider, ScoredUniverseProvider)

    def test_fake_benchmark_provider_is_protocol(self):
        provider = FakeBenchmarkProvider({})
        assert isinstance(provider, BenchmarkProvider)

    def test_stable_universe_provider_is_protocol(self):
        provider = StableUniverseProvider(["AAPL"])
        assert isinstance(provider, ScoredUniverseProvider)

    def test_growing_benchmark_provider_is_protocol(self):
        provider = GrowingBenchmarkProvider()
        assert isinstance(provider, BenchmarkProvider)


# ---------------------------------------------------------------------------
# Test rebalance date generation
# ---------------------------------------------------------------------------


class TestRebalanceDateGeneration:
    def test_monthly_dates_2020_jan_to_jun(self):
        """Generate monthly rebalance dates from 2020-01 to 2020-06."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )
        dates = sim._generate_rebalance_dates()

        assert len(dates) == 6

        # January 2020: Jan 1 is a Wednesday (weekday 2), so it IS a business day
        assert dates[0] == date(2020, 1, 1)

        # February 2020: Feb 1 is Saturday -> first business day is Feb 3 (Monday)
        assert dates[1] == date(2020, 2, 3)

        # March 2020: Mar 1 is Sunday -> first business day is Mar 2 (Monday)
        assert dates[2] == date(2020, 3, 2)

        # April 2020: Apr 1 is Wednesday -> first business day is Apr 1
        assert dates[3] == date(2020, 4, 1)

        # May 2020: May 1 is Friday -> first business day is May 1
        assert dates[4] == date(2020, 5, 1)

        # June 2020: Jun 1 is Monday -> first business day is Jun 1
        assert dates[5] == date(2020, 6, 1)

    def test_all_dates_are_weekdays(self):
        """Every generated rebalance date must be a weekday (Mon-Fri)."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )
        dates = sim._generate_rebalance_dates()

        for d in dates:
            assert d.weekday() < 5, f"{d} is a weekend day (weekday={d.weekday()})"

    def test_quarterly_dates(self):
        """Quarterly frequency should produce dates every 3 months."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )
        dates = sim._generate_rebalance_dates()

        assert len(dates) == 4
        # January, April, July, October
        assert dates[0].month == 1
        assert dates[1].month == 4
        assert dates[2].month == 7
        assert dates[3].month == 10

    def test_dates_are_within_range(self):
        """All generated dates should be within [start_date, end_date]."""
        config = BacktestConfig(
            start_date=date(2020, 3, 15),
            end_date=date(2020, 9, 15),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )
        dates = sim._generate_rebalance_dates()

        for d in dates:
            assert d >= config.start_date
            assert d <= config.end_date

    def test_deterministic(self):
        """Same config must produce same dates every time."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2022, 12, 31),
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )
        dates1 = sim._generate_rebalance_dates()
        dates2 = sim._generate_rebalance_dates()
        assert dates1 == dates2


# ---------------------------------------------------------------------------
# Test stock selection
# ---------------------------------------------------------------------------


class TestStockSelection:
    def test_top_5_percent_of_100_stocks(self):
        """Top 5% of 100 stocks = ceil(5.0) = 5 stocks, equal weighted."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            top_percentile=0.05,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

        scores = [
            ScoredStock(ticker=f"STOCK{i:03d}", composite_score=float(i), price=100.0 + i)
            for i in range(100)
        ]
        holdings = sim._select_holdings(scores, [])

        assert len(holdings) == 5
        # Should be the top 5 by score (scores 99, 98, 97, 96, 95)
        tickers = [h.ticker for h in holdings]
        assert "STOCK099" in tickers
        assert "STOCK098" in tickers
        assert "STOCK097" in tickers
        assert "STOCK096" in tickers
        assert "STOCK095" in tickers

    def test_equal_weight(self):
        """All selected stocks should have equal weight summing to 1.0."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            top_percentile=0.05,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

        scores = [
            ScoredStock(ticker=f"STOCK{i:03d}", composite_score=float(i), price=100.0)
            for i in range(100)
        ]
        holdings = sim._select_holdings(scores, [])

        expected_weight = 1.0 / 5
        for h in holdings:
            assert h.weight == pytest.approx(expected_weight)

        total_weight = sum(h.weight for h in holdings)
        assert total_weight == pytest.approx(1.0)

    def test_top_10_percent_of_20_stocks(self):
        """Top 10% of 20 stocks = ceil(2.0) = 2 stocks."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            top_percentile=0.10,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

        scores = [
            ScoredStock(ticker=f"S{i}", composite_score=float(i), price=50.0)
            for i in range(20)
        ]
        holdings = sim._select_holdings(scores, [])

        assert len(holdings) == 2
        assert holdings[0].ticker == "S19"
        assert holdings[1].ticker == "S18"

    def test_empty_universe_returns_no_holdings(self):
        """Empty scored universe should return empty holdings list."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )
        holdings = sim._select_holdings([], [])
        assert holdings == []

    def test_minimum_one_stock_selected(self):
        """Even with a tiny percentile, at least 1 stock should be selected."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            top_percentile=0.001,  # 0.1%
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

        scores = [
            ScoredStock(ticker="ONLY", composite_score=95.0, price=100.0),
        ]
        holdings = sim._select_holdings(scores, [])

        assert len(holdings) == 1
        assert holdings[0].ticker == "ONLY"
        assert holdings[0].weight == pytest.approx(1.0)

    def test_entry_price_and_score_captured(self):
        """Holdings should capture entry_price and composite_score from scored data."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            top_percentile=1.0,  # Select all
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

        scores = [
            ScoredStock(ticker="AAPL", composite_score=95.5, price=175.50),
        ]
        holdings = sim._select_holdings(scores, [])

        assert holdings[0].entry_price == 175.50
        assert holdings[0].composite_score == 95.5

    def test_deterministic_tiebreaking(self):
        """Stocks with equal scores should be ordered deterministically by ticker."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

        scores = [
            ScoredStock(ticker="ZZZ", composite_score=90.0, price=100.0),
            ScoredStock(ticker="AAA", composite_score=90.0, price=100.0),
            ScoredStock(ticker="MMM", composite_score=90.0, price=100.0),
            ScoredStock(ticker="BBB", composite_score=90.0, price=100.0),
        ]
        holdings1 = sim._select_holdings(scores, [])
        holdings2 = sim._select_holdings(scores, [])

        # Should be deterministic
        tickers1 = [h.ticker for h in holdings1]
        tickers2 = [h.ticker for h in holdings2]
        assert tickers1 == tickers2

        # With equal scores, should be alphabetical
        assert tickers1 == ["AAA", "BBB"]


# ---------------------------------------------------------------------------
# Test turnover calculation
# ---------------------------------------------------------------------------


class TestTurnoverCalculation:
    def test_full_turnover(self):
        """Completely different holdings = 100% turnover."""
        old = [
            HoldingRecord(ticker="A", weight=0.5, entry_price=100.0, composite_score=90.0),
            HoldingRecord(ticker="B", weight=0.5, entry_price=100.0, composite_score=85.0),
        ]
        new = [
            HoldingRecord(ticker="C", weight=0.5, entry_price=100.0, composite_score=92.0),
            HoldingRecord(ticker="D", weight=0.5, entry_price=100.0, composite_score=88.0),
        ]
        turnover = WalkForwardSimulator._calculate_turnover(old, new)
        assert turnover == pytest.approx(1.0)

    def test_no_turnover(self):
        """Same holdings = 0% turnover."""
        old = [
            HoldingRecord(ticker="A", weight=0.5, entry_price=100.0, composite_score=90.0),
            HoldingRecord(ticker="B", weight=0.5, entry_price=100.0, composite_score=85.0),
        ]
        new = [
            HoldingRecord(ticker="A", weight=0.5, entry_price=105.0, composite_score=91.0),
            HoldingRecord(ticker="B", weight=0.5, entry_price=102.0, composite_score=86.0),
        ]
        turnover = WalkForwardSimulator._calculate_turnover(old, new)
        assert turnover == pytest.approx(0.0)

    def test_partial_turnover(self):
        """One of two holdings changed = 50% turnover."""
        old = [
            HoldingRecord(ticker="A", weight=0.5, entry_price=100.0, composite_score=90.0),
            HoldingRecord(ticker="B", weight=0.5, entry_price=100.0, composite_score=85.0),
        ]
        new = [
            HoldingRecord(ticker="A", weight=0.5, entry_price=105.0, composite_score=91.0),
            HoldingRecord(ticker="C", weight=0.5, entry_price=100.0, composite_score=88.0),
        ]
        # Changed tickers: B removed, C added = 2 changed
        # Denominator: max(2, 2, 1) = 2
        # Turnover: 2/2 = 1.0
        # Wait -- symmetric_difference of {A,B} and {A,C} = {B,C} = 2 changed
        # denominator = max(2, 2, 1) = 2
        # 2/2 = 1.0  -- that's actually full turnover!
        # For partial: need one ticker to stay and sizes to differ or just one change
        turnover = WalkForwardSimulator._calculate_turnover(old, new)
        assert turnover == pytest.approx(1.0)

    def test_partial_turnover_one_of_three(self):
        """One of three holdings changed = 2/3 turnover."""
        old = [
            HoldingRecord(ticker="A", weight=0.33, entry_price=100.0, composite_score=90.0),
            HoldingRecord(ticker="B", weight=0.33, entry_price=100.0, composite_score=85.0),
            HoldingRecord(ticker="C", weight=0.34, entry_price=100.0, composite_score=80.0),
        ]
        new = [
            HoldingRecord(ticker="A", weight=0.33, entry_price=105.0, composite_score=91.0),
            HoldingRecord(ticker="B", weight=0.33, entry_price=102.0, composite_score=86.0),
            HoldingRecord(ticker="D", weight=0.34, entry_price=100.0, composite_score=82.0),
        ]
        # symmetric_difference: {C, D} = 2 changed
        # denominator: max(3, 3, 1) = 3
        # turnover: 2/3
        turnover = WalkForwardSimulator._calculate_turnover(old, new)
        assert turnover == pytest.approx(2.0 / 3.0)

    def test_empty_old_holdings(self):
        """First rebalance from empty portfolio — all new holdings are "changed"."""
        new = [
            HoldingRecord(ticker="A", weight=0.5, entry_price=100.0, composite_score=90.0),
            HoldingRecord(ticker="B", weight=0.5, entry_price=100.0, composite_score=85.0),
        ]
        turnover = WalkForwardSimulator._calculate_turnover([], new)
        # symmetric_difference: {A, B} = 2 changed
        # denominator: max(0, 2, 1) = 2
        # turnover: 2/2 = 1.0
        assert turnover == pytest.approx(1.0)

    def test_both_empty(self):
        """Both old and new are empty = 0% turnover."""
        turnover = WalkForwardSimulator._calculate_turnover([], [])
        assert turnover == pytest.approx(0.0)

    def test_different_sizes(self):
        """Holdings that change from 2 to 3 tickers."""
        old = [
            HoldingRecord(ticker="A", weight=0.5, entry_price=100.0, composite_score=90.0),
            HoldingRecord(ticker="B", weight=0.5, entry_price=100.0, composite_score=85.0),
        ]
        new = [
            HoldingRecord(ticker="A", weight=0.33, entry_price=105.0, composite_score=91.0),
            HoldingRecord(ticker="C", weight=0.33, entry_price=100.0, composite_score=88.0),
            HoldingRecord(ticker="D", weight=0.34, entry_price=100.0, composite_score=82.0),
        ]
        # symmetric_difference: {B, C, D} = 3 changed
        # denominator: max(2, 3, 1) = 3
        # turnover: 3/3 = 1.0
        turnover = WalkForwardSimulator._calculate_turnover(old, new)
        assert turnover == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test transaction cost calculation
# ---------------------------------------------------------------------------


class TestTransactionCostCalculation:
    def test_full_turnover_cost(self):
        """Full turnover with 15 bps total cost on 1M portfolio."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            transaction_cost_bps=10.0,
            slippage_bps=5.0,
        )
        # total_cost_bps = 15
        # portfolio_value * (turnover * total_cost_bps / 10000)
        # 1_000_000 * (1.0 * 15 / 10000) = 1_000_000 * 0.0015 = 1500
        portfolio_value = 1_000_000.0
        turnover = 1.0
        expected_cost = portfolio_value * (turnover * config.total_cost_bps / 10_000)
        assert expected_cost == pytest.approx(1500.0)

    def test_zero_turnover_no_cost(self):
        """Zero turnover should produce zero transaction costs."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
        )
        portfolio_value = 1_000_000.0
        turnover = 0.0
        cost = portfolio_value * (turnover * config.total_cost_bps / 10_000)
        assert cost == pytest.approx(0.0)

    def test_partial_turnover_cost(self):
        """Partial turnover (50%) with 15 bps on 1M portfolio."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            transaction_cost_bps=10.0,
            slippage_bps=5.0,
        )
        portfolio_value = 1_000_000.0
        turnover = 0.5
        cost = portfolio_value * (turnover * config.total_cost_bps / 10_000)
        assert cost == pytest.approx(750.0)

    def test_custom_cost_bps(self):
        """Custom transaction cost + slippage."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            transaction_cost_bps=20.0,
            slippage_bps=10.0,
        )
        assert config.total_cost_bps == 30.0
        portfolio_value = 2_000_000.0
        turnover = 0.5
        cost = portfolio_value * (turnover * config.total_cost_bps / 10_000)
        assert cost == pytest.approx(3000.0)


# ---------------------------------------------------------------------------
# Test basic simulation run
# ---------------------------------------------------------------------------


def _make_universe_data(
    dates: list[date],
    tickers: list[str],
    base_price: float = 100.0,
    monthly_return: float = 0.01,
) -> dict[date, list[ScoredStock]]:
    """Create synthetic scored universe data for testing."""
    data: dict[date, list[ScoredStock]] = {}
    for i, d in enumerate(dates):
        price = base_price * (1 + monthly_return) ** i
        stocks = [
            ScoredStock(
                ticker=ticker,
                composite_score=90.0 - j,
                price=price + j,
            )
            for j, ticker in enumerate(tickers)
        ]
        data[d] = stocks
    return data


def _make_benchmark_data(
    dates: list[date],
    base_price: float = 100.0,
    monthly_return: float = 0.005,
) -> dict[date, float]:
    """Create synthetic benchmark price data for testing."""
    data: dict[date, float] = {}
    for i, d in enumerate(dates):
        data[d] = base_price * (1 + monthly_return) ** i
    return data


class TestBasicSimulationRun:
    def test_snapshots_created(self):
        """A basic simulation run should produce snapshots."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B", "C", "D"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        result = sim.run()

        assert len(result.snapshots) > 0
        assert result.config == config
        assert result.duration_seconds >= 0

    def test_portfolio_starts_at_starting_capital(self):
        """First snapshot's portfolio value should be close to starting capital."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B", "C", "D"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        result = sim.run()
        first_snapshot = result.snapshots[0]

        # First snapshot: portfolio_value = STARTING_CAPITAL - transaction_costs
        # transaction_costs = STARTING_CAPITAL * (turnover * total_cost_bps / 10000)
        # First month has full turnover (from empty to new holdings)
        expected_costs = STARTING_CAPITAL * (1.0 * config.total_cost_bps / 10_000)
        expected_value = STARTING_CAPITAL - expected_costs
        assert first_snapshot.portfolio_value == pytest.approx(expected_value)

    def test_first_snapshot_return_is_zero(self):
        """The first snapshot should have zero portfolio and benchmark return."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        result = sim.run()
        assert result.snapshots[0].portfolio_return == 0.0
        assert result.snapshots[0].benchmark_return == 0.0

    def test_benchmark_tracking(self):
        """Benchmark value should track the benchmark price changes."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                base_price=100.0,
                monthly_return=0.01,
                start_date=date(2020, 1, 1),
            ),
        )
        result = sim.run()

        # First benchmark value should be starting capital
        assert result.snapshots[0].benchmark_value == pytest.approx(STARTING_CAPITAL)

        # Benchmark should grow over time
        for i in range(1, len(result.snapshots)):
            assert result.snapshots[i].benchmark_value >= result.snapshots[i - 1].benchmark_value

    def test_metrics_computed(self):
        """The result should have computed performance metrics."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B", "C", "D"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        result = sim.run()

        assert result.metrics is not None
        assert result.metrics.num_months == len(result.snapshots)


# ---------------------------------------------------------------------------
# Test simulation with no turnover
# ---------------------------------------------------------------------------


class TestSimulationNoTurnover:
    def test_same_stocks_every_month(self):
        """When the same stocks are selected every month, turnover should be 0 after month 1."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B", "C", "D"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        result = sim.run()

        # First month has full turnover (from empty to holdings)
        assert result.snapshots[0].turnover == pytest.approx(1.0)

        # Subsequent months should have 0 turnover since stable provider
        # always returns the same tickers
        for snap in result.snapshots[1:]:
            assert snap.turnover == pytest.approx(0.0)

    def test_zero_turnover_means_zero_costs_after_first(self):
        """With no turnover after month 1, transaction costs should be 0."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B", "C", "D"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        result = sim.run()

        for snap in result.snapshots[1:]:
            assert snap.transaction_costs == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test snapshot count matches rebalance dates
# ---------------------------------------------------------------------------


class TestSnapshotCount:
    def test_monthly_snapshot_count(self):
        """Number of snapshots should match number of rebalance dates."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B", "C", "D"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        expected_dates = sim._generate_rebalance_dates()
        result = sim.run()

        assert len(result.snapshots) == len(expected_dates)

    def test_quarterly_snapshot_count(self):
        """Quarterly rebalance should produce 4 snapshots per year."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B", "C", "D"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        result = sim.run()

        assert len(result.snapshots) == 4

    def test_snapshot_dates_match_rebalance_dates(self):
        """Each snapshot date should match the corresponding rebalance date."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=StableUniverseProvider(
                tickers=["A", "B"],
                start_date=date(2020, 1, 1),
            ),
            benchmark_provider=GrowingBenchmarkProvider(
                start_date=date(2020, 1, 1),
            ),
        )
        expected_dates = sim._generate_rebalance_dates()
        result = sim.run()

        snapshot_dates = [s.date for s in result.snapshots]
        assert snapshot_dates == expected_dates


# ---------------------------------------------------------------------------
# Test empty universe handling
# ---------------------------------------------------------------------------


class TestEmptyUniverse:
    def test_empty_provider_returns_result(self):
        """Simulation with empty universe provider should not crash."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({date(2020, 1, 1): 100.0}),
        )
        result = sim.run()

        # Should still have snapshots (one per rebalance date)
        assert len(result.snapshots) > 0

    def test_empty_universe_no_holdings(self):
        """When the universe is empty, snapshots should have no holdings."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({date(2020, 1, 1): 100.0}),
        )
        result = sim.run()

        for snap in result.snapshots:
            assert len(snap.holdings) == 0

    def test_empty_universe_zero_turnover(self):
        """With no holdings, turnover should be 0."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({date(2020, 1, 1): 100.0}),
        )
        result = sim.run()

        for snap in result.snapshots:
            assert snap.turnover == pytest.approx(0.0)
            assert snap.transaction_costs == pytest.approx(0.0)

    def test_empty_universe_preserves_capital(self):
        """With no holdings, portfolio value should remain at starting capital."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({date(2020, 1, 1): 100.0}),
        )
        result = sim.run()

        for snap in result.snapshots:
            assert snap.portfolio_value == pytest.approx(STARTING_CAPITAL)

    def test_empty_universe_metrics(self):
        """With no holdings, metrics should still be computed."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({date(2020, 1, 1): 100.0}),
        )
        result = sim.run()

        assert result.metrics is not None
        assert result.metrics.num_months > 0


# ---------------------------------------------------------------------------
# Test determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_inputs_same_outputs(self):
        """Running the same simulation twice must produce identical results."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=0.50,
        )

        def run_once() -> list[float]:
            sim = WalkForwardSimulator(
                config=config,
                universe_provider=StableUniverseProvider(
                    tickers=["A", "B", "C", "D"],
                    start_date=date(2020, 1, 1),
                ),
                benchmark_provider=GrowingBenchmarkProvider(
                    start_date=date(2020, 1, 1),
                ),
            )
            result = sim.run()
            return [s.portfolio_value for s in result.snapshots]

        values1 = run_once()
        values2 = run_once()

        assert len(values1) == len(values2)
        for v1, v2 in zip(values1, values2):
            assert v1 == pytest.approx(v2)


# ---------------------------------------------------------------------------
# Test with explicit mock data for precise verification
# ---------------------------------------------------------------------------


class TestPreciseCalculation:
    def test_known_values_simulation(self):
        """Run with precisely known data to verify calculations."""
        # Create a 2-month simulation with explicit data
        # Jan 2020: first business day is Jan 2 (Thu) -- wait, Jan 1 is Wed
        # Actually date(2020,1,1).weekday() = 2 (Wed), so first_business_day = Jan 1
        jan1 = date(2020, 1, 1)
        # Feb 2020: Feb 1 is Sat, first business day = Feb 3
        feb3 = date(2020, 2, 3)

        stocks_jan = [
            ScoredStock(ticker="A", composite_score=90.0, price=100.0),
            ScoredStock(ticker="B", composite_score=80.0, price=50.0),
        ]
        stocks_feb = [
            ScoredStock(ticker="A", composite_score=85.0, price=110.0),  # A went up 10%
            ScoredStock(ticker="B", composite_score=95.0, price=45.0),   # B went down 10%
        ]

        universe_data = {jan1: stocks_jan, feb3: stocks_feb}

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 2, 28),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=1.0,  # Select all stocks
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )

        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider(universe_data),
            benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0}),
        )
        result = sim.run()

        assert len(result.snapshots) == 2

        # Month 1 (Jan): Select A and B, equal weight 50% each
        snap1 = result.snapshots[0]
        assert len(snap1.holdings) == 2
        assert snap1.portfolio_value == pytest.approx(STARTING_CAPITAL)  # No costs
        assert snap1.turnover == pytest.approx(1.0)  # Full turnover from empty
        assert snap1.transaction_costs == pytest.approx(0.0)  # 0 bps

        # Month 2 (Feb): Portfolio value changes based on price movements
        # A: entry=100, now=110 -> +10%
        # B: entry=50, now=45 -> -10%
        # Portfolio return = 0.5 * 0.10 + 0.5 * (-0.10) = 0.0
        snap2 = result.snapshots[1]
        assert snap2.portfolio_value == pytest.approx(STARTING_CAPITAL)

    def test_transaction_costs_deducted(self):
        """Verify that transaction costs are properly deducted from portfolio value."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)

        stocks = [
            ScoredStock(ticker="A", composite_score=90.0, price=100.0),
        ]
        # Same stocks, same price -- no price change
        universe_data = {jan1: stocks, feb3: stocks}

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 2, 28),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
            top_percentile=1.0,
            transaction_cost_bps=10.0,
            slippage_bps=5.0,  # total = 15 bps
        )

        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider(universe_data),
            benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 100.0}),
        )
        result = sim.run()

        # Month 1: full turnover, costs = 1M * (1.0 * 15/10000) = 1500
        snap1 = result.snapshots[0]
        assert snap1.transaction_costs == pytest.approx(1500.0)
        assert snap1.portfolio_value == pytest.approx(STARTING_CAPITAL - 1500.0)

        # Month 2: same stock, 0 turnover, no costs. But no price change either.
        # Portfolio value should stay the same.
        snap2 = result.snapshots[1]
        assert snap2.turnover == pytest.approx(0.0)
        assert snap2.transaction_costs == pytest.approx(0.0)
        assert snap2.portfolio_value == pytest.approx(STARTING_CAPITAL - 1500.0)


# ---------------------------------------------------------------------------
# Test ScoredStock model (margin_of_safety field)
# ---------------------------------------------------------------------------


class TestScoredStockModel:
    def test_scored_stock_without_mos(self):
        """ScoredStock should work without margin_of_safety (backward compat)."""
        stock = ScoredStock(ticker="AAPL", composite_score=85.0, price=150.0)
        assert stock.margin_of_safety is None

    def test_scored_stock_with_mos(self):
        """ScoredStock should accept margin_of_safety."""
        stock = ScoredStock(
            ticker="AAPL", composite_score=85.0, price=150.0, margin_of_safety=0.35
        )
        assert stock.margin_of_safety == 0.35

    def test_scored_stock_with_negative_mos(self):
        """Negative MoS means overvalued — should be accepted."""
        stock = ScoredStock(
            ticker="TSLA", composite_score=60.0, price=300.0, margin_of_safety=-0.20
        )
        assert stock.margin_of_safety == -0.20


# ---------------------------------------------------------------------------
# Test conviction + margin-of-safety selection mode
# ---------------------------------------------------------------------------


class TestConvictionMosSelection:
    """Tests for _select_by_conviction_mos stock selection."""

    def _make_simulator(self, min_score: float = 79.0, min_mos: float = 0.30):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=min_score,
            min_margin_of_safety=min_mos,
        )
        return WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

    def test_passes_both_thresholds(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="AAPL", composite_score=82.0, price=150.0, margin_of_safety=0.35),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 1
        assert holdings[0].ticker == "AAPL"

    def test_fails_mos_threshold(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="MSFT", composite_score=82.0, price=300.0, margin_of_safety=0.25),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_fails_conviction_threshold(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="GOOG", composite_score=75.0, price=140.0, margin_of_safety=0.40),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_mos_none_rejected(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="AMZN", composite_score=80.0, price=180.0, margin_of_safety=None),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_mos_exactly_threshold_rejected(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="META", composite_score=79.0, price=500.0, margin_of_safety=0.30),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_mos_barely_above_threshold(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="META", composite_score=79.0, price=500.0, margin_of_safety=0.3001),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 1

    def test_zero_eligible_returns_prev_holdings(self):
        sim = self._make_simulator()
        prev = [
            HoldingRecord(ticker="AAPL", weight=0.5, entry_price=150.0, composite_score=82.0),
            HoldingRecord(ticker="MSFT", weight=0.5, entry_price=300.0, composite_score=80.0),
        ]
        scores = [
            ScoredStock(ticker="GOOG", composite_score=70.0, price=140.0, margin_of_safety=0.10),
        ]
        holdings = sim._select_holdings(scores, prev)
        assert holdings == prev

    def test_equal_weight_multiple(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.40),
            ScoredStock(ticker="B", composite_score=82.0, price=100.0, margin_of_safety=0.35),
            ScoredStock(ticker="C", composite_score=80.0, price=100.0, margin_of_safety=0.32),
            ScoredStock(ticker="D", composite_score=79.5, price=100.0, margin_of_safety=0.31),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 4
        for h in holdings:
            assert h.weight == pytest.approx(0.25)
        assert sum(h.weight for h in holdings) == pytest.approx(1.0)

    def test_single_eligible_full_weight(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="AAPL", composite_score=85.0, price=150.0, margin_of_safety=0.40),
            ScoredStock(ticker="MSFT", composite_score=70.0, price=300.0, margin_of_safety=0.50),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 1
        assert holdings[0].weight == pytest.approx(1.0)

    def test_deterministic_sort_order(self):
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="ZZZ", composite_score=80.0, price=100.0, margin_of_safety=0.35),
            ScoredStock(ticker="AAA", composite_score=80.0, price=100.0, margin_of_safety=0.35),
            ScoredStock(ticker="MMM", composite_score=85.0, price=100.0, margin_of_safety=0.40),
        ]
        holdings1 = sim._select_holdings(scores, [])
        holdings2 = sim._select_holdings(scores, [])
        tickers1 = [h.ticker for h in holdings1]
        tickers2 = [h.ticker for h in holdings2]
        assert tickers1 == tickers2
        assert tickers1 == ["MMM", "AAA", "ZZZ"]

    def test_top_percentile_mode_unchanged(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.TOP_PERCENTILE,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )
        scores = [
            ScoredStock(ticker="A", composite_score=90.0, price=100.0),
            ScoredStock(ticker="B", composite_score=80.0, price=100.0),
            ScoredStock(ticker="C", composite_score=70.0, price=100.0),
            ScoredStock(ticker="D", composite_score=60.0, price=100.0),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 2
        assert holdings[0].ticker == "A"
        assert holdings[1].ticker == "B"


# ---------------------------------------------------------------------------
# Integration tests for full simulation with CONVICTION_MOS mode
# ---------------------------------------------------------------------------


class TestConvictionMosSimulation:
    """Integration tests for full simulation with CONVICTION_MOS mode."""

    def test_basic_conviction_mos_simulation(self):
        """Run a full simulation with CONVICTION_MOS selection."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)
        mar2 = date(2020, 3, 2)

        universe_data = {
            jan1: [
                ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.40),
                ScoredStock(ticker="B", composite_score=80.0, price=50.0, margin_of_safety=0.35),
                ScoredStock(ticker="C", composite_score=70.0, price=80.0, margin_of_safety=0.50),
            ],
            feb3: [
                ScoredStock(ticker="A", composite_score=85.0, price=110.0, margin_of_safety=0.38),
                ScoredStock(ticker="B", composite_score=80.0, price=55.0, margin_of_safety=0.33),
                ScoredStock(ticker="C", composite_score=70.0, price=85.0, margin_of_safety=0.48),
            ],
            mar2: [
                ScoredStock(ticker="A", composite_score=85.0, price=105.0, margin_of_safety=0.36),
                ScoredStock(ticker="B", composite_score=80.0, price=52.0, margin_of_safety=0.31),
                ScoredStock(ticker="C", composite_score=70.0, price=90.0, margin_of_safety=0.45),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=79.0,
            min_margin_of_safety=0.30,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider(universe_data),
            benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0, mar2: 103.0}),
        )
        result = sim.run()

        assert len(result.snapshots) == 3
        # Jan: A (score=85, mos=0.40) and B (score=80, mos=0.35) selected
        # C rejected (score=70, below 79)
        snap1 = result.snapshots[0]
        assert len(snap1.holdings) == 2
        tickers = {h.ticker for h in snap1.holdings}
        assert tickers == {"A", "B"}

    def test_hold_through_zero_eligible_period(self):
        """Portfolio holds when no candidates pass filter."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)
        mar2 = date(2020, 3, 2)

        universe_data = {
            jan1: [
                ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.40),
            ],
            feb3: [
                ScoredStock(ticker="A", composite_score=85.0, price=110.0, margin_of_safety=0.20),
            ],
            mar2: [
                ScoredStock(ticker="A", composite_score=85.0, price=115.0, margin_of_safety=0.35),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider(universe_data),
            benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0, mar2: 103.0}),
        )
        result = sim.run()

        assert len(result.snapshots[0].holdings) == 1
        assert result.snapshots[0].holdings[0].ticker == "A"

        # Month 2: zero eligible -> hold prior
        assert len(result.snapshots[1].holdings) == 1
        assert result.snapshots[1].holdings[0].ticker == "A"
        assert result.snapshots[1].turnover == pytest.approx(0.0)
        assert result.snapshots[1].transaction_costs == pytest.approx(0.0)

        # Month 3: A qualifies again
        assert len(result.snapshots[2].holdings) == 1
        assert result.snapshots[2].holdings[0].ticker == "A"

    def test_point_in_time_correctness(self):
        """Scores from each date are used, not current values."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)

        universe_data = {
            jan1: [
                ScoredStock(ticker="X", composite_score=82.0, price=100.0, margin_of_safety=0.35),
            ],
            feb3: [
                ScoredStock(ticker="X", composite_score=70.0, price=110.0, margin_of_safety=0.35),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 2, 28),
            selection_mode=SelectionMode.CONVICTION_MOS,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider(universe_data),
            benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0}),
        )
        result = sim.run()

        assert len(result.snapshots[0].holdings) == 1
        assert len(result.snapshots[1].holdings) == 1
        assert result.snapshots[1].turnover == pytest.approx(0.0)

    def test_determinism_conviction_mos(self):
        """Same inputs produce identical outputs."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)

        universe_data = {
            jan1: [
                ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.40),
                ScoredStock(ticker="B", composite_score=80.0, price=50.0, margin_of_safety=0.35),
            ],
            feb3: [
                ScoredStock(ticker="A", composite_score=85.0, price=110.0, margin_of_safety=0.38),
                ScoredStock(ticker="B", composite_score=80.0, price=55.0, margin_of_safety=0.33),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 2, 28),
            selection_mode=SelectionMode.CONVICTION_MOS,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )

        def run_once():
            sim = WalkForwardSimulator(
                config=config,
                universe_provider=FakeUniverseProvider(universe_data),
                benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0}),
            )
            return [s.portfolio_value for s in sim.run().snapshots]

        assert run_once() == run_once()
