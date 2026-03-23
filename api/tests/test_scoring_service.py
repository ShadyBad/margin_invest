"""Tests for the scoring service (engine-to-DB bridge).

Tests build_financial_period, build_asset_profile, and run_scoring_pipeline
using realistic Apple-like financial data.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from margin_api.services.scoring import (
    INVERTED_FACTORS,
    build_asset_profile,
    build_financial_history_from_rows,
    build_financial_period,
    compute_raw_factor_scores,
    rank_and_compute_composites,
    run_scoring_pipeline,
)
from margin_engine.models.financial import (
    AssetProfile,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
)
from margin_engine.models.scoring import CompositeScore, FactorScore

# ---------------------------------------------------------------------------
# Test data helpers — Apple-like numbers (FY2024)
# ---------------------------------------------------------------------------


def _income_raw(
    revenue: str = "391035000000",
    cost_of_revenue: str = "214137000000",
    gross_profit: str = "176898000000",
    ebit: str = "123216000000",
    net_income: str = "100913000000",
    interest_expense: str = "3933000000",
    tax_provision: str = "18679000000",
    shares_outstanding: int = 15408095000,
) -> dict:
    return {
        "revenue": revenue,
        "costOfRevenue": cost_of_revenue,
        "grossProfit": gross_profit,
        "ebit": ebit,
        "netIncome": net_income,
        "interestExpense": interest_expense,
        "incomeTaxExpense": tax_provision,
        "sharesOutstanding": shares_outstanding,
    }


def _balance_raw(
    total_assets: str = "352583000000",
    current_assets: str = "152987000000",
    cash: str = "29965000000",
    receivables: str = "66243000000",
    total_liabilities: str = "290437000000",
    current_liabilities: str = "176392000000",
    long_term_debt: str = "96807000000",
    total_equity: str = "62146000000",
    retained_earnings: str = "-214000000",
    pp_and_e: str = "44856000000",
    shares_outstanding: int = 15408095000,
) -> dict:
    return {
        "totalAssets": total_assets,
        "totalCurrentAssets": current_assets,
        "cashAndCashEquivalents": cash,
        "netReceivables": receivables,
        "totalLiabilities": total_liabilities,
        "totalCurrentLiabilities": current_liabilities,
        "longTermDebt": long_term_debt,
        "totalStockholdersEquity": total_equity,
        "retainedEarnings": retained_earnings,
        "propertyPlantEquipmentNet": pp_and_e,
        "sharesOutstanding": shares_outstanding,
    }


def _cashflow_raw(
    operating_cf: str = "118254000000",
    capex: str = "-9959000000",
    dividends: str = "-15025000000",
    repurchases: str = "-94949000000",
    issuance: str = "0",
) -> dict:
    return {
        "operatingCashFlow": operating_cf,
        "capitalExpenditure": capex,
        "dividendsPaid": dividends,
        "commonStockRepurchased": repurchases,
        "commonStockIssued": issuance,
    }


def _prior_income_raw() -> dict:
    return _income_raw(
        revenue="383285000000",
        cost_of_revenue="209717000000",
        gross_profit="173568000000",
        ebit="118658000000",
        net_income="96995000000",
        interest_expense="3468000000",
        tax_provision="16741000000",
    )


def _prior_balance_raw() -> dict:
    return _balance_raw(
        total_assets="352755000000",
        current_assets="143566000000",
        cash="29965000000",
        receivables="60985000000",
        total_liabilities="290020000000",
        current_liabilities="145308000000",
        long_term_debt="95281000000",
        total_equity="62235000000",
    )


def _prior_cashflow_raw() -> dict:
    return _cashflow_raw(
        operating_cf="110543000000",
        capex="-11062000000",
        dividends="-14996000000",
        repurchases="-77550000000",
    )


def _price_bars_raw(n_bars: int = 260) -> list[dict]:
    """Generate ~1 year of daily price bars with a slight uptrend."""
    bars = []
    base_date = datetime.date(2024, 9, 28)
    base_price = 170.0
    for i in range(n_bars):
        d = base_date - datetime.timedelta(days=n_bars - 1 - i)
        # Small uptrend: +0.1 per day on average
        price = base_price + i * 0.1
        bars.append(
            {
                "date": d.isoformat(),
                "open": str(round(price - 0.5, 2)),
                "high": str(round(price + 1.0, 2)),
                "low": str(round(price - 1.0, 2)),
                "close": str(round(price, 2)),
                "volume": 50000000,
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildFinancialPeriod:
    """Tests for build_financial_period."""

    def test_returns_valid_financial_period(self):
        period = build_financial_period(
            income_raw=_income_raw(),
            balance_raw=_balance_raw(),
            cashflow_raw=_cashflow_raw(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        assert isinstance(period, FinancialPeriod)
        assert period.period_end == "2024-09-28"
        assert period.filing_date == "2024-11-01"

    def test_income_statement_fields(self):
        period = build_financial_period(
            income_raw=_income_raw(),
            balance_raw=_balance_raw(),
            cashflow_raw=_cashflow_raw(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        assert period.current_income.revenue == Decimal("391035000000")
        assert period.current_income.gross_profit == Decimal("176898000000")
        assert period.current_income.net_income == Decimal("100913000000")

    def test_balance_sheet_fields(self):
        period = build_financial_period(
            income_raw=_income_raw(),
            balance_raw=_balance_raw(),
            cashflow_raw=_cashflow_raw(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        assert period.current_balance.total_assets == Decimal("352583000000")
        assert period.current_balance.total_equity == Decimal("62146000000")

    def test_cash_flow_fields(self):
        period = build_financial_period(
            income_raw=_income_raw(),
            balance_raw=_balance_raw(),
            cashflow_raw=_cashflow_raw(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        assert period.current_cash_flow.operating_cash_flow == Decimal("118254000000")
        assert period.current_cash_flow.capital_expenditures == Decimal("-9959000000")

    def test_with_prior_period(self):
        period = build_financial_period(
            income_raw=_income_raw(),
            balance_raw=_balance_raw(),
            cashflow_raw=_cashflow_raw(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
            prior_income_raw=_prior_income_raw(),
            prior_balance_raw=_prior_balance_raw(),
            prior_cashflow_raw=_prior_cashflow_raw(),
        )
        assert period.prior_income is not None
        assert period.prior_income.revenue == Decimal("383285000000")
        assert period.prior_balance is not None
        assert period.prior_cash_flow is not None

    def test_without_prior_period(self):
        period = build_financial_period(
            income_raw=_income_raw(),
            balance_raw=_balance_raw(),
            cashflow_raw=_cashflow_raw(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        assert period.prior_income is None
        assert period.prior_balance is None
        assert period.prior_cash_flow is None


class TestBuildAssetProfile:
    """Tests for build_asset_profile."""

    def test_returns_valid_asset_profile(self):
        profile = build_asset_profile(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3000000000000"),
        )
        assert isinstance(profile, AssetProfile)
        assert profile.ticker == "AAPL"
        assert profile.name == "Apple Inc."
        assert profile.sector == GICSSector.TECHNOLOGY
        assert profile.market_cap == Decimal("3000000000000")

    def test_sector_enum_conversion(self):
        """Test various sector strings map to correct GICSSector values."""
        test_cases = [
            ("Information Technology", GICSSector.TECHNOLOGY),
            ("Health Care", GICSSector.HEALTHCARE),
            ("Financials", GICSSector.FINANCIALS),
            ("Energy", GICSSector.ENERGY),
            ("Consumer Discretionary", GICSSector.CONSUMER_DISCRETIONARY),
            ("Consumer Staples", GICSSector.CONSUMER_STAPLES),
            ("Industrials", GICSSector.INDUSTRIALS),
            ("Materials", GICSSector.MATERIALS),
            ("Real Estate", GICSSector.REAL_ESTATE),
            ("Utilities", GICSSector.UTILITIES),
            ("Communication Services", GICSSector.COMMUNICATION_SERVICES),
        ]
        for sector_str, expected_enum in test_cases:
            profile = build_asset_profile(
                ticker="TEST",
                name="Test Co.",
                sector=sector_str,
                market_cap=Decimal("1000000000"),
            )
            assert profile.sector == expected_enum, (
                f"Sector '{sector_str}' did not map to {expected_enum}"
            )

    def test_invalid_sector_raises(self):
        """An invalid sector string should raise a ValueError."""
        with pytest.raises(ValueError, match="Unknown sector"):
            build_asset_profile(
                ticker="TEST",
                name="Test Co.",
                sector="Nonexistent Sector",
                market_cap=Decimal("1000000000"),
            )


class TestRunScoringPipeline:
    """Integration tests for run_scoring_pipeline."""

    def _build_period_with_priors(self) -> FinancialPeriod:
        return build_financial_period(
            income_raw=_income_raw(),
            balance_raw=_balance_raw(),
            cashflow_raw=_cashflow_raw(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
            prior_income_raw=_prior_income_raw(),
            prior_balance_raw=_prior_balance_raw(),
            prior_cashflow_raw=_prior_cashflow_raw(),
        )

    def _build_profile(self) -> AssetProfile:
        return build_asset_profile(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3000000000000"),
            avg_daily_volume=Decimal("10000000000"),
            years_of_history=44,
        )

    def test_returns_composite_score(self):
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        assert isinstance(result, CompositeScore)

    def test_correct_ticker(self):
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        assert result.ticker == "AAPL"

    def test_quality_factor_count(self):
        """Quality should have 5 sub-factors (without history)."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        assert len(result.quality.sub_scores) == 5
        quality_names = {s.name for s in result.quality.sub_scores}
        assert "gross_profitability" in quality_names
        assert "roic_wacc_spread" in quality_names
        assert "accrual_ratio" in quality_names
        assert "piotroski_f_score" in quality_names
        assert "fcf_conversion" in quality_names

    def test_value_factor_count(self):
        """Value should have 4 sub-factors."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        assert len(result.value.sub_scores) == 4
        value_names = {s.name for s in result.value.sub_scores}
        assert "ev_fcf" in value_names
        assert "shareholder_yield" in value_names
        assert "dcf_margin_of_safety" in value_names
        assert "acquirers_multiple" in value_names

    def test_momentum_factor_count(self):
        """Momentum has 2 sub-factors without sentiment (momentum + sue).

        Sentiment is only included when sentiment_value is passed to
        compute_raw_factor_scores(); the single-ticker pipeline omits it.
        """
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        assert len(result.momentum.sub_scores) == 2
        momentum_names = {s.name for s in result.momentum.sub_scores}
        assert "multi_horizon_momentum" in momentum_names
        assert "sue" in momentum_names

    def test_filters_populated(self):
        """Elimination filters should be populated with results."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        # Apple-like data should pass all filters
        assert len(result.filters_passed) > 0
        assert all(f.passed for f in result.filters_passed)

    def test_composite_percentile_valid_range(self):
        """Composite percentile should be between 0 and 100."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        assert 0.0 <= result.composite_percentile <= 100.0

    def test_data_coverage_valid(self):
        """Data coverage should be between 0 and 1."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        assert 0.0 <= result.data_coverage <= 1.0

    def test_growth_stage_assigned(self):
        """Growth stage should be assigned from the classifier."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        assert result.growth_stage is not None

    def test_all_factor_scores_valid(self):
        """Every sub-score should be a valid FactorScore with percentile 0-100."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        all_scores = (
            result.quality.sub_scores + result.value.sub_scores + result.momentum.sub_scores
        )
        for score in all_scores:
            assert isinstance(score, FactorScore)
            assert 0.0 <= score.percentile_rank <= 100.0
            assert score.name  # non-empty name


class TestNewFactorWiring:
    """Tests for new audit factors wired into the scoring pipeline."""

    def _build_period_with_priors(self) -> FinancialPeriod:
        return build_financial_period(
            income_raw=_income_raw(),
            balance_raw=_balance_raw(),
            cashflow_raw=_cashflow_raw(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
            prior_income_raw=_prior_income_raw(),
            prior_balance_raw=_prior_balance_raw(),
            prior_cashflow_raw=_prior_cashflow_raw(),
        )

    def _build_profile(self, shares_outstanding: int | None = None) -> AssetProfile:
        return build_asset_profile(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3000000000000"),
            avg_daily_volume=Decimal("10000000000"),
            years_of_history=44,
            shares_outstanding=shares_outstanding,
        )

    def _build_history(self) -> FinancialHistory:
        """Build a 3-year FinancialHistory for multi-period factors."""
        rows = []
        for year in (2022, 2023, 2024):
            rows.append(
                {
                    "period_end": f"{year}-09-28",
                    "filing_date": f"{year}-11-01",
                    "income_statement": _income_raw(),
                    "balance_sheet": _balance_raw(),
                    "cash_flow": _cashflow_raw(),
                }
            )
        return build_financial_history_from_rows("AAPL", rows)

    def test_quality_factors_with_history(self):
        """With history, quality should have 7 factors.

        Base 5 + roic_trend + gross_margin_stability.
        """
        period = self._build_period_with_priors()
        profile = self._build_profile()
        history = self._build_history()

        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
            history=history,
        )
        quality_names = {s.name for s in raw.quality_scores}
        assert len(raw.quality_scores) == 7
        assert "roic_trend" in quality_names
        assert "gross_margin_stability" in quality_names
        assert "fcf_conversion" in quality_names

    def test_quality_factors_without_history(self):
        """Without history, quality should have 5 factors.

        No roic_trend or gross_margin_stability.
        """
        period = self._build_period_with_priors()
        profile = self._build_profile()

        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
            history=None,
        )
        quality_names = {s.name for s in raw.quality_scores}
        assert len(raw.quality_scores) == 5
        assert "roic_trend" not in quality_names
        assert "gross_margin_stability" not in quality_names
        assert "fcf_conversion" in quality_names

    def test_scenario_iv_in_value_scores(self):
        """With shares_outstanding and positive FCF, scenario_iv should appear in value scores."""
        period = self._build_period_with_priors()
        profile = self._build_profile(shares_outstanding=15408095000)

        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        value_names = {s.name for s in raw.value_scores}
        assert "scenario_iv" in value_names
        assert len(raw.value_scores) == 5  # 4 base + scenario_iv

    def test_scenario_iv_absent_without_shares(self):
        """Without shares_outstanding, scenario_iv should not appear."""
        period = self._build_period_with_priors()
        profile = self._build_profile(shares_outstanding=None)

        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        value_names = {s.name for s in raw.value_scores}
        assert "scenario_iv" not in value_names
        assert len(raw.value_scores) == 4

    def test_multi_horizon_replaces_price_momentum(self):
        """Momentum should contain multi_horizon_momentum, not price_momentum."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        momentum_names = {s.name for s in raw.momentum_scores}
        assert "multi_horizon_momentum" in momentum_names
        assert "price_momentum" not in momentum_names

    def test_gross_margin_stability_inverted(self):
        """gross_margin_stability should be in INVERTED_FACTORS (lower CoV = better)."""
        assert "gross_margin_stability" in INVERTED_FACTORS

    def test_data_quality_gate_caps_conviction(self):
        """When data_coverage is low, the gate should cap composite_raw_score."""
        period = self._build_period_with_priors()
        profile = self._build_profile()

        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=[],  # No earnings data → lower data_coverage
        )
        composites = rank_and_compute_composites([raw])
        composite = composites[0]
        # With a single ticker, composite_raw_score is the weighted average.
        # The data_quality_gate only kicks in when data_coverage < 0.8.
        # With no earnings, data_coverage should be less than 1.0.
        # If gate triggered and downgraded, raw score should be capped.
        if composite.data_coverage < 0.80:
            assert composite.composite_raw_score <= 71.9
        else:
            # High coverage: gate doesn't apply, just check score is valid
            assert 0.0 <= composite.composite_raw_score <= 100.0

    def test_history_stored_on_raw_result(self):
        """The RawScoringResult should store the history passed to it."""
        period = self._build_period_with_priors()
        profile = self._build_profile()
        history = self._build_history()

        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
            history=history,
        )
        assert raw.history is history


class TestBuildFinancialHistory:
    def test_builds_history_from_multiple_periods(self):
        """Given multiple row dicts, build a FinancialHistory."""
        rows = [
            {
                "period_end": "2022-12-31",
                "filing_date": "2023-02-15",
                "income_statement": {
                    "revenue": 1000,
                    "cost_of_revenue": 600,
                    "gross_profit": 400,
                    "ebit": 200,
                    "net_income": 160,
                },
                "balance_sheet": {"total_assets": 1500, "total_equity": 500},
                "cash_flow": {
                    "operating_cash_flow": 250,
                    "capital_expenditures": -80,
                },
            },
            {
                "period_end": "2023-12-31",
                "filing_date": "2024-02-15",
                "income_statement": {
                    "revenue": 1200,
                    "cost_of_revenue": 700,
                    "gross_profit": 500,
                    "ebit": 250,
                    "net_income": 200,
                },
                "balance_sheet": {"total_assets": 1800, "total_equity": 600},
                "cash_flow": {
                    "operating_cash_flow": 300,
                    "capital_expenditures": -100,
                },
            },
        ]
        history = build_financial_history_from_rows("TEST", rows)
        assert history.ticker == "TEST"
        assert len(history.periods) == 2
        assert history.periods[0].period_end < history.periods[1].period_end

    def test_pairs_prior_period_data(self):
        """Second period should have prior_income, prior_balance, prior_cash_flow populated."""
        rows = [
            {
                "period_end": "2022-09-24",
                "filing_date": "2022-10-28",
                "income_statement": _prior_income_raw(),
                "balance_sheet": _prior_balance_raw(),
                "cash_flow": _prior_cashflow_raw(),
            },
            {
                "period_end": "2023-09-30",
                "filing_date": "2023-10-27",
                "income_statement": _income_raw(),
                "balance_sheet": _balance_raw(),
                "cash_flow": _cashflow_raw(),
            },
        ]
        history = build_financial_history_from_rows("AAPL", rows)
        assert len(history.periods) == 2

        # First period has no prior data
        first = history.periods[0]
        assert first.prior_income is None
        assert first.prior_balance is None
        assert first.prior_cash_flow is None

        # Second period has prior data populated from first period
        second = history.periods[1]
        assert second.prior_income is not None
        assert second.prior_balance is not None
        assert second.prior_cash_flow is not None

    def test_single_row_has_no_prior_data(self):
        """A single-row history should have no prior data."""
        rows = [
            {
                "period_end": "2023-09-30",
                "filing_date": "2023-10-27",
                "income_statement": _income_raw(),
                "balance_sheet": _balance_raw(),
                "cash_flow": _cashflow_raw(),
            },
        ]
        history = build_financial_history_from_rows("AAPL", rows)
        assert len(history.periods) == 1
        assert history.periods[0].prior_income is None
