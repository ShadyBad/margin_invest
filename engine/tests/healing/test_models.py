"""Tests for self-healing data layer models."""

from __future__ import annotations

from margin_engine.healing.models import (
    EXCLUDED_FIELDS,
    FIELD_CLASS_MAP,
    CorrectionEvent,
    CorrectionMethod,
    DetectionResult,
    DetectionSeverity,
    FieldClass,
    HealingConfig,
    SectorDistribution,
)


class TestDetectionSeverity:
    def test_enum_values(self) -> None:
        assert DetectionSeverity.IMPOSSIBLE == "IMPOSSIBLE"
        assert DetectionSeverity.OUTLIER == "OUTLIER"
        assert DetectionSeverity.SUSPICIOUS == "SUSPICIOUS"

    def test_all_members(self) -> None:
        members = set(DetectionSeverity)
        assert members == {
            DetectionSeverity.IMPOSSIBLE,
            DetectionSeverity.OUTLIER,
            DetectionSeverity.SUSPICIOUS,
        }


class TestCorrectionMethod:
    def test_enum_values(self) -> None:
        assert CorrectionMethod.L1_SUBSTITUTE == "L1_SUBSTITUTE"
        assert CorrectionMethod.L2_CARRY_FORWARD == "L2_CARRY_FORWARD"
        assert CorrectionMethod.L3_SECTOR_MEDIAN == "L3_SECTOR_MEDIAN"

    def test_all_members(self) -> None:
        members = set(CorrectionMethod)
        assert members == {
            CorrectionMethod.L1_SUBSTITUTE,
            CorrectionMethod.L2_CARRY_FORWARD,
            CorrectionMethod.L3_SECTOR_MEDIAN,
        }


class TestFieldClass:
    def test_enum_values(self) -> None:
        assert FieldClass.MARGINS == "MARGINS"
        assert FieldClass.GROWTH_RATES == "GROWTH_RATES"
        assert FieldClass.LEVERAGE_RATIOS == "LEVERAGE_RATIOS"
        assert FieldClass.PRICE_RETURNS == "PRICE_RETURNS"

    def test_all_members(self) -> None:
        members = set(FieldClass)
        assert members == {
            FieldClass.MARGINS,
            FieldClass.GROWTH_RATES,
            FieldClass.LEVERAGE_RATIOS,
            FieldClass.PRICE_RETURNS,
        }


class TestFieldClassMap:
    def test_margin_fields(self) -> None:
        assert FIELD_CLASS_MAP["income_statement.gross_margin"] == FieldClass.MARGINS
        assert FIELD_CLASS_MAP["income_statement.net_margin"] == FieldClass.MARGINS
        assert FIELD_CLASS_MAP["cash_flow.fcf_margin"] == FieldClass.MARGINS

    def test_growth_rate_fields(self) -> None:
        assert FIELD_CLASS_MAP["derived.revenue_growth"] == FieldClass.GROWTH_RATES
        assert FIELD_CLASS_MAP["derived.earnings_growth"] == FieldClass.GROWTH_RATES

    def test_leverage_ratio_fields(self) -> None:
        assert FIELD_CLASS_MAP["balance_sheet.debt_to_equity"] == FieldClass.LEVERAGE_RATIOS
        assert FIELD_CLASS_MAP["derived.interest_coverage"] == FieldClass.LEVERAGE_RATIOS
        assert FIELD_CLASS_MAP["balance_sheet.current_ratio"] == FieldClass.LEVERAGE_RATIOS

    def test_all_entries_present(self) -> None:
        assert len(FIELD_CLASS_MAP) == 8


class TestExcludedFields:
    def test_is_frozenset(self) -> None:
        assert isinstance(EXCLUDED_FIELDS, frozenset)

    def test_contains_expected_fields(self) -> None:
        expected = {
            "revenue",
            "net_income",
            "operating_cash_flow",
            "free_cash_flow",
            "total_assets",
            "total_liabilities",
            "total_equity",
            "total_debt",
            "shares_outstanding",
            "market_cap",
            "price_history",
        }
        assert EXCLUDED_FIELDS == expected

    def test_count(self) -> None:
        assert len(EXCLUDED_FIELDS) == 11


class TestDetectionResult:
    def test_create_impossible(self) -> None:
        result = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.IMPOSSIBLE,
            detail="Gross margin > 100%",
            original_value=1.5,
        )
        assert result.field_path == "income_statement.gross_margin"
        assert result.severity == DetectionSeverity.IMPOSSIBLE
        assert result.detail == "Gross margin > 100%"
        assert result.original_value == 1.5
        assert result.mad_deviation is None

    def test_create_outlier_with_mad_deviation(self) -> None:
        result = DetectionResult(
            field_path="derived.revenue_growth",
            severity=DetectionSeverity.OUTLIER,
            detail="Revenue growth 12 MAD from sector median",
            original_value=5.0,
            mad_deviation=12.0,
        )
        assert result.severity == DetectionSeverity.OUTLIER
        assert result.original_value == 5.0
        assert result.mad_deviation == 12.0

    def test_create_suspicious_none_value(self) -> None:
        result = DetectionResult(
            field_path="balance_sheet.debt_to_equity",
            severity=DetectionSeverity.SUSPICIOUS,
            detail="Missing debt_to_equity for 3 consecutive quarters",
            original_value=None,
        )
        assert result.original_value is None
        assert result.mad_deviation is None


class TestCorrectionEvent:
    def test_create_l1_substitute(self) -> None:
        event = CorrectionEvent(
            field_path="income_statement.gross_margin",
            detection_severity=DetectionSeverity.IMPOSSIBLE,
            detection_detail="Gross margin > 100%",
            original_value=1.5,
            corrected_value=0.45,
            correction_method=CorrectionMethod.L1_SUBSTITUTE,
            correction_source="algebraic: gross_profit / revenue",
            correction_confidence=0.95,
        )
        assert event.correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert event.corrected_value == 0.45
        assert event.correction_confidence == 0.95
        assert event.correction_source == "algebraic: gross_profit / revenue"

    def test_create_l2_carry_forward(self) -> None:
        event = CorrectionEvent(
            field_path="derived.revenue_growth",
            detection_severity=DetectionSeverity.SUSPICIOUS,
            detection_detail="Missing revenue growth",
            original_value=None,
            corrected_value=0.12,
            correction_method=CorrectionMethod.L2_CARRY_FORWARD,
            correction_source="Q3-2024 (1 quarter back)",
            correction_confidence=0.85,
        )
        assert event.correction_method == CorrectionMethod.L2_CARRY_FORWARD
        assert event.original_value is None
        assert event.corrected_value == 0.12

    def test_create_l3_sector_median(self) -> None:
        event = CorrectionEvent(
            field_path="balance_sheet.debt_to_equity",
            detection_severity=DetectionSeverity.OUTLIER,
            detection_detail="D/E 15 MAD from sector median",
            original_value=50.0,
            corrected_value=1.2,
            correction_method=CorrectionMethod.L3_SECTOR_MEDIAN,
            correction_source="Information Technology sector median (n=45)",
            correction_confidence=0.4,
        )
        assert event.correction_method == CorrectionMethod.L3_SECTOR_MEDIAN
        assert event.corrected_value == 1.2
        assert event.correction_confidence == 0.4


class TestSectorDistribution:
    def test_create_with_all_fields(self) -> None:
        dist = SectorDistribution(
            sector="Information Technology",
            field_path="income_statement.gross_margin",
            median=0.55,
            mad=0.12,
            n_observations=45,
            period="2024-Q4",
        )
        assert dist.sector == "Information Technology"
        assert dist.field_path == "income_statement.gross_margin"
        assert dist.median == 0.55
        assert dist.mad == 0.12
        assert dist.n_observations == 45
        assert dist.period == "2024-Q4"


class TestHealingConfig:
    def test_defaults(self) -> None:
        config = HealingConfig()
        assert config.version == "1.0.0"
        assert config.tier2_mad_thresholds == {
            "margins": 6.0,
            "growth_rates": 8.0,
            "leverage_ratios": 7.0,
            "price_returns": 10.0,
        }
        assert config.tier3_self_history_multiplier == 3.0
        assert config.tier3_sector_corroboration_required is True
        assert config.carry_forward_max_quarters == 4
        assert config.carry_forward_decay_rate == 0.15
        assert config.cross_sectional_min_confidence == 0.3
        assert config.substitution_tolerance == 0.20
        assert config.sector_breadth_threshold == 0.15
        assert config.consecutive_flag_regime_shift == 2
        assert config.variance_compression_floor == 0.85
        assert config.trend_threshold_multiplier == 1.5
        assert config.excluded_fields == EXCLUDED_FIELDS

    def test_custom_thresholds(self) -> None:
        custom_thresholds = {
            "margins": 10.0,
            "growth_rates": 12.0,
            "leverage_ratios": 9.0,
            "price_returns": 15.0,
        }
        config = HealingConfig(
            tier2_mad_thresholds=custom_thresholds,
            carry_forward_max_quarters=8,
            carry_forward_decay_rate=0.25,
        )
        assert config.tier2_mad_thresholds == custom_thresholds
        assert config.carry_forward_max_quarters == 8
        assert config.carry_forward_decay_rate == 0.25
        # Other defaults unchanged
        assert config.version == "1.0.0"
        assert config.tier3_self_history_multiplier == 3.0

    def test_version_present(self) -> None:
        config = HealingConfig()
        assert isinstance(config.version, str)
        assert config.version == "1.0.0"

    def test_custom_excluded_fields(self) -> None:
        custom_excluded = frozenset({"revenue", "net_income"})
        config = HealingConfig(excluded_fields=custom_excluded)
        assert config.excluded_fields == custom_excluded
