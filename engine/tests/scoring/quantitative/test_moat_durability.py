"""Tests for moat durability classifier — detects moat signatures from financial patterns."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score


def _make_period(
    *,
    revenue: Decimal = Decimal("1000"),
    ebit: Decimal = Decimal("200"),
    cost_of_revenue: Decimal = Decimal("600"),
    gross_profit: Decimal = Decimal("400"),
    depreciation: Decimal | None = Decimal("50"),
    total_equity: Decimal = Decimal("500"),
    long_term_debt: Decimal | None = Decimal("200"),
    short_term_debt: Decimal = Decimal("100"),
    cash_and_equivalents: Decimal | None = Decimal("0"),
    operating_cash_flow: Decimal = Decimal("250"),
    capital_expenditures: Decimal = Decimal("-80"),
    period_end: str = "2024-09-28",
) -> FinancialPeriod:
    income = IncomeStatement(
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
        gross_profit=gross_profit,
        ebit=ebit,
        depreciation=depreciation,
        net_income=ebit * Decimal("0.79"),
        shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1500"),
        total_equity=total_equity,
        long_term_debt=long_term_debt,
        short_term_debt=short_term_debt,
        cash_and_equivalents=cash_and_equivalents,
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


class TestMoatDurability:
    def test_scale_economics_detected(self):
        """ROIC increases as revenue grows -> scale economics signature."""
        periods = [
            _make_period(
                revenue=Decimal("500"),
                ebit=Decimal("50"),
                total_equity=Decimal("300"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("700"),
                ebit=Decimal("100"),
                total_equity=Decimal("400"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("900"),
                ebit=Decimal("170"),
                total_equity=Decimal("500"),
                period_end="2021-12-31",
            ),
            _make_period(
                revenue=Decimal("1100"),
                ebit=Decimal("260"),
                total_equity=Decimal("600"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1300"),
                ebit=Decimal("370"),
                total_equity=Decimal("700"),
                period_end="2023-12-31",
            ),
        ]
        history = FinancialHistory(ticker="SCALE", periods=periods)
        result = moat_durability_score(history)
        assert result.raw_value >= 1.0
        assert "scale_economics" in result.detail

    def test_capital_efficiency_detected(self):
        """Incremental ROIC >= trailing ROIC -> capital efficiency signature."""
        periods = [
            _make_period(
                ebit=Decimal("100"),
                total_equity=Decimal("400"),
                period_end="2019-12-31",
            ),
            _make_period(
                ebit=Decimal("200"),
                total_equity=Decimal("600"),
                period_end="2023-12-31",
            ),
        ]
        history = FinancialHistory(ticker="CAPEFF", periods=periods)
        result = moat_durability_score(history)
        assert "capital_efficiency" in result.detail

    def test_pricing_power_detected(self):
        """Gross margin expands while revenue grows -> pricing power signature."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                gross_profit=Decimal("400"),
                cost_of_revenue=Decimal("600"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("1100"),
                gross_profit=Decimal("460"),
                cost_of_revenue=Decimal("640"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("1200"),
                gross_profit=Decimal("530"),
                cost_of_revenue=Decimal("670"),
                period_end="2021-12-31",
            ),
            _make_period(
                revenue=Decimal("1300"),
                gross_profit=Decimal("610"),
                cost_of_revenue=Decimal("690"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1400"),
                gross_profit=Decimal("700"),
                cost_of_revenue=Decimal("700"),
                period_end="2023-12-31",
            ),
        ]
        history = FinancialHistory(ticker="PRICE", periods=periods)
        result = moat_durability_score(history)
        assert "pricing_power" in result.detail

    def test_operating_leverage_detected(self):
        """Revenue growth exceeds cost growth -> operating leverage signature."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("700"),
                gross_profit=Decimal("300"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("1200"),
                cost_of_revenue=Decimal("800"),
                gross_profit=Decimal("400"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("1500"),
                cost_of_revenue=Decimal("900"),
                gross_profit=Decimal("600"),
                period_end="2021-12-31",
            ),
        ]
        history = FinancialHistory(ticker="SWITCH", periods=periods)
        result = moat_durability_score(history)
        assert "operating_leverage" in result.detail

    def test_no_moat_signatures(self):
        """Declining ROIC with flat margins -> 0 signatures."""
        periods = [
            _make_period(
                ebit=Decimal("200"),
                total_equity=Decimal("400"),
                gross_profit=Decimal("400"),
                period_end="2019-12-31",
            ),
            _make_period(
                ebit=Decimal("150"),
                total_equity=Decimal("500"),
                gross_profit=Decimal("380"),
                period_end="2020-12-31",
            ),
            _make_period(
                ebit=Decimal("100"),
                total_equity=Decimal("600"),
                gross_profit=Decimal("360"),
                period_end="2021-12-31",
            ),
        ]
        history = FinancialHistory(ticker="NOMOAT", periods=periods)
        result = moat_durability_score(history)
        assert result.raw_value == 0.0

    def test_single_period_returns_zero(self):
        """Need 2+ periods to detect moat patterns."""
        history = FinancialHistory(ticker="ONE", periods=[_make_period()])
        result = moat_durability_score(history)
        assert result.raw_value == 0.0

    def test_percentile_rank_placeholder(self):
        history = FinancialHistory(ticker="PH", periods=[_make_period()])
        result = moat_durability_score(history)
        assert result.percentile_rank == 0.0
        assert result.name == "moat_durability"


class TestWeightedMoatSignatures:
    """Moat signatures weighted by empirical durability.

    Weights: operating_leverage=1.5, pricing_power=1.25,
    scale_economics=1.0, capital_efficiency=0.75
    Max weighted = 4.5, normalized to 0-4 scale: score = weighted_sum * (4.0 / 4.5)
    """

    def test_all_four_weighted_max(self):
        """All 4 signatures detected -> normalized raw_value = 4.0."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                ebit=Decimal("100"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                total_equity=Decimal("500"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("1200"),
                ebit=Decimal("160"),
                cost_of_revenue=Decimal("680"),
                gross_profit=Decimal("520"),
                total_equity=Decimal("600"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("1400"),
                ebit=Decimal("240"),
                cost_of_revenue=Decimal("740"),
                gross_profit=Decimal("660"),
                total_equity=Decimal("700"),
                period_end="2021-12-31",
            ),
            _make_period(
                revenue=Decimal("1600"),
                ebit=Decimal("340"),
                cost_of_revenue=Decimal("780"),
                gross_profit=Decimal("820"),
                total_equity=Decimal("800"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1800"),
                ebit=Decimal("460"),
                cost_of_revenue=Decimal("800"),
                gross_profit=Decimal("1000"),
                total_equity=Decimal("900"),
                period_end="2023-12-31",
            ),
        ]
        history = FinancialHistory(ticker="ALL4", periods=periods)
        result = moat_durability_score(history)
        assert result.raw_value == pytest.approx(4.0, rel=0.01)

    def test_durable_pair_higher_than_nondurable_pair(self):
        """operating_leverage + pricing_power (2.44) > scale + capital_efficiency (1.56)."""
        # Durable pair: operating_leverage + pricing_power only
        # ROIC declines (no scale_economics), incremental ROIC < median (no capital_efficiency)
        durable_periods = [
            _make_period(
                revenue=Decimal("1000"),
                ebit=Decimal("200"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                total_equity=Decimal("500"),
                long_term_debt=Decimal("200"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("1200"),
                ebit=Decimal("220"),
                cost_of_revenue=Decimal("660"),
                gross_profit=Decimal("540"),
                total_equity=Decimal("800"),
                long_term_debt=Decimal("300"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("1500"),
                ebit=Decimal("240"),
                cost_of_revenue=Decimal("700"),
                gross_profit=Decimal("800"),
                total_equity=Decimal("1200"),
                long_term_debt=Decimal("400"),
                period_end="2021-12-31",
            ),
        ]
        durable_history = FinancialHistory(ticker="DURABLE", periods=durable_periods)
        durable = moat_durability_score(durable_history)

        # Non-durable pair: scale_economics + capital_efficiency only
        # Gross margin declines (no pricing_power), cost growth > rev growth (no operating_leverage)
        nondurable_periods = [
            _make_period(
                revenue=Decimal("1000"),
                ebit=Decimal("100"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                total_equity=Decimal("400"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("1200"),
                ebit=Decimal("150"),
                cost_of_revenue=Decimal("740"),
                gross_profit=Decimal("460"),
                total_equity=Decimal("450"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("1400"),
                ebit=Decimal("210"),
                cost_of_revenue=Decimal("880"),
                gross_profit=Decimal("520"),
                total_equity=Decimal("500"),
                period_end="2021-12-31",
            ),
            _make_period(
                revenue=Decimal("1600"),
                ebit=Decimal("280"),
                cost_of_revenue=Decimal("1040"),
                gross_profit=Decimal("560"),
                total_equity=Decimal("550"),
                period_end="2022-12-31",
            ),
        ]
        nondurable_history = FinancialHistory(ticker="NONDURABLE", periods=nondurable_periods)
        nondurable = moat_durability_score(nondurable_history)

        assert durable.raw_value > nondurable.raw_value
        assert durable.raw_value == pytest.approx(2.44, rel=0.02)
        assert nondurable.raw_value == pytest.approx(1.56, rel=0.02)

    def test_no_signatures_zero(self):
        """No signatures detected -> raw_value = 0.0."""
        periods = [
            _make_period(
                ebit=Decimal("200"),
                total_equity=Decimal("400"),
                gross_profit=Decimal("400"),
                period_end="2019-12-31",
            ),
            _make_period(
                ebit=Decimal("150"),
                total_equity=Decimal("500"),
                gross_profit=Decimal("380"),
                period_end="2020-12-31",
            ),
            _make_period(
                ebit=Decimal("100"),
                total_equity=Decimal("600"),
                gross_profit=Decimal("360"),
                period_end="2021-12-31",
            ),
        ]
        history = FinancialHistory(ticker="NOMOAT", periods=periods)
        result = moat_durability_score(history)
        assert result.raw_value == pytest.approx(0.0)

    def test_operating_leverage_only(self):
        """Single most-durable signature -> raw_value = 1.5 * 4/4.5 = 1.333."""
        # Triggers ONLY operating_leverage: rev growth > cost growth,
        # but GM flat (no pricing_power), ROIC declining (no scale_economics),
        # incremental ROIC < median (no capital_efficiency).
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                ebit=Decimal("200"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                total_equity=Decimal("400"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("1200"),
                ebit=Decimal("170"),
                cost_of_revenue=Decimal("650"),
                gross_profit=Decimal("480"),
                total_equity=Decimal("600"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("1500"),
                ebit=Decimal("150"),
                cost_of_revenue=Decimal("700"),
                gross_profit=Decimal("600"),
                total_equity=Decimal("900"),
                period_end="2021-12-31",
            ),
        ]
        history = FinancialHistory(ticker="SWITCHONLY", periods=periods)
        result = moat_durability_score(history)
        assert "operating_leverage" in result.detail
        assert result.raw_value == pytest.approx(1.5 * 4.0 / 4.5, rel=0.01)
