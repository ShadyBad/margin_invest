"""Tests for factor availability registry."""

from datetime import date

from margin_engine.backtesting.factor_registry import (
    FactorAvailability,
    FactorRegistry,
)


class TestFactorRegistry:
    def test_available_factors_returns_all_when_after_all_dates(self):
        registry = FactorRegistry.default()
        factors = registry.available_factors(date(2026, 1, 1))
        # All factors should be available in 2026
        assert len(factors) > 10

    def test_available_factors_excludes_ml_before_2026(self):
        registry = FactorRegistry.default()
        factors = registry.available_factors(date(2020, 1, 1))
        factor_names = {f.name for f in factors}
        assert "ml_cluster_score" not in factor_names

    def test_available_factors_returns_subset_for_2006(self):
        registry = FactorRegistry.default()
        factors_2006 = registry.available_factors(date(2006, 6, 1))
        factors_2020 = registry.available_factors(date(2020, 6, 1))
        assert len(factors_2006) < len(factors_2020)

    def test_coverage_ratio(self):
        registry = FactorRegistry.default()
        ratio = registry.coverage_ratio(date(2006, 6, 1))
        assert 0.0 < ratio < 1.0
        ratio_2026 = registry.coverage_ratio(date(2026, 1, 1))
        assert ratio_2026 == 1.0

    def test_missing_factors(self):
        registry = FactorRegistry.default()
        missing = registry.missing_factors(date(2006, 6, 1))
        assert len(missing) > 0
        missing_names = {f.name for f in missing}
        assert "ml_cluster_score" in missing_names

    def test_custom_registry(self):
        entries = [
            FactorAvailability(
                name="test_factor", available_from=date(2010, 1, 1), category="quality",
            ),
            FactorAvailability(
                name="old_factor", available_from=date(2005, 1, 1), category="value",
            ),
        ]
        registry = FactorRegistry(entries)
        assert len(registry.available_factors(date(2008, 1, 1))) == 1
        assert len(registry.available_factors(date(2012, 1, 1))) == 2
