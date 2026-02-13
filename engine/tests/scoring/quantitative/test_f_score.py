"""Tests for Piotroski F-Score quality factor."""

from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.f_score import (
    compute_f_score_signals,
    piotroski_f_score,
)


class TestAppleGolden:
    """Golden-value tests using Apple FY2024 10-K data."""

    def test_apple_f_score_golden(self):
        """Apple FY2024 Piotroski F-Score should be 6."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = piotroski_f_score(APPLE_PERIOD_2024)
        assert result.raw_value == 6

    def test_apple_signals(self):
        """Verify each individual Apple FY2024 signal matches expected values."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        signals = compute_f_score_signals(APPLE_PERIOD_2024)
        expected = {
            "roa": 1,
            "cfo": 1,
            "roa_change": 0,
            "accruals": 1,
            "leverage": 1,
            "liquidity": 0,
            "dilution": 1,
            "gross_margin": 1,
            "asset_turnover": 0,
        }
        assert signals == expected

    def test_name(self):
        """Factor name should be 'piotroski_f_score'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = piotroski_f_score(APPLE_PERIOD_2024)
        assert result.name == "piotroski_f_score"

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = piotroski_f_score(APPLE_PERIOD_2024)
        assert result.percentile_rank == 0.0


class TestNoPriorData:
    """Tests when prior period data is unavailable."""

    def test_no_prior_data(self):
        """Signals requiring prior data should be 0 when prior is None."""
        period = _make_period_current_only(
            net_income=Decimal("100"),
            total_assets=Decimal("1000"),
            operating_cash_flow=Decimal("150"),
        )
        signals = compute_f_score_signals(period)

        # Signals 1 (roa) and 2 (cfo) and 4 (accruals) should pass
        assert signals["roa"] == 1
        assert signals["cfo"] == 1
        assert signals["accruals"] == 1

        # All YoY signals should be 0
        assert signals["roa_change"] == 0
        assert signals["leverage"] == 0
        assert signals["liquidity"] == 0
        assert signals["dilution"] == 0
        assert signals["gross_margin"] == 0
        assert signals["asset_turnover"] == 0


class TestPerfectScore:
    """Test where all 9 signals pass."""

    def test_perfect_score(self):
        """Synthetic data engineered so all 9 F-Score signals = 1."""
        period = _make_period_full(
            # Current period: positive ROA, positive CFO, CFO > NI
            current_net_income=Decimal("200"),
            current_total_assets=Decimal("1000"),
            current_cfo=Decimal("300"),
            current_revenue=Decimal("2000"),
            current_cost_of_revenue=Decimal("1000"),
            current_gross_profit=Decimal("1000"),
            current_current_assets=Decimal("600"),
            current_current_liabilities=Decimal("300"),
            current_long_term_debt=Decimal("100"),
            current_shares=1000,
            # Prior period: worse in every way
            prior_net_income=Decimal("100"),
            prior_total_assets=Decimal("1000"),
            prior_cfo=Decimal("150"),
            prior_revenue=Decimal("1500"),
            prior_cost_of_revenue=Decimal("900"),
            prior_gross_profit=Decimal("600"),
            prior_current_assets=Decimal("400"),
            prior_current_liabilities=Decimal("300"),
            prior_long_term_debt=Decimal("200"),
            prior_shares=1100,
        )
        result = piotroski_f_score(period)
        assert result.raw_value == 9

        signals = compute_f_score_signals(period)
        assert all(v == 1 for v in signals.values())


class TestZeroScore:
    """Test where all 9 signals fail."""

    def test_zero_score(self):
        """Synthetic data engineered so all 9 F-Score signals = 0."""
        period = _make_period_full(
            # Current period: negative ROA, negative CFO, CFO < NI
            current_net_income=Decimal("-200"),
            current_total_assets=Decimal("1000"),
            current_cfo=Decimal("-300"),
            current_revenue=Decimal("1000"),
            current_cost_of_revenue=Decimal("700"),
            current_gross_profit=Decimal("300"),
            current_current_assets=Decimal("300"),
            current_current_liabilities=Decimal("400"),
            current_long_term_debt=Decimal("500"),
            current_shares=1200,
            # Prior period: better in every way
            prior_net_income=Decimal("-100"),
            prior_total_assets=Decimal("1000"),
            prior_cfo=Decimal("-50"),
            prior_revenue=Decimal("1200"),
            prior_cost_of_revenue=Decimal("700"),
            prior_gross_profit=Decimal("500"),
            prior_current_assets=Decimal("500"),
            prior_current_liabilities=Decimal("400"),
            prior_long_term_debt=Decimal("400"),
            prior_shares=1000,
        )
        result = piotroski_f_score(period)
        assert result.raw_value == 0

        signals = compute_f_score_signals(period)
        assert all(v == 0 for v in signals.values())


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_period_current_only(
    net_income: Decimal,
    total_assets: Decimal,
    operating_cash_flow: Decimal,
) -> FinancialPeriod:
    """Build a FinancialPeriod with only current data (no prior)."""
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=Decimal("1000"),
            net_income=net_income,
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
        ),
    )


def _make_period_full(
    *,
    current_net_income: Decimal,
    current_total_assets: Decimal,
    current_cfo: Decimal,
    current_revenue: Decimal,
    current_cost_of_revenue: Decimal,
    current_gross_profit: Decimal,
    current_current_assets: Decimal,
    current_current_liabilities: Decimal,
    current_long_term_debt: Decimal,
    current_shares: int,
    prior_net_income: Decimal,
    prior_total_assets: Decimal,
    prior_cfo: Decimal,
    prior_revenue: Decimal,
    prior_cost_of_revenue: Decimal,
    prior_gross_profit: Decimal,
    prior_current_assets: Decimal,
    prior_current_liabilities: Decimal,
    prior_long_term_debt: Decimal,
    prior_shares: int,
) -> FinancialPeriod:
    """Build a complete FinancialPeriod with current and prior data."""
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=current_revenue,
            cost_of_revenue=current_cost_of_revenue,
            gross_profit=current_gross_profit,
            net_income=current_net_income,
            shares_outstanding=current_shares,
        ),
        prior_income=IncomeStatement(
            revenue=prior_revenue,
            cost_of_revenue=prior_cost_of_revenue,
            gross_profit=prior_gross_profit,
            net_income=prior_net_income,
            shares_outstanding=prior_shares,
        ),
        current_balance=BalanceSheet(
            total_assets=current_total_assets,
            current_assets=current_current_assets,
            current_liabilities=current_current_liabilities,
            long_term_debt=current_long_term_debt,
            shares_outstanding=current_shares,
        ),
        prior_balance=BalanceSheet(
            total_assets=prior_total_assets,
            current_assets=prior_current_assets,
            current_liabilities=prior_current_liabilities,
            long_term_debt=prior_long_term_debt,
            shares_outstanding=prior_shares,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=current_cfo,
        ),
        prior_cash_flow=CashFlowStatement(
            operating_cash_flow=prior_cfo,
        ),
    )
