"""End-to-end integration test for the full scoring pipeline.

Exercises the complete chain: raw JSON -> engine models -> scoring -> CompositeScore,
using realistic Apple FY2024-like financial data.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from margin_api.schemas.scores import ScoreResponse
from margin_api.services.scoring import (
    build_asset_profile,
    build_financial_period,
    run_scoring_pipeline,
)
from margin_engine.models.scoring import CompositeScore

# ---------------------------------------------------------------------------
# Realistic Apple FY2024-like test data
# ---------------------------------------------------------------------------

INCOME = {
    "revenue": "391035000000",
    "costOfRevenue": "210352000000",
    "grossProfit": "180683000000",
    "ebit": "123216000000",
    "netIncome": "93736000000",
    "interestExpense": "3423000000",
    "incomeTaxExpense": "18679000000",
    "sharesOutstanding": 15_408_095_000,
}

BALANCE = {
    "totalAssets": "364980000000",
    "totalCurrentAssets": "152987000000",
    "cashAndCashEquivalents": "29943000000",
    "netReceivables": "66243000000",
    "totalLiabilities": "308030000000",
    "totalCurrentLiabilities": "176392000000",
    "longTermDebt": "96802000000",
    "totalStockholdersEquity": "56950000000",
    "retainedEarnings": "-214000000",
    "propertyPlantEquipmentNet": "44856000000",
    "sharesOutstanding": 15_408_095_000,
}

CASHFLOW = {
    "operatingCashFlow": "118254000000",
    "capitalExpenditure": "-9959000000",
    "dividendsPaid": "-15234000000",
    "commonStockRepurchased": "-94949000000",
    "commonStockIssued": "0",
}

PRIOR_INCOME = {
    "revenue": "383285000000",
    "costOfRevenue": "209717000000",
    "grossProfit": "173568000000",
    "ebit": "118658000000",
    "netIncome": "96995000000",
    "interestExpense": "3468000000",
    "incomeTaxExpense": "16741000000",
    "sharesOutstanding": 15_408_095_000,
}

PRIOR_BALANCE = {
    "totalAssets": "352755000000",
    "totalCurrentAssets": "143566000000",
    "cashAndCashEquivalents": "29965000000",
    "netReceivables": "60985000000",
    "totalLiabilities": "290020000000",
    "totalCurrentLiabilities": "145308000000",
    "longTermDebt": "95281000000",
    "totalStockholdersEquity": "62235000000",
    "retainedEarnings": "-214000000",
    "propertyPlantEquipmentNet": "42117000000",
    "sharesOutstanding": 15_408_095_000,
}

PRIOR_CASHFLOW = {
    "operatingCashFlow": "110543000000",
    "capitalExpenditure": "-11062000000",
    "dividendsPaid": "-14996000000",
    "commonStockRepurchased": "-77550000000",
    "commonStockIssued": "0",
}

VALID_CONVICTION_LEVELS = {"exceptional", "high", "medium", "none"}
VALID_SIGNALS = {"buy", "watch", "no_action", "hold", "sell", "urgent_sell"}


def _price_bars_raw(n_bars: int = 260) -> list[dict]:
    """Generate ~1 year of daily price bars with a slight uptrend."""
    bars = []
    base_date = datetime.date(2024, 9, 28)
    base_price = 170.0
    for i in range(n_bars):
        d = base_date - datetime.timedelta(days=n_bars - 1 - i)
        price = base_price + i * 0.1
        bars.append(
            {
                "date": d.isoformat(),
                "open": str(round(price - 0.5, 2)),
                "high": str(round(price + 1.0, 2)),
                "low": str(round(price - 1.0, 2)),
                "close": str(round(price, 2)),
                "volume": 50_000_000,
            }
        )
    return bars


def _earnings_raw() -> list[dict]:
    """Generate 4 quarters of earnings surprises."""
    return [
        {"quarter": "2024-Q1", "actual_eps": "2.18", "expected_eps": "2.10"},
        {"quarter": "2024-Q2", "actual_eps": "1.40", "expected_eps": "1.35"},
        {"quarter": "2024-Q3", "actual_eps": "1.46", "expected_eps": "1.39"},
        {"quarter": "2024-Q4", "actual_eps": "2.40", "expected_eps": "2.35"},
    ]


def _build_aapl_period():
    """Build a FinancialPeriod with Apple FY2024-like data including priors."""
    return build_financial_period(
        income_raw=INCOME,
        balance_raw=BALANCE,
        cashflow_raw=CASHFLOW,
        period_end="2024-09-28",
        filing_date="2024-11-01",
        prior_income_raw=PRIOR_INCOME,
        prior_balance_raw=PRIOR_BALANCE,
        prior_cashflow_raw=PRIOR_CASHFLOW,
    )


def _build_aapl_profile():
    """Build an AssetProfile for Apple."""
    return build_asset_profile(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Information Technology",
        market_cap=Decimal("3000000000000"),
        avg_daily_volume=Decimal("10000000000"),
        years_of_history=44,
    )


def _run_aapl_pipeline() -> CompositeScore:
    """Run the full scoring pipeline for Apple-like data."""
    period = _build_aapl_period()
    profile = _build_aapl_profile()
    return run_scoring_pipeline(
        ticker="AAPL",
        period=period,
        profile=profile,
        price_bars_raw=_price_bars_raw(),
        earnings_raw=_earnings_raw(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """End-to-end integration tests for the scoring pipeline."""

    def test_pipeline_produces_valid_composite_score(self):
        """Full pipeline with Apple-like data produces a valid CompositeScore."""
        composite = _run_aapl_pipeline()

        # Returns a CompositeScore instance
        assert isinstance(composite, CompositeScore)

        # Correct ticker
        assert composite.ticker == "AAPL"

        # composite_percentile in valid range
        assert 0.0 <= composite.composite_percentile <= 100.0

        # conviction_level is one of the valid values
        assert composite.conviction_level.value in VALID_CONVICTION_LEVELS

        # signal is one of the valid values
        assert composite.signal.value in VALID_SIGNALS

        # data_coverage between 0 and 1
        assert 0.0 <= composite.data_coverage <= 1.0

        # Quality factor: 5 sub_scores (without history), correct factor_name
        assert composite.quality.factor_name == "quality"
        assert len(composite.quality.sub_scores) == 5

        # Value factor: 4 sub_scores, correct factor_name
        assert composite.value.factor_name == "value"
        assert len(composite.value.sub_scores) == 4

        # Momentum factor: 2 real sub_scores (multi_horizon_momentum + SUE)
        assert composite.momentum.factor_name == "momentum"
        assert len(composite.momentum.sub_scores) == 2

        # All 6 elimination filters ran
        assert len(composite.filters_passed) == 6

    def test_score_detail_serializes_to_json(self):
        """CompositeScore can be serialized and reconstructed via ScoreResponse."""
        composite = _run_aapl_pipeline()

        # Convert engine model to API response, then dump to JSON-compatible dict
        response = ScoreResponse.from_engine(composite)
        detail = response.model_dump(mode="json")

        # Verify it's a dict
        assert isinstance(detail, dict)

        # Round-trip: reconstruct ScoreResponse from the dict
        reconstructed = ScoreResponse(**detail)

        # Verify key fields survive the round-trip
        assert reconstructed.ticker == "AAPL"
        assert reconstructed.composite_percentile == response.composite_percentile
        assert reconstructed.conviction_level == response.conviction_level
        assert reconstructed.signal == response.signal
        assert reconstructed.data_coverage == response.data_coverage
        assert len(reconstructed.quality.sub_scores) == 5
        assert len(reconstructed.value.sub_scores) == 4
        assert len(reconstructed.momentum.sub_scores) == 2
        assert len(reconstructed.filters_passed) == 6

    def test_pipeline_with_different_sectors(self):
        """Pipeline works with a Financials sector profile (e.g., JPM-like)."""
        period = _build_aapl_period()

        # Build a Financials-sector profile (JPM-like metadata)
        profile = build_asset_profile(
            ticker="JPM",
            name="JPMorgan Chase & Co.",
            sector="Financials",
            market_cap=Decimal("600000000000"),
            avg_daily_volume=Decimal("5000000000"),
            years_of_history=50,
        )

        composite = run_scoring_pipeline(
            ticker="JPM",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )

        # Should still produce a valid CompositeScore
        assert isinstance(composite, CompositeScore)
        assert composite.ticker == "JPM"
        assert 0.0 <= composite.composite_percentile <= 100.0
        assert composite.conviction_level.value in VALID_CONVICTION_LEVELS
        assert composite.signal.value in VALID_SIGNALS
        assert 0.0 <= composite.data_coverage <= 1.0
        assert len(composite.filters_passed) == 6
