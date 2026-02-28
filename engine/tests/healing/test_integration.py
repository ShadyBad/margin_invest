"""End-to-end integration test for the full healing pipeline."""

from decimal import Decimal

from margin_engine.healing.distributions import compute_sector_distributions
from margin_engine.healing.models import (
    CorrectionMethod,
    DetectionSeverity,
    HealingConfig,
)
from margin_engine.healing.pipeline import HealingPipeline
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)


def _make_period(revenue: int = 100_000, shares: int = 1_000_000) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2024-12-31",
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            cost_of_revenue=Decimal(str(int(revenue * 0.55))),
            gross_profit=Decimal(str(int(revenue * 0.45))),
            ebit=Decimal(str(int(revenue * 0.20))),
            net_income=Decimal(str(int(revenue * 0.15))),
            shares_outstanding=shares,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal(str(int(revenue * 2))),
            total_liabilities=Decimal(str(int(revenue * 0.8))),
            total_equity=Decimal(str(int(revenue * 1.2))),
            shares_outstanding=shares,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal(str(int(revenue * 0.20))),
            capital_expenditures=Decimal(str(int(-revenue * 0.05))),
        ),
    )


class TestFullPipelineIntegration:
    def test_clean_universe_no_corrections(self):
        """A clean 5-ticker universe produces zero corrections."""
        tickers = {
            "AAPL": _make_period(100_000),
            "MSFT": _make_period(120_000),
            "GOOGL": _make_period(90_000),
            "META": _make_period(110_000),
            "NVDA": _make_period(95_000),
        }

        # Build distributions from raw data
        raw_field_values = {}
        for ticker, period in tickers.items():
            raw_field_values[ticker] = {
                "income_statement.gross_margin": period.current_income.gross_margin,
            }
        sector_dists = compute_sector_distributions(raw_field_values, "TECHNOLOGY", "2026-Q1")

        pipeline = HealingPipeline(config=HealingConfig())
        for ticker, period in tickers.items():
            result = pipeline.heal(
                period=period,
                sector="TECHNOLOGY",
                sector_distributions=sector_dists,
                prior_sector_distributions=sector_dists,
                ticker_history={},
                secondary_values={},
                prior_valid_values={},
                sector_ticker_count=5,
                sector_flagged_tickers=set(),
            )
            assert len(result.corrections) == 0
            assert result.excluded is False

    def test_tier1_detection_with_l1_correction(self):
        """Negative revenue detected by Tier 1, corrected via L1 substitute."""
        period = _make_period(revenue=-50_000)
        pipeline = HealingPipeline(config=HealingConfig())

        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={"income_statement.revenue": 100_000.0},
            prior_valid_values={},
            sector_ticker_count=50,
            sector_flagged_tickers=set(),
        )

        assert any(d.severity == DetectionSeverity.IMPOSSIBLE for d in result.detections)
        revenue_corrections = [
            c for c in result.corrections if c.field_path == "income_statement.revenue"
        ]
        assert len(revenue_corrections) == 1
        assert revenue_corrections[0].correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert revenue_corrections[0].corrected_value == 100_000.0

    def test_excluded_field_causes_exclusion(self):
        """Zero shares (excluded field) with no L1/L2 -> ticker excluded."""
        period = _make_period(shares=0)
        pipeline = HealingPipeline(config=HealingConfig())

        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={},
            prior_valid_values={},
            sector_ticker_count=50,
            sector_flagged_tickers=set(),
        )
        assert result.excluded is True

    def test_breadth_suspension_blocks_corrections(self):
        """When >15% of sector flagged, corrections are suspended."""
        period = _make_period(revenue=-50_000)
        pipeline = HealingPipeline(config=HealingConfig())

        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={"income_statement.revenue": 100_000.0},
            prior_valid_values={},
            sector_ticker_count=10,
            sector_flagged_tickers={"A", "B", "C"},  # 30% > 15%
        )
        assert result.breadth_suspended is True
        assert len(result.corrections) == 0
        assert len(result.detections) >= 1
