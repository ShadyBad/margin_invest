"""Tests for healing integration in the scoring service."""

from margin_api.services.scoring import build_financial_period
from margin_engine.healing.models import HealingConfig
from margin_engine.healing.pipeline import HealingPipeline, HealingResult
from margin_engine.models.financial import FinancialPeriod


class TestBuildFinancialPeriodWithHealing:
    def test_clean_data_unchanged(self):
        """Normal data passes through without modification when no pipeline."""
        income_raw = {
            "revenue": 100000,
            "ebit": 20000,
            "netIncome": 15000,
            "sharesOutstanding": 1000000,
        }
        balance_raw = {
            "totalAssets": 500000,
            "totalLiabilities": 200000,
            "totalStockholdersEquity": 300000,
        }
        cashflow_raw = {"operatingCashFlow": 25000, "capitalExpenditure": -5000}

        period = build_financial_period(
            income_raw,
            balance_raw,
            cashflow_raw,
            period_end="2024-12-31",
            filing_date="2024-12-31",
        )
        # Returns just FinancialPeriod (not a tuple) when no pipeline
        assert isinstance(period, FinancialPeriod)
        assert float(period.current_income.revenue) == 100000

    def test_negative_revenue_detected_when_healing_enabled(self):
        """When healing pipeline is provided, Tier 1 detects negative revenue."""
        income_raw = {
            "revenue": -50000,
            "ebit": 20000,
            "netIncome": 15000,
            "sharesOutstanding": 1000000,
        }
        balance_raw = {
            "totalAssets": 500000,
            "totalLiabilities": 200000,
            "totalStockholdersEquity": 300000,
        }
        cashflow_raw = {"operatingCashFlow": 25000, "capitalExpenditure": -5000}

        pipeline = HealingPipeline(config=HealingConfig())
        period, result = build_financial_period(
            income_raw,
            balance_raw,
            cashflow_raw,
            period_end="2024-12-31",
            filing_date="2024-12-31",
            healing_pipeline=pipeline,
            sector="TECHNOLOGY",
        )
        assert result is not None
        assert len(result.detections) >= 1

    def test_backward_compatible_return_type(self):
        """Without healing pipeline, returns bare FinancialPeriod (not tuple)."""
        income_raw = {
            "revenue": 100000,
            "ebit": 20000,
            "netIncome": 15000,
            "sharesOutstanding": 1000000,
        }
        balance_raw = {
            "totalAssets": 500000,
            "totalLiabilities": 200000,
            "totalStockholdersEquity": 300000,
        }
        cashflow_raw = {"operatingCashFlow": 25000, "capitalExpenditure": -5000}

        result = build_financial_period(
            income_raw,
            balance_raw,
            cashflow_raw,
            period_end="2024-12-31",
            filing_date="2024-12-31",
        )
        assert not isinstance(result, tuple)

    def test_healing_returns_tuple(self):
        """With healing pipeline, returns (FinancialPeriod, HealingResult)."""
        income_raw = {
            "revenue": 100000,
            "ebit": 20000,
            "netIncome": 15000,
            "sharesOutstanding": 1000000,
        }
        balance_raw = {
            "totalAssets": 500000,
            "totalLiabilities": 200000,
            "totalStockholdersEquity": 300000,
        }
        cashflow_raw = {"operatingCashFlow": 25000, "capitalExpenditure": -5000}

        pipeline = HealingPipeline(config=HealingConfig())
        result = build_financial_period(
            income_raw,
            balance_raw,
            cashflow_raw,
            period_end="2024-12-31",
            filing_date="2024-12-31",
            healing_pipeline=pipeline,
            sector="TECHNOLOGY",
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        period, healing_result = result
        assert isinstance(period, FinancialPeriod)
        assert isinstance(healing_result, HealingResult)

    def test_clean_data_with_healing_returns_empty_detections(self):
        """Clean data through the healing pipeline produces no detections."""
        income_raw = {
            "revenue": 100000,
            "ebit": 20000,
            "netIncome": 15000,
            "sharesOutstanding": 1000000,
        }
        balance_raw = {
            "totalAssets": 500000,
            "totalLiabilities": 200000,
            "totalStockholdersEquity": 300000,
        }
        cashflow_raw = {"operatingCashFlow": 25000, "capitalExpenditure": -5000}

        pipeline = HealingPipeline(config=HealingConfig())
        period, healing_result = build_financial_period(
            income_raw,
            balance_raw,
            cashflow_raw,
            period_end="2024-12-31",
            filing_date="2024-12-31",
            healing_pipeline=pipeline,
            sector="TECHNOLOGY",
        )
        assert healing_result.detections == []
        assert healing_result.corrections == []
        assert not healing_result.excluded
        assert not healing_result.breadth_suspended

    def test_healing_passes_sector_distributions(self):
        """Sector distributions are forwarded to the healing pipeline."""
        from margin_engine.healing.models import SectorDistribution

        income_raw = {
            "revenue": 100000,
            "ebit": 20000,
            "netIncome": 15000,
            "sharesOutstanding": 1000000,
        }
        balance_raw = {
            "totalAssets": 500000,
            "totalLiabilities": 200000,
            "totalStockholdersEquity": 300000,
        }
        cashflow_raw = {"operatingCashFlow": 25000, "capitalExpenditure": -5000}

        distributions = [
            SectorDistribution(
                sector="TECHNOLOGY",
                field_path="income_statement.gross_margin",
                median=0.5,
                mad=0.1,
                n_observations=50,
                period="2024-Q4",
            ),
        ]
        pipeline = HealingPipeline(config=HealingConfig())
        period, result = build_financial_period(
            income_raw,
            balance_raw,
            cashflow_raw,
            period_end="2024-12-31",
            filing_date="2024-12-31",
            healing_pipeline=pipeline,
            sector="TECHNOLOGY",
            sector_distributions=distributions,
        )
        # Should succeed — distributions were accepted by the pipeline
        assert isinstance(period, FinancialPeriod)
        assert isinstance(result, HealingResult)
