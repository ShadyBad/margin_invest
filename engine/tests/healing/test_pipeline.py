"""Tests for the HealingPipeline orchestrator.

Covers:
- Clean data passes through (no detections, no corrections)
- Negative revenue detected (Tier 1)
- Zero shares → excluded=True (excluded field, no correction possible)
- Breadth suspension blocks corrections but still has detections
- Corrections are applied to period (field values updated on copy)
- Multiple tiers produce combined detections
- _extract_field_values skips margins when revenue is zero
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.healing.models import (
    CorrectionMethod,
    DetectionSeverity,
    HealingConfig,
    SectorDistribution,
)
from margin_engine.healing.pipeline import HealingPipeline, HealingResult
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_period(
    revenue: Decimal = Decimal("1000"),
    gross_profit: Decimal = Decimal("400"),
    net_income: Decimal = Decimal("200"),
    shares_outstanding: int = 100,
    total_assets: Decimal = Decimal("5000"),
    total_liabilities: Decimal = Decimal("2000"),
    total_equity: Decimal = Decimal("3000"),
    current_assets: Decimal = Decimal("2000"),
    current_liabilities: Decimal = Decimal("1000"),
    long_term_debt: Decimal | None = Decimal("500"),
) -> FinancialPeriod:
    """Build a FinancialPeriod with sensible defaults for pipeline tests."""
    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2025-02-15",
        current_income=IncomeStatement(
            revenue=revenue,
            gross_profit=gross_profit,
            net_income=net_income,
            shares_outstanding=shares_outstanding,
            ebit=Decimal("300"),
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            current_assets=current_assets,
            current_liabilities=current_liabilities,
            long_term_debt=long_term_debt,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("400"),
            capital_expenditures=Decimal("-100"),
        ),
    )


def _make_sector_distributions(
    sector: str = "Information Technology",
    period: str = "2024-12-31",
    gross_margin: float = 0.40,
    net_margin: float = 0.20,
    debt_to_equity: float = 0.25,
    current_ratio: float = 2.0,
) -> list[SectorDistribution]:
    """Build a set of sector distributions for common fields."""
    return [
        SectorDistribution(
            sector=sector,
            field_path="income_statement.gross_margin",
            median=gross_margin,
            mad=0.05,
            n_observations=30,
            period=period,
        ),
        SectorDistribution(
            sector=sector,
            field_path="income_statement.net_margin",
            median=net_margin,
            mad=0.04,
            n_observations=30,
            period=period,
        ),
        SectorDistribution(
            sector=sector,
            field_path="balance_sheet.debt_to_equity",
            median=debt_to_equity,
            mad=0.10,
            n_observations=30,
            period=period,
        ),
        SectorDistribution(
            sector=sector,
            field_path="balance_sheet.current_ratio",
            median=current_ratio,
            mad=0.30,
            n_observations=30,
            period=period,
        ),
    ]


# ---------------------------------------------------------------------------
# Test: clean data passes through
# ---------------------------------------------------------------------------


class TestCleanDataPassthrough:
    """Clean data should produce a HealingResult with no detections or corrections."""

    def test_clean_data_no_detections(self) -> None:
        pipeline = HealingPipeline()
        period = _make_period()
        sector_dists = _make_sector_distributions()

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values=None,
            prior_valid_values=None,
        )

        assert isinstance(result, HealingResult)
        assert result.period == period
        assert result.detections == []
        assert result.corrections == []
        assert result.excluded is False
        assert result.breadth_suspended is False

    def test_clean_data_with_custom_config(self) -> None:
        config = HealingConfig(tier2_mad_thresholds={
            "margins": 10.0,
            "growth_rates": 12.0,
            "leverage_ratios": 11.0,
            "price_returns": 15.0,
        })
        pipeline = HealingPipeline(config=config)
        period = _make_period()
        sector_dists = _make_sector_distributions()

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values=None,
            prior_valid_values=None,
        )

        assert result.detections == []
        assert result.corrections == []


# ---------------------------------------------------------------------------
# Test: negative revenue (Tier 1 detection)
# ---------------------------------------------------------------------------


class TestNegativeRevenueDetection:
    """Negative revenue triggers a Tier 1 IMPOSSIBLE detection."""

    def test_negative_revenue_detected(self) -> None:
        pipeline = HealingPipeline()
        period = _make_period(revenue=Decimal("-500"))
        sector_dists = _make_sector_distributions()

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values=None,
            prior_valid_values=None,
        )

        assert len(result.detections) >= 1
        revenue_flags = [
            d for d in result.detections if d.field_path == "income_statement.revenue"
        ]
        assert len(revenue_flags) == 1
        assert revenue_flags[0].severity == DetectionSeverity.IMPOSSIBLE

    def test_negative_revenue_with_secondary_correction(self) -> None:
        """Negative revenue with a secondary source should produce a correction."""
        pipeline = HealingPipeline()
        period = _make_period(revenue=Decimal("-500"))
        sector_dists = _make_sector_distributions()

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values={"income_statement.revenue": 1000.0},
            prior_valid_values=None,
        )

        # Should have at least one correction for revenue
        revenue_corrections = [
            c for c in result.corrections if c.field_path == "income_statement.revenue"
        ]
        assert len(revenue_corrections) == 1
        assert revenue_corrections[0].correction_method == CorrectionMethod.L1_SUBSTITUTE


# ---------------------------------------------------------------------------
# Test: zero shares → excluded
# ---------------------------------------------------------------------------


class TestZeroSharesExcluded:
    """Zero shares outstanding → excluded=True because shares_outstanding is an excluded field."""

    def test_zero_shares_sets_excluded(self) -> None:
        pipeline = HealingPipeline()
        period = _make_period(shares_outstanding=0)
        sector_dists = _make_sector_distributions()

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values=None,
            prior_valid_values=None,
        )

        assert result.excluded is True
        shares_flags = [
            d for d in result.detections
            if d.field_path == "income_statement.shares_outstanding"
        ]
        assert len(shares_flags) == 1
        assert shares_flags[0].severity == DetectionSeverity.IMPOSSIBLE

    def test_zero_shares_with_secondary_not_excluded(self) -> None:
        """Zero shares with a secondary source correction should not be excluded."""
        pipeline = HealingPipeline()
        period = _make_period(shares_outstanding=0)
        sector_dists = _make_sector_distributions()

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values={"income_statement.shares_outstanding": 1000.0},
            prior_valid_values=None,
        )

        # With a correction available, should not be excluded
        assert result.excluded is False
        shares_corrections = [
            c for c in result.corrections
            if c.field_path == "income_statement.shares_outstanding"
        ]
        assert len(shares_corrections) == 1


# ---------------------------------------------------------------------------
# Test: breadth suspension
# ---------------------------------------------------------------------------


class TestBreadthSuspension:
    """Breadth suspension blocks corrections but keeps detections."""

    def test_breadth_suspension_blocks_corrections(self) -> None:
        pipeline = HealingPipeline()
        period = _make_period(revenue=Decimal("-500"))
        sector_dists = _make_sector_distributions()

        # Simulate 20% of sector flagged (above 15% threshold)
        flagged_tickers = {"AAPL", "MSFT", "NVDA", "GOOG"}  # 4 of 20 = 20%

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values={"income_statement.revenue": 1000.0},
            prior_valid_values=None,
            sector_ticker_count=20,
            sector_flagged_tickers=flagged_tickers,
        )

        assert result.breadth_suspended is True
        assert len(result.detections) >= 1
        assert result.corrections == []

    def test_no_breadth_suspension_when_below_threshold(self) -> None:
        pipeline = HealingPipeline()
        period = _make_period(revenue=Decimal("-500"))
        sector_dists = _make_sector_distributions()

        # 2 of 100 = 2%, well below 15% threshold
        flagged_tickers = {"AAPL", "MSFT"}

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values={"income_statement.revenue": 1000.0},
            prior_valid_values=None,
            sector_ticker_count=100,
            sector_flagged_tickers=flagged_tickers,
        )

        assert result.breadth_suspended is False
        # Corrections should be present since breadth is not suspended
        assert len(result.corrections) >= 1


# ---------------------------------------------------------------------------
# Test: field value extraction
# ---------------------------------------------------------------------------


class TestFieldValueExtraction:
    """_extract_field_values correctly extracts fields and skips when revenue=0."""

    def test_extract_normal_values(self) -> None:
        pipeline = HealingPipeline()
        period = _make_period(
            revenue=Decimal("1000"),
            gross_profit=Decimal("400"),
            net_income=Decimal("200"),
            current_assets=Decimal("2000"),
            current_liabilities=Decimal("1000"),
            long_term_debt=Decimal("500"),
            total_equity=Decimal("3000"),
        )

        values = pipeline._extract_field_values(period)

        assert "income_statement.gross_margin" in values
        assert "income_statement.net_margin" in values
        assert "balance_sheet.debt_to_equity" in values
        assert "balance_sheet.current_ratio" in values
        assert abs(values["income_statement.gross_margin"] - 0.40) < 0.01
        assert abs(values["income_statement.net_margin"] - 0.20) < 0.01

    def test_extract_skips_margins_when_revenue_zero(self) -> None:
        pipeline = HealingPipeline()
        period = _make_period(revenue=Decimal("0"))

        values = pipeline._extract_field_values(period)

        assert "income_statement.gross_margin" not in values
        assert "income_statement.net_margin" not in values
        # Balance sheet fields should still be present
        assert "balance_sheet.debt_to_equity" in values
        assert "balance_sheet.current_ratio" in values


# ---------------------------------------------------------------------------
# Test: correction applied to period
# ---------------------------------------------------------------------------


class TestCorrectionAppliedToPeriod:
    """Corrections modify the returned period (on a copy, not the original)."""

    def test_original_period_not_mutated(self) -> None:
        pipeline = HealingPipeline()
        period = _make_period(revenue=Decimal("-500"))
        sector_dists = _make_sector_distributions()

        result = pipeline.heal(
            period=period,
            sector="Information Technology",
            sector_distributions=sector_dists,
            prior_sector_distributions=sector_dists,
            ticker_history={},
            secondary_values={"income_statement.revenue": 1000.0},
            prior_valid_values=None,
        )

        # Original period should be unchanged
        assert period.current_income.revenue == Decimal("-500")
        # Result period should have correction applied
        if result.corrections:
            rev_corr = [
                c for c in result.corrections if c.field_path == "income_statement.revenue"
            ]
            if rev_corr:
                # The result period should have the corrected value
                assert result.period.current_income.revenue != Decimal("-500")


# ---------------------------------------------------------------------------
# Test: HealingResult model structure
# ---------------------------------------------------------------------------


class TestHealingResultModel:
    """HealingResult model has expected fields and defaults."""

    def test_default_healing_result(self) -> None:
        period = _make_period()
        result = HealingResult(period=period)

        assert result.period is period
        assert result.detections == []
        assert result.corrections == []
        assert result.excluded is False
        assert result.breadth_suspended is False

    def test_healing_result_with_all_fields(self) -> None:
        from margin_engine.healing.models import (
            CorrectionEvent,
            CorrectionMethod,
            DetectionResult,
            DetectionSeverity,
        )

        period = _make_period()
        detection = DetectionResult(
            field_path="income_statement.revenue",
            severity=DetectionSeverity.IMPOSSIBLE,
            detail="test",
            original_value=-500.0,
        )
        correction = CorrectionEvent(
            field_path="income_statement.revenue",
            detection_severity=DetectionSeverity.IMPOSSIBLE,
            detection_detail="test",
            original_value=-500.0,
            corrected_value=1000.0,
            correction_method=CorrectionMethod.L1_SUBSTITUTE,
            correction_source="test",
            correction_confidence=0.9,
        )

        result = HealingResult(
            period=period,
            detections=[detection],
            corrections=[correction],
            excluded=False,
            breadth_suspended=False,
        )

        assert len(result.detections) == 1
        assert len(result.corrections) == 1


# ---------------------------------------------------------------------------
# Test: pipeline with default config
# ---------------------------------------------------------------------------


class TestPipelineDefaultConfig:
    """Pipeline should use HealingConfig defaults when no config is provided."""

    def test_default_config(self) -> None:
        pipeline = HealingPipeline()
        assert pipeline.config is not None
        assert isinstance(pipeline.config, HealingConfig)
        assert pipeline.config.version == "1.0.0"

    def test_custom_config(self) -> None:
        config = HealingConfig(sector_breadth_threshold=0.25)
        pipeline = HealingPipeline(config=config)
        assert pipeline.config.sector_breadth_threshold == 0.25
