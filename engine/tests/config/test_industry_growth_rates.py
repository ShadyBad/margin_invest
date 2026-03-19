"""Tests for industry growth rates configuration."""

from __future__ import annotations

import pytest
from margin_engine.config.industry_growth_rates import (
    INDUSTRY_GROWTH_RATES,
    IndustryGrowthRate,
    get_industry_growth_rate,
)


class TestIndustryGrowthRateModel:
    def test_model_has_required_fields(self):
        igr = IndustryGrowthRate(rate=0.12, last_updated="2026-01-01")
        assert igr.rate == pytest.approx(0.12)
        assert igr.last_updated == "2026-01-01"

    def test_model_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(IndustryGrowthRate, BaseModel)


class TestKnownIndustries:
    def test_cloud_computing(self):
        assert get_industry_growth_rate("cloud_computing") == pytest.approx(0.15)

    def test_cybersecurity(self):
        assert get_industry_growth_rate("cybersecurity") == pytest.approx(0.12)

    def test_electric_vehicles(self):
        assert get_industry_growth_rate("electric_vehicles") == pytest.approx(0.25)

    def test_traditional_auto(self):
        assert get_industry_growth_rate("traditional_auto") == pytest.approx(0.02)

    def test_payments(self):
        assert get_industry_growth_rate("payments") == pytest.approx(0.10)

    def test_enterprise_software(self):
        assert get_industry_growth_rate("enterprise_software") == pytest.approx(0.08)

    def test_ai_ml(self):
        assert get_industry_growth_rate("ai_ml") == pytest.approx(0.20)

    def test_quantum_computing(self):
        assert get_industry_growth_rate("quantum_computing") == pytest.approx(0.30)

    def test_traditional_energy(self):
        assert get_industry_growth_rate("traditional_energy") == pytest.approx(0.01)

    def test_climate_tech(self):
        assert get_industry_growth_rate("climate_tech") == pytest.approx(0.18)

    def test_neobanking(self):
        assert get_industry_growth_rate("neobanking") == pytest.approx(0.15)

    def test_consumer_staples(self):
        assert get_industry_growth_rate("consumer_staples") == pytest.approx(0.03)


class TestFallback:
    def test_unknown_industry_returns_default(self):
        assert get_industry_growth_rate("unknown_industry") == pytest.approx(0.05)

    def test_empty_string_returns_default(self):
        assert get_industry_growth_rate("") == pytest.approx(0.05)

    def test_case_sensitive_fallback(self):
        # Keys are lowercase; mixed case should fallback
        assert get_industry_growth_rate("Cloud_Computing") == pytest.approx(0.05)


class TestCoverage:
    def test_at_least_50_industries(self):
        assert len(INDUSTRY_GROWTH_RATES) >= 50

    def test_all_rates_positive(self):
        for name, entry in INDUSTRY_GROWTH_RATES.items():
            assert entry.rate > 0, f"{name} has non-positive rate {entry.rate}"

    def test_all_rates_reasonable(self):
        """No rate should exceed 100% annual growth."""
        for name, entry in INDUSTRY_GROWTH_RATES.items():
            assert entry.rate < 1.0, f"{name} rate {entry.rate} >= 1.0 seems unreasonable"

    def test_all_last_updated_set(self):
        for name, entry in INDUSTRY_GROWTH_RATES.items():
            assert entry.last_updated, f"{name} missing last_updated"

    def test_specific_industries_present(self):
        required = [
            "cloud_computing",
            "cybersecurity",
            "electric_vehicles",
            "ai_ml",
            "quantum_computing",
            "climate_tech",
            "neobanking",
            "digital_payments",
            "supply_chain_tech",
        ]
        for ind in required:
            assert ind in INDUSTRY_GROWTH_RATES, f"{ind} missing from config"
