"""Tests for Capital Allocation sub-factors."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.capital_allocation import (
    buyback_effectiveness,
    debt_discipline,
    insider_ownership_score,
    organic_reinvestment_ratio,
)


def _make_period(
    year: int,
    share_repurchases: Decimal = Decimal("-100"),
    shares_outstanding: int = 1000,
    long_term_debt: Decimal = Decimal("500"),
    ebit: Decimal = Decimal("200"),
    depreciation: Decimal = Decimal("30"),
    capex: Decimal = Decimal("-80"),
    dividends: Decimal = Decimal("-30"),
    cfo: Decimal = Decimal("250"),
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"),
            ebit=ebit,
            depreciation=depreciation,
            net_income=ebit * Decimal("0.79"),
            shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
            long_term_debt=long_term_debt,
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo,
            capital_expenditures=capex,
            dividends_paid=dividends,
            share_repurchases=share_repurchases,
        ),
    )


class TestBuybackEffectiveness:
    def test_buying_below_average(self):
        """If avg repurchase price < avg stock price, ratio < 1 = effective."""
        result = buyback_effectiveness(
            total_repurchases=Decimal("1000000"),
            shares_reduced=100,
            avg_stock_price=12000.0,
        )
        # Avg buyback price = 1000000 / 100 = 10000
        # Ratio = 10000 / 12000 = 0.833
        assert result.name == "buyback_effectiveness"
        assert result.raw_value == pytest.approx(0.833, abs=0.01)

    def test_no_buybacks_returns_neutral(self):
        result = buyback_effectiveness(
            total_repurchases=Decimal("0"),
            shares_reduced=0,
            avg_stock_price=100.0,
        )
        assert result.raw_value == 0.5  # neutral


class TestDebtDiscipline:
    def test_declining_leverage(self):
        """Net Debt / EBITDA declining over time = disciplined."""
        periods = [
            _make_period(2021, long_term_debt=Decimal("800")),
            _make_period(2022, long_term_debt=Decimal("600")),
            _make_period(2023, long_term_debt=Decimal("400")),
        ]
        h = FinancialHistory(ticker="DISC", periods=periods)
        result = debt_discipline(h)
        assert result.name == "debt_discipline"
        assert result.raw_value < 0  # Negative slope = improving


class TestOrganicReinvestmentRatio:
    def test_high_reinvestment(self):
        """Most capital deployed to growth capex = high ratio."""
        # Growth capex = |capex| - depr = 80 - 30 = 50
        # Total deployed = growth_capex + |buybacks| + |dividends| = 50 + 100 + 30 = 180
        # Ratio = 50 / 180 = 0.2778
        period = _make_period(2023)
        result = organic_reinvestment_ratio(period)
        assert result.name == "organic_reinvestment_ratio"
        assert result.raw_value == pytest.approx(0.2778, abs=0.01)


class TestInsiderOwnership:
    def test_basic(self):
        result = insider_ownership_score(ownership_pct=0.15)
        assert result.name == "insider_ownership"
        assert result.raw_value == pytest.approx(0.15)

    def test_zero(self):
        result = insider_ownership_score(ownership_pct=0.0)
        assert result.raw_value == 0.0


class TestSbcDilutionTax:
    def test_low_sbc_good_score(self):
        """SBC < 3% of revenue -> low dilution."""
        from margin_engine.scoring.quantitative.capital_allocation import sbc_dilution_tax

        result = sbc_dilution_tax(
            sbc_amount=Decimal("30"),
            revenue=Decimal("1000"),
        )
        assert result.name == "sbc_dilution_tax"
        assert result.raw_value == pytest.approx(0.03)

    def test_high_sbc_bad_score(self):
        """SBC > 10% of revenue -> heavy dilution."""
        from margin_engine.scoring.quantitative.capital_allocation import sbc_dilution_tax

        result = sbc_dilution_tax(
            sbc_amount=Decimal("120"),
            revenue=Decimal("1000"),
        )
        assert result.raw_value == pytest.approx(0.12)

    def test_zero_revenue(self):
        from margin_engine.scoring.quantitative.capital_allocation import sbc_dilution_tax

        result = sbc_dilution_tax(
            sbc_amount=Decimal("30"),
            revenue=Decimal("0"),
        )
        assert result.raw_value == 1.0  # Worst case


class TestMaDiscipline:
    def test_roic_stable_after_acquisition(self):
        """ROIC doesn't decline after acquisition -> good discipline."""
        from margin_engine.scoring.quantitative.capital_allocation import ma_discipline

        result = ma_discipline(
            roic_before_acquisition=0.20,
            roic_after_acquisition=0.22,
        )
        assert result.name == "ma_discipline"
        assert result.raw_value > 0.0

    def test_roic_declines_after_acquisition(self):
        """ROIC declines after acquisition -> bad discipline."""
        from margin_engine.scoring.quantitative.capital_allocation import ma_discipline

        result = ma_discipline(
            roic_before_acquisition=0.20,
            roic_after_acquisition=0.12,
        )
        assert result.raw_value < 0.0

    def test_no_acquisition(self):
        """No acquisition data -> neutral."""
        from margin_engine.scoring.quantitative.capital_allocation import ma_discipline

        result = ma_discipline(
            roic_before_acquisition=None,
            roic_after_acquisition=None,
        )
        assert result.raw_value == 0.0
