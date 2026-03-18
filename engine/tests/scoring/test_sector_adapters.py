"""Tests for sector-specific profitability adapters and percentile normalization.

Covers:
- SectorAdapter.profitability_metric() returns ROE for Financials, FFO proxy for
  Real Estate, ROIC for all other sectors.
- SectorAdapter.metric_name() returns human-readable label.
- SectorAdapter.needs_percentile_gates() is True only for Financials/Real Estate.
- sector_percentile_rank() computes correct percentile from known distributions.
- Missing/unknown sector defaults to 50th percentile.
- Edge cases: zero equity, negative values, single-element universe.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from margin_engine.config.v3_scoring_config import SectorPercentileConfig
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.sector_adapters import (
    SectorAdapter,
    sector_percentile_rank,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_period(
    *,
    revenue: Decimal = Decimal("1000"),
    ebit: Decimal = Decimal("200"),
    net_income: Decimal = Decimal("150"),
    depreciation: Decimal | None = Decimal("50"),
    tax_provision: Decimal | None = Decimal("40"),
    total_equity: Decimal = Decimal("1000"),
    total_debt: Decimal = Decimal("500"),
    cash: Decimal = Decimal("200"),
) -> FinancialPeriod:
    """Build a FinancialPeriod with controllable values."""
    income = IncomeStatement(
        revenue=revenue,
        ebit=ebit,
        net_income=net_income,
        depreciation=depreciation,
        tax_provision=tax_provision,
    )
    balance = BalanceSheet(
        total_assets=Decimal("3000"),
        total_equity=total_equity,
        long_term_debt=total_debt,
        cash_and_equivalents=cash,
    )
    cash_flow = CashFlowStatement()
    return FinancialPeriod(
        period_end="2025-12-31",
        filing_date="2026-02-15",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cash_flow,
    )


# ---------------------------------------------------------------------------
# SectorAdapter.profitability_metric() — correct formula per sector
# ---------------------------------------------------------------------------


class TestProfitabilityMetric:
    """profitability_metric() returns the right metric for each sector."""

    def test_financials_uses_roe(self) -> None:
        """Financials: ROE = net_income / total_equity."""
        period = _make_period(net_income=Decimal("150"), total_equity=Decimal("1000"))
        result = SectorAdapter.profitability_metric(period, GICSSector.FINANCIALS)
        assert result == pytest.approx(0.15, abs=1e-6)

    def test_real_estate_uses_ffo_proxy(self) -> None:
        """Real Estate: FFO proxy = (net_income + depreciation) / total_equity."""
        period = _make_period(
            net_income=Decimal("100"),
            depreciation=Decimal("80"),
            total_equity=Decimal("1000"),
        )
        result = SectorAdapter.profitability_metric(period, GICSSector.REAL_ESTATE)
        # (100 + 80) / 1000 = 0.18
        assert result == pytest.approx(0.18, abs=1e-6)

    def test_technology_uses_roic(self) -> None:
        """Technology (and all non-special sectors): ROIC = NOPAT / IC."""
        period = _make_period(
            ebit=Decimal("200"),
            tax_provision=Decimal("40"),
            total_equity=Decimal("1000"),
            total_debt=Decimal("500"),
            cash=Decimal("200"),
        )
        # tax_rate = 40 / (200 - 0) = 0.20
        # NOPAT = 200 * (1 - 0.20) = 160
        # IC = 1000 + 500 - 200 = 1300
        # ROIC = 160 / 1300 ≈ 0.12308
        result = SectorAdapter.profitability_metric(period, GICSSector.TECHNOLOGY)
        assert result == pytest.approx(160.0 / 1300.0, abs=1e-6)

    def test_industrials_uses_roic(self) -> None:
        """Non-special sectors (Industrials) also use ROIC."""
        period = _make_period(
            ebit=Decimal("200"),
            tax_provision=Decimal("40"),
            total_equity=Decimal("1000"),
            total_debt=Decimal("500"),
            cash=Decimal("200"),
        )
        result = SectorAdapter.profitability_metric(period, GICSSector.INDUSTRIALS)
        assert result == pytest.approx(160.0 / 1300.0, abs=1e-6)

    def test_zero_equity_returns_zero(self) -> None:
        """When total_equity is zero, metric returns 0.0 (no division error)."""
        period = _make_period(total_equity=Decimal("0"))
        result = SectorAdapter.profitability_metric(period, GICSSector.FINANCIALS)
        assert result == 0.0

    def test_zero_invested_capital_returns_zero(self) -> None:
        """When invested capital is zero (or negative), ROIC returns 0.0."""
        period = _make_period(
            total_equity=Decimal("0"),
            total_debt=Decimal("0"),
            cash=Decimal("100"),
        )
        result = SectorAdapter.profitability_metric(period, GICSSector.TECHNOLOGY)
        assert result == 0.0

    def test_real_estate_no_depreciation_uses_zero(self) -> None:
        """FFO proxy treats None depreciation as 0."""
        period = _make_period(
            net_income=Decimal("100"),
            depreciation=None,
            total_equity=Decimal("1000"),
        )
        result = SectorAdapter.profitability_metric(period, GICSSector.REAL_ESTATE)
        # (100 + 0) / 1000 = 0.10
        assert result == pytest.approx(0.10, abs=1e-6)


# ---------------------------------------------------------------------------
# SectorAdapter.metric_name()
# ---------------------------------------------------------------------------


class TestMetricName:
    def test_financials_name(self) -> None:
        assert SectorAdapter.metric_name(GICSSector.FINANCIALS) == "ROE"

    def test_real_estate_name(self) -> None:
        assert SectorAdapter.metric_name(GICSSector.REAL_ESTATE) == "FFO Proxy"

    def test_technology_name(self) -> None:
        assert SectorAdapter.metric_name(GICSSector.TECHNOLOGY) == "ROIC"

    def test_energy_name(self) -> None:
        assert SectorAdapter.metric_name(GICSSector.ENERGY) == "ROIC"


# ---------------------------------------------------------------------------
# SectorAdapter.needs_percentile_gates()
# ---------------------------------------------------------------------------


class TestNeedsPercentileGates:
    def test_financials_needs_percentile(self) -> None:
        assert SectorAdapter.needs_percentile_gates(GICSSector.FINANCIALS) is True

    def test_real_estate_needs_percentile(self) -> None:
        assert SectorAdapter.needs_percentile_gates(GICSSector.REAL_ESTATE) is True

    def test_technology_does_not(self) -> None:
        assert SectorAdapter.needs_percentile_gates(GICSSector.TECHNOLOGY) is False

    def test_industrials_does_not(self) -> None:
        assert SectorAdapter.needs_percentile_gates(GICSSector.INDUSTRIALS) is False

    def test_all_non_percentile_sectors(self) -> None:
        """All 9 non-percentile sectors return False."""
        percentile_sectors = {GICSSector.FINANCIALS, GICSSector.REAL_ESTATE}
        for sector in GICSSector:
            if sector not in percentile_sectors:
                assert SectorAdapter.needs_percentile_gates(sector) is False, sector


# ---------------------------------------------------------------------------
# sector_percentile_rank() — percentile within sector universe
# ---------------------------------------------------------------------------


class TestSectorPercentileRank:
    def test_known_distribution_top(self) -> None:
        """Top value in a 5-element universe → 100th percentile."""
        universe = [0.05, 0.08, 0.10, 0.12, 0.15]
        rank = sector_percentile_rank(0.15, GICSSector.FINANCIALS, universe)
        assert rank == pytest.approx(100.0, abs=1e-6)

    def test_known_distribution_bottom(self) -> None:
        """Bottom value in a 5-element universe → 20th percentile (1/5 * 100)."""
        universe = [0.05, 0.08, 0.10, 0.12, 0.15]
        rank = sector_percentile_rank(0.05, GICSSector.FINANCIALS, universe)
        assert rank == pytest.approx(20.0, abs=1e-6)

    def test_known_distribution_median(self) -> None:
        """Middle of 5 → 60th percentile (3/5 * 100)."""
        universe = [0.05, 0.08, 0.10, 0.12, 0.15]
        rank = sector_percentile_rank(0.10, GICSSector.FINANCIALS, universe)
        assert rank == pytest.approx(60.0, abs=1e-6)

    def test_empty_universe_returns_50(self) -> None:
        """Empty universe → default 50."""
        rank = sector_percentile_rank(0.10, GICSSector.FINANCIALS, [])
        assert rank == 50.0

    def test_single_element_universe(self) -> None:
        """Single element → 100th percentile if matched."""
        rank = sector_percentile_rank(0.10, GICSSector.FINANCIALS, [0.10])
        assert rank == pytest.approx(100.0, abs=1e-6)

    def test_non_percentile_sector_returns_50(self) -> None:
        """Non-percentile sector → always 50."""
        universe = [0.05, 0.08, 0.10, 0.12, 0.15]
        rank = sector_percentile_rank(0.10, GICSSector.TECHNOLOGY, universe)
        assert rank == 50.0

    def test_value_above_all_in_universe(self) -> None:
        """Value above all in universe → 100th percentile."""
        universe = [0.05, 0.08, 0.10]
        rank = sector_percentile_rank(0.20, GICSSector.FINANCIALS, universe)
        assert rank == pytest.approx(100.0, abs=1e-6)

    def test_value_below_all_in_universe(self) -> None:
        """Value below all in universe → approaches 0 but uses rank logic."""
        universe = [0.05, 0.08, 0.10]
        rank = sector_percentile_rank(0.01, GICSSector.FINANCIALS, universe)
        # Below all 3 values: 0 out of 3 are <= 0.01, wait no:
        # percentile = count(universe <= value) / len(universe) * 100
        # 0 values are <= 0.01 → 0/3 * 100 = 0.0
        assert rank == pytest.approx(0.0, abs=1e-6)

    def test_duplicate_values(self) -> None:
        """Duplicate values handled correctly."""
        universe = [0.10, 0.10, 0.10, 0.10, 0.20]
        rank = sector_percentile_rank(0.10, GICSSector.FINANCIALS, universe)
        # 4 out of 5 are <= 0.10 → 80th percentile
        assert rank == pytest.approx(80.0, abs=1e-6)


# ---------------------------------------------------------------------------
# SectorPercentileConfig — config model
# ---------------------------------------------------------------------------


class TestSectorPercentileConfig:
    def test_defaults(self) -> None:
        config = SectorPercentileConfig()
        assert config.capital_light_bypass == 90.0
        assert config.exceptional == 75.0
        assert config.strong == 60.0
        assert config.adequate == 50.0
        assert config.minimum == 50.0

    def test_custom_values(self) -> None:
        config = SectorPercentileConfig(
            capital_light_bypass=95.0,
            exceptional=80.0,
            strong=65.0,
            adequate=55.0,
            minimum=45.0,
        )
        assert config.capital_light_bypass == 95.0
        assert config.exceptional == 80.0
