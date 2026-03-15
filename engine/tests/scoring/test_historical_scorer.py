"""Tests for the historical_scorer module — PIT-based universe scoring."""

from __future__ import annotations

from margin_engine.scoring.historical_scorer import score_universe_at_date


def _make_snapshot(
    ticker: str,
    period_end: str,
    *,
    revenue: float = 1_000_000_000,
    gross_profit: float = 400_000_000,
    ebit: float = 200_000_000,
    net_income: float = 150_000_000,
    total_assets: float = 5_000_000_000,
    total_equity: float = 2_000_000_000,
    total_liabilities: float = 3_000_000_000,
    current_assets: float = 1_000_000_000,
    current_liabilities: float = 500_000_000,
    operating_cash_flow: float = 250_000_000,
    capital_expenditures: float = -50_000_000,
    sector: str = "Information Technology",
    market_cap: float = 10_000_000_000,
    shares_outstanding: int | None = 1_000_000,
    filing_date: str = "2024-03-15",
) -> dict:
    """Build a minimal PIT snapshot dict for testing."""
    return {
        "ticker": ticker,
        "period_end": period_end,
        "filing_date": filing_date,
        "income_statement": {
            "revenue": revenue,
            "grossProfit": gross_profit,
            "costOfRevenue": revenue - gross_profit,
            "ebit": ebit,
            "netIncome": net_income,
        },
        "balance_sheet": {
            "totalAssets": total_assets,
            "totalStockholdersEquity": total_equity,
            "totalLiabilities": total_liabilities,
            "totalCurrentAssets": current_assets,
            "totalCurrentLiabilities": current_liabilities,
        },
        "cash_flow": {
            "operatingCashFlow": operating_cash_flow,
            "capitalExpenditure": capital_expenditures,
        },
        "sector": sector,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
    }


def _make_price_bars(ticker: str, n: int = 260) -> list[dict]:
    """Build minimal daily price bars (1 year of trading days)."""
    bars = []
    base = 100.0
    for i in range(n):
        day = f"2024-{((i // 28) % 12) + 1:02d}-{(i % 28) + 1:02d}"
        price = base + i * 0.1
        bars.append(
            {
                "ticker": ticker,
                "date": day,
                "close": price,
                "open": price - 0.5,
                "high": price + 0.5,
                "low": price - 1.0,
                "volume": 1_000_000,
            }
        )
    return bars


class TestReturnsCompositeScores:
    """test_returns_composite_scores — 2 tickers -> 2 CompositeScore results."""

    def test_returns_composite_scores(self) -> None:
        snapshots = [
            _make_snapshot("AAPL", "2024-09-28"),
            _make_snapshot("MSFT", "2024-09-28", revenue=2_000_000_000),
        ]
        prices = {
            "AAPL": _make_price_bars("AAPL"),
            "MSFT": _make_price_bars("MSFT"),
        }
        active = {"AAPL", "MSFT"}

        results = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date="2024-12-31",
            active_tickers=active,
        )

        assert len(results) == 2
        tickers = {r.ticker for r in results}
        assert tickers == {"AAPL", "MSFT"}

        for r in results:
            assert r.quality is not None
            assert r.value is not None
            assert r.momentum is not None
            assert 0.0 <= r.composite_percentile <= 100.0
            assert 0.0 <= r.composite_raw_score <= 100.0
            assert 0.0 <= r.data_coverage <= 1.0


class TestFiltersByActiveTickers:
    """test_filters_by_active_tickers — delisted ticker excluded."""

    def test_filters_by_active_tickers(self) -> None:
        snapshots = [
            _make_snapshot("AAPL", "2024-09-28"),
            _make_snapshot("DEAD", "2024-09-28"),  # delisted
        ]
        prices = {
            "AAPL": _make_price_bars("AAPL"),
            "DEAD": _make_price_bars("DEAD"),
        }
        # Only AAPL is active — DEAD should be excluded
        active = {"AAPL"}

        results = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date="2024-12-31",
            active_tickers=active,
        )

        assert len(results) == 1
        assert results[0].ticker == "AAPL"


class TestDeterministicOutput:
    """test_deterministic_output — same inputs -> same scores."""

    def test_deterministic_output(self) -> None:
        snapshots = [
            _make_snapshot("AAPL", "2024-09-28"),
            _make_snapshot("MSFT", "2024-09-28", revenue=2_000_000_000),
        ]
        prices = {
            "AAPL": _make_price_bars("AAPL"),
            "MSFT": _make_price_bars("MSFT"),
        }
        active = {"AAPL", "MSFT"}

        results1 = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date="2024-12-31",
            active_tickers=active,
        )
        results2 = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date="2024-12-31",
            active_tickers=active,
        )

        # Sort both by ticker for stable comparison
        results1.sort(key=lambda r: r.ticker)
        results2.sort(key=lambda r: r.ticker)

        for r1, r2 in zip(results1, results2):
            assert r1.ticker == r2.ticker
            assert r1.composite_raw_score == r2.composite_raw_score
            assert r1.composite_percentile == r2.composite_percentile
            assert r1.data_coverage == r2.data_coverage


class TestEmptySnapshotsReturnsEmpty:
    """test_empty_snapshots_returns_empty."""

    def test_empty_snapshots_returns_empty(self) -> None:
        results = score_universe_at_date(
            pit_snapshots=[],
            pit_prices={},
            rebalance_date="2024-12-31",
            active_tickers=set(),
        )
        assert results == []

    def test_no_active_tickers_returns_empty(self) -> None:
        snapshots = [_make_snapshot("AAPL", "2024-09-28")]
        prices = {"AAPL": _make_price_bars("AAPL")}

        results = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date="2024-12-31",
            active_tickers=set(),
        )
        assert results == []


class TestScoresIncludeGrowthFactors:
    """test_scores_include_growth_factors — multi-period history -> growth breakdown exists."""

    def test_scores_include_growth_factors(self) -> None:
        # Two periods for the same ticker -> FinancialHistory with 2 periods
        snapshots = [
            _make_snapshot(
                "AAPL",
                "2023-09-28",
                filing_date="2023-11-01",
                revenue=800_000_000,
            ),
            _make_snapshot(
                "AAPL",
                "2024-09-28",
                filing_date="2024-11-01",
                revenue=1_000_000_000,
            ),
        ]
        prices = {"AAPL": _make_price_bars("AAPL")}
        active = {"AAPL"}

        results = score_universe_at_date(
            pit_snapshots=snapshots,
            pit_prices=prices,
            rebalance_date="2024-12-31",
            active_tickers=active,
        )

        assert len(results) == 1
        composite = results[0]
        assert composite.ticker == "AAPL"

        # With multi-period history, quality should have 7 sub-scores
        # (5 base + roic_trend + gross_margin_stability)
        quality_names = [s.name for s in composite.quality.sub_scores]
        assert "roic_trend" in quality_names
        assert "gross_margin_stability" in quality_names

        # Momentum should include sentiment stub
        momentum_names = [s.name for s in composite.momentum.sub_scores]
        assert "sentiment" in momentum_names
        assert "multi_horizon_momentum" in momentum_names

        # Growth breakdown should exist (revenue_cagr, incremental_roic, rule_of_40, runway_score)
        assert composite.growth is not None
        growth_names = [s.name for s in composite.growth.sub_scores]
        assert "revenue_cagr" in growth_names
        assert "incremental_roic" in growth_names
        assert "runway_score" in growth_names
