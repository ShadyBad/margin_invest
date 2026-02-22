"""Tests for growth stage classifier."""

from decimal import Decimal

from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import GrowthStage
from margin_engine.scoring.classifier import classify_growth_stage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_period(
    revenue: Decimal = Decimal("10000"),
    cost_of_revenue: Decimal = Decimal("5000"),
    gross_profit: Decimal | None = None,
    operating_cash_flow: Decimal = Decimal("1000"),
    capital_expenditures: Decimal = Decimal("-200"),
    net_income: Decimal = Decimal("500"),
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for testing."""
    gp = gross_profit if gross_profit is not None else (revenue - cost_of_revenue)
    income = IncomeStatement(
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
        gross_profit=gp,
        net_income=net_income,
    )
    balance = BalanceSheet(total_assets=Decimal("50000"))
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


def _make_profile(
    sector: GICSSector = GICSSector.TECHNOLOGY,
    market_cap: Decimal = Decimal("10000000000"),  # $10B
) -> AssetProfile:
    """Build a minimal AssetProfile for testing."""
    return AssetProfile(
        ticker="TEST",
        name="Test Corp",
        sector=sector,
        market_cap=market_cap,
    )


# ---------------------------------------------------------------------------
# High Growth classification
# ---------------------------------------------------------------------------


class TestHighGrowth:
    """Revenue CAGR > 20%, Gross Margin > 40%, Market Cap > $2B."""

    def test_high_growth_all_criteria_met(self):
        period = _make_period(
            revenue=Decimal("10000"),
            cost_of_revenue=Decimal("5000"),
            gross_profit=Decimal("5000"),  # 50% GM
        )
        profile = _make_profile(market_cap=Decimal("5000000000"))  # $5B

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.25,  # 25%
        )
        assert result == GrowthStage.HIGH_GROWTH

    def test_high_growth_cagr_too_low(self):
        """CAGR = 15% should NOT be High Growth."""
        period = _make_period(
            revenue=Decimal("10000"),
            gross_profit=Decimal("5000"),  # 50% GM
        )
        profile = _make_profile(market_cap=Decimal("5000000000"))

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.15,
        )
        assert result != GrowthStage.HIGH_GROWTH

    def test_high_growth_gross_margin_too_low(self):
        """GM = 30% should NOT be High Growth."""
        period = _make_period(
            revenue=Decimal("10000"),
            cost_of_revenue=Decimal("7000"),
            gross_profit=Decimal("3000"),  # 30% GM
        )
        profile = _make_profile(market_cap=Decimal("5000000000"))

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.25,
        )
        assert result != GrowthStage.HIGH_GROWTH

    def test_high_growth_market_cap_too_low(self):
        """Market cap $1B should NOT be High Growth."""
        period = _make_period(
            revenue=Decimal("10000"),
            gross_profit=Decimal("5000"),  # 50% GM
        )
        profile = _make_profile(market_cap=Decimal("1000000000"))  # $1B

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.25,
        )
        assert result != GrowthStage.HIGH_GROWTH


# ---------------------------------------------------------------------------
# Steady Growth classification
# ---------------------------------------------------------------------------


class TestSteadyGrowth:
    """Revenue CAGR 5-20%, positive FCF."""

    def test_steady_growth(self):
        period = _make_period(
            operating_cash_flow=Decimal("500"),
            capital_expenditures=Decimal("-100"),  # FCF = 400
        )
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.10,  # 10%
        )
        assert result == GrowthStage.STEADY_GROWTH

    def test_steady_growth_negative_fcf_falls_to_default(self):
        """CAGR 10% but negative FCF should still default to Steady Growth."""
        period = _make_period(
            operating_cash_flow=Decimal("-500"),
            capital_expenditures=Decimal("-100"),  # FCF = -600
        )
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.10,
        )
        # With negative FCF it doesn't match Steady Growth rule explicitly,
        # but since nothing else matches it falls to default = Steady Growth
        assert result == GrowthStage.STEADY_GROWTH


# ---------------------------------------------------------------------------
# Mature / Cash Cow classification
# ---------------------------------------------------------------------------


class TestMature:
    """Revenue CAGR < 5%, FCF Yield > 4%."""

    def test_mature_by_cagr_and_fcf_yield(self):
        period = _make_period()
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.03,  # 3%
            fcf_yield=0.05,  # 5%
        )
        assert result == GrowthStage.MATURE

    def test_mature_fcf_yield_too_low(self):
        """Low CAGR but FCF yield 3% should NOT be Mature."""
        period = _make_period()
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.03,
            fcf_yield=0.03,
        )
        assert result != GrowthStage.MATURE

    def test_mature_computed_fcf_yield(self):
        """When fcf_yield is None, compute from FCF / market_cap."""
        period = _make_period(
            operating_cash_flow=Decimal("600000000"),
            capital_expenditures=Decimal("-100000000"),  # FCF = 500M
        )
        profile = _make_profile(market_cap=Decimal("10000000000"))  # $10B
        # FCF yield = 500M / 10B = 5%

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.02,
        )
        assert result == GrowthStage.MATURE


# ---------------------------------------------------------------------------
# Cyclical classification
# ---------------------------------------------------------------------------


class TestCyclical:
    """Revenue StdDev > 15% OR cyclical sector."""

    def test_cyclical_by_sector_energy(self):
        period = _make_period()
        profile = _make_profile(sector=GICSSector.ENERGY)

        result = classify_growth_stage(
            period=period,
            profile=profile,
        )
        assert result == GrowthStage.CYCLICAL

    def test_cyclical_by_sector_materials(self):
        period = _make_period()
        profile = _make_profile(sector=GICSSector.MATERIALS)

        result = classify_growth_stage(
            period=period,
            profile=profile,
        )
        assert result == GrowthStage.CYCLICAL

    def test_cyclical_by_sector_industrials(self):
        period = _make_period()
        profile = _make_profile(sector=GICSSector.INDUSTRIALS)

        result = classify_growth_stage(
            period=period,
            profile=profile,
        )
        assert result == GrowthStage.CYCLICAL

    def test_cyclical_by_sector_consumer_discretionary(self):
        period = _make_period()
        profile = _make_profile(sector=GICSSector.CONSUMER_DISCRETIONARY)

        result = classify_growth_stage(
            period=period,
            profile=profile,
        )
        assert result == GrowthStage.CYCLICAL

    def test_cyclical_by_revenue_volatility(self):
        """Revenue stddev > 15% triggers Cyclical even for non-cyclical sector."""
        period = _make_period()
        profile = _make_profile(sector=GICSSector.TECHNOLOGY)

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_stddev_5yr=0.20,  # 20%
        )
        assert result == GrowthStage.CYCLICAL

    def test_not_cyclical_with_low_stddev_and_noncyclical_sector(self):
        """Low stddev + non-cyclical sector should not be Cyclical."""
        period = _make_period()
        profile = _make_profile(sector=GICSSector.TECHNOLOGY)

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_stddev_5yr=0.10,
            revenue_cagr_3yr=0.10,
        )
        assert result != GrowthStage.CYCLICAL


# ---------------------------------------------------------------------------
# Turnaround classification
# ---------------------------------------------------------------------------


class TestTurnaround:
    """2+ negative NI of 4 quarters, 2+ sequential margin improvement, positive CFO."""

    def test_turnaround_all_criteria(self):
        period = _make_period(
            operating_cash_flow=Decimal("100"),  # positive CFO
        )
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            quarterly_net_incomes=[-50.0, -30.0, 10.0, 20.0],  # 2 negative
            quarterly_margins=[0.05, 0.08, 0.12, 0.15],  # 3 sequential improvements
        )
        assert result == GrowthStage.TURNAROUND

    def test_turnaround_needs_positive_cfo(self):
        """Negative CFO should prevent Turnaround classification."""
        period = _make_period(
            operating_cash_flow=Decimal("-100"),  # negative CFO
        )
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            quarterly_net_incomes=[-50.0, -30.0, 10.0, 20.0],
            quarterly_margins=[0.05, 0.08, 0.12, 0.15],
        )
        assert result != GrowthStage.TURNAROUND

    def test_turnaround_needs_margin_improvement(self):
        """Without sequential margin improvement, no Turnaround."""
        period = _make_period(
            operating_cash_flow=Decimal("100"),
        )
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            quarterly_net_incomes=[-50.0, -30.0, 10.0, 20.0],
            quarterly_margins=[0.15, 0.12, 0.08, 0.05],  # declining margins
        )
        assert result != GrowthStage.TURNAROUND

    def test_turnaround_needs_enough_negative_quarters(self):
        """Only 1 negative quarter is not enough for Turnaround."""
        period = _make_period(
            operating_cash_flow=Decimal("100"),
        )
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            quarterly_net_incomes=[-10.0, 30.0, 40.0, 50.0],  # only 1 negative
            quarterly_margins=[0.05, 0.08, 0.12, 0.15],
        )
        assert result != GrowthStage.TURNAROUND

    def test_turnaround_exactly_two_negative_quarters(self):
        """Exactly 2 negative quarters should trigger Turnaround."""
        period = _make_period(
            operating_cash_flow=Decimal("100"),
        )
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            quarterly_net_incomes=[-50.0, -30.0, 50.0, 60.0],
            quarterly_margins=[0.05, 0.08, 0.12, 0.15],
        )
        assert result == GrowthStage.TURNAROUND


# ---------------------------------------------------------------------------
# Priority order
# ---------------------------------------------------------------------------


class TestPriorityOrder:
    """First match wins: Turnaround > High Growth > Cyclical > Mature > Steady."""

    def test_turnaround_beats_high_growth(self):
        """When both Turnaround and High Growth criteria are met, Turnaround wins."""
        period = _make_period(
            revenue=Decimal("10000"),
            gross_profit=Decimal("5000"),  # 50% GM
            operating_cash_flow=Decimal("100"),
        )
        profile = _make_profile(market_cap=Decimal("5000000000"))

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.25,  # would qualify as High Growth
            quarterly_net_incomes=[-50.0, -30.0, 10.0, 20.0],
            quarterly_margins=[0.05, 0.08, 0.12, 0.15],
        )
        assert result == GrowthStage.TURNAROUND

    def test_high_growth_beats_cyclical(self):
        """High Growth checked before Cyclical; a high-growth cyclical sector -> High Growth."""
        period = _make_period(
            revenue=Decimal("10000"),
            gross_profit=Decimal("5000"),  # 50% GM
        )
        profile = _make_profile(
            sector=GICSSector.CONSUMER_DISCRETIONARY,  # cyclical
            market_cap=Decimal("5000000000"),
        )

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.25,
        )
        assert result == GrowthStage.HIGH_GROWTH

    def test_cyclical_beats_mature(self):
        """Cyclical sector + mature metrics -> Cyclical wins."""
        period = _make_period()
        profile = _make_profile(sector=GICSSector.ENERGY)

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.03,
            fcf_yield=0.05,
        )
        assert result == GrowthStage.CYCLICAL

    def test_mature_beats_steady_growth(self):
        """When Mature criteria met (CAGR < 5%, FCF yield > 4%), Mature wins."""
        period = _make_period()
        profile = _make_profile()

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.04,  # < 5%
            fcf_yield=0.05,  # > 4%
        )
        assert result == GrowthStage.MATURE


# ---------------------------------------------------------------------------
# Default / edge cases
# ---------------------------------------------------------------------------


class TestDefault:
    """Default to Steady Growth when no data or nothing matches."""

    def test_default_no_optional_data(self):
        """All optional params are None -> default Steady Growth."""
        period = _make_period()
        profile = _make_profile()

        result = classify_growth_stage(period=period, profile=profile)
        assert result == GrowthStage.STEADY_GROWTH

    def test_default_non_cyclical_sector_no_data(self):
        """Non-cyclical sector with no metrics defaults to Steady Growth."""
        period = _make_period()
        profile = _make_profile(sector=GICSSector.HEALTHCARE)

        result = classify_growth_stage(period=period, profile=profile)
        assert result == GrowthStage.STEADY_GROWTH

    def test_none_cagr_skips_growth_rules(self):
        """None revenue_cagr_3yr means growth-based rules are skipped."""
        period = _make_period()
        profile = _make_profile(sector=GICSSector.TECHNOLOGY)

        result = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=None,
            fcf_yield=0.05,
        )
        # Can't check High Growth, Mature, or Steady Growth CAGR rules
        # Non-cyclical sector, no turnaround data -> default
        assert result == GrowthStage.STEADY_GROWTH


# ---------------------------------------------------------------------------
# Apple FY2024 golden fixture test
# ---------------------------------------------------------------------------


class TestAppleFY2024:
    """Apple FY2024 classification using the golden test fixture."""

    def test_apple_classifies_as_steady_growth(self):
        """Apple FY2024: ~2% revenue CAGR, Technology sector, ~3% FCF yield.

        - Not turnaround (consistently profitable)
        - Not high growth (CAGR ~2%)
        - Not cyclical (Technology sector)
        - Not mature (FCF yield ~3.1% < 4%)
        - Not steady growth by rule (CAGR ~2% < 5%)
        - Default -> Steady Growth
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        # Apple's actual 3-year revenue CAGR (FY2021-FY2024) is ~2%
        apple_cagr_3yr = 0.02

        # FCF / Market Cap = 108.295B / 3.5T = ~3.09%
        apple_fcf_yield = 108_295_000_000 / 3_500_000_000_000

        result = classify_growth_stage(
            period=APPLE_PERIOD_2024,
            profile=APPLE_PROFILE,
            revenue_cagr_3yr=apple_cagr_3yr,
            fcf_yield=apple_fcf_yield,
        )
        assert result == GrowthStage.STEADY_GROWTH

    def test_apple_not_cyclical(self):
        """Technology sector is not cyclical."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = classify_growth_stage(
            period=APPLE_PERIOD_2024,
            profile=APPLE_PROFILE,
            revenue_cagr_3yr=0.02,
        )
        assert result != GrowthStage.CYCLICAL

    def test_apple_with_higher_cagr_becomes_steady(self):
        """If Apple had 10% CAGR, it would be Steady Growth (by rule, not default)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = classify_growth_stage(
            period=APPLE_PERIOD_2024,
            profile=APPLE_PROFILE,
            revenue_cagr_3yr=0.10,
        )
        assert result == GrowthStage.STEADY_GROWTH
