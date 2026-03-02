"""Tests for style-aware FCF distress filter adjustments."""

from decimal import Decimal

from margin_engine.config.filter_config import FcfDistressConfig
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.models.scoring import InvestmentStyle
from margin_engine.scoring.filters.fcf_distress import fcf_distress_check_v2


def _make_period(
    fcf_positive: bool,
    revenue: float = 5_000_000,
    gross_margin: float = 0.5,
    year: int = 2020,
) -> FinancialPeriod:
    """Helper to create a period with positive or negative FCF.

    When fcf_positive=True: OCF=200000, capex=-50000, FCF=150000
    When fcf_positive=False: OCF=-100000, capex=-50000, FCF=-150000

    Default revenue=5M keeps FCF margin above the -5% floor
    (-150000/5000000 = -3%) so tests focus on the count logic.
    """
    gross_profit = Decimal(str(revenue * gross_margin))
    cogs = Decimal(str(revenue)) - gross_profit
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("200000") if fcf_positive else Decimal("-100000"),
        capital_expenditures=Decimal("-50000"),
    )
    income = IncomeStatement(
        revenue=Decimal(str(revenue)),
        cost_of_revenue=cogs,
        gross_profit=gross_profit,
    )
    balance = BalanceSheet(
        total_assets=Decimal("5000000"),
        current_assets=Decimal("2000000"),
        total_liabilities=Decimal("2000000"),
        current_liabilities=Decimal("1000000"),
        total_equity=Decimal("3000000"),
    )
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


class TestFcfDistressStyleAware:
    def test_growth_stock_2_of_5_passes(self):
        """Growth stocks need only 2/5 positive FCF years (not 3/5)."""
        # Use permissive margin floor so test focuses on count logic
        config = FcfDistressConfig(min_fcf_margin=-0.05, sector_margin_overrides={})
        periods = [
            _make_period(False, year=2020),
            _make_period(False, year=2021),
            _make_period(False, year=2022),
            _make_period(True, year=2023),
            _make_period(True, year=2024),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = fcf_distress_check_v2(
            history,
            config=config,
            style=InvestmentStyle.GROWTH,
        )
        assert result.passed is True

    def test_value_stock_2_of_5_fails(self):
        """Value stocks still need 3/5 positive FCF years."""
        periods = [
            _make_period(False, year=2020),
            _make_period(False, year=2021),
            _make_period(False, year=2022),
            _make_period(True, year=2023),
            _make_period(True, year=2024),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = fcf_distress_check_v2(
            history,
            style=InvestmentStyle.VALUE,
        )
        assert result.passed is False

    def test_growth_stock_ocf_plus_margin_rescue(self):
        """Growth stock with positive operating CF + gross margin > 40%.

        Passes even with 1/5 positive FCF.
        """
        # Use permissive margin floor so test focuses on OCF rescue logic
        config = FcfDistressConfig(min_fcf_margin=-0.05, sector_margin_overrides={})
        periods = [
            _make_period(False, gross_margin=0.55, year=2020),
            _make_period(False, gross_margin=0.55, year=2021),
            _make_period(False, gross_margin=0.55, year=2022),
            _make_period(False, gross_margin=0.55, year=2023),
            _make_period(True, gross_margin=0.55, year=2024),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = fcf_distress_check_v2(
            history,
            config=config,
            style=InvestmentStyle.GROWTH,
        )
        # 1/5 positive < 2 required, but OCF rescue applies (latest has positive OCF + margin > 40%)
        assert result.passed is True

    def test_growth_stock_low_margin_no_rescue(self):
        """Growth stock with gross margin <= 40% doesn't get OCF rescue."""
        periods = [
            _make_period(False, gross_margin=0.30, year=2020),
            _make_period(False, gross_margin=0.30, year=2021),
            _make_period(False, gross_margin=0.30, year=2022),
            _make_period(False, gross_margin=0.30, year=2023),
            _make_period(True, gross_margin=0.30, year=2024),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = fcf_distress_check_v2(
            history,
            style=InvestmentStyle.GROWTH,
        )
        # 1/5 positive < 2, low margin = no rescue
        assert result.passed is False

    def test_none_style_uses_default_behavior(self):
        """When style is None, behaves as before (3/5 required)."""
        periods = [
            _make_period(False, year=2020),
            _make_period(False, year=2021),
            _make_period(False, year=2022),
            _make_period(True, year=2023),
            _make_period(True, year=2024),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = fcf_distress_check_v2(history, style=None)
        assert result.passed is False
