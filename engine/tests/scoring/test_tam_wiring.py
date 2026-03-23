"""Tests for TAM modifier wiring in scoring pipelines."""

import pytest
from margin_engine.scoring.quantitative.tam_expansion import tam_expansion_velocity
from margin_engine.scoring.score_modifiers import tam_modifier


class TestTamWiring:
    def test_tam_with_revenue_history(self):
        """Revenue data should produce a non-1.0 modifier."""
        revenues = [
            {"revenue": 100_000_000, "year": 2023},
            {"revenue": 130_000_000, "year": 2025},
        ]
        factor = tam_expansion_velocity(revenues, industry_growth_rate=0.05)
        assert factor is not None
        modifier = tam_modifier(factor.raw_value)
        assert modifier != pytest.approx(1.0)

    def test_tam_without_revenue_history(self):
        """No revenue data means modifier is 1.0."""
        assert tam_modifier(None) == pytest.approx(1.0)

    def test_tam_single_data_point(self):
        """Single revenue point returns None, falls back to 1.0."""
        revenues = [{"revenue": 100_000_000, "year": 2024}]
        factor = tam_expansion_velocity(revenues, industry_growth_rate=0.05)
        assert factor is None
        assert tam_modifier(None) == pytest.approx(1.0)
