"""Integration tests for value factor scoring."""

import pytest
from margin_engine.scoring.quantitative import (
    acquirers_multiple,
    dcf_margin_of_safety,
    ev_fcf,
    shareholder_yield,
)

from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE


class TestValueFactorIntegration:
    def test_all_value_factors_compute(self):
        """All 4 value sub-factors compute without error for Apple."""
        market_cap = APPLE_PROFILE.market_cap

        ev = ev_fcf(APPLE_PERIOD_2024, market_cap)
        sy = shareholder_yield(APPLE_PERIOD_2024, market_cap)
        dcf = dcf_margin_of_safety(
            APPLE_PERIOD_2024,
            market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
        )
        am = acquirers_multiple(APPLE_PERIOD_2024, market_cap)

        assert ev.name == "ev_fcf"
        assert sy.name == "shareholder_yield"
        assert dcf.name == "dcf_margin_of_safety"
        assert am.name == "acquirers_multiple"

    def test_apple_golden_values(self):
        """Verify all Apple golden values."""
        market_cap = APPLE_PROFILE.market_cap

        ev = ev_fcf(APPLE_PERIOD_2024, market_cap)
        sy = shareholder_yield(APPLE_PERIOD_2024, market_cap)
        dcf = dcf_margin_of_safety(
            APPLE_PERIOD_2024,
            market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
        )
        am = acquirers_multiple(APPLE_PERIOD_2024, market_cap)

        assert ev.raw_value == pytest.approx(33.1294, rel=1e-3)
        assert sy.raw_value == pytest.approx(0.0315, rel=1e-2)
        assert dcf.raw_value == pytest.approx(-0.9713, rel=1e-2)
        assert am.raw_value == pytest.approx(29.2708, rel=1e-3)

    def test_all_percentiles_are_placeholders(self):
        """All percentile_ranks should be 0.0 (filled in Phase 6)."""
        market_cap = APPLE_PROFILE.market_cap

        ev = ev_fcf(APPLE_PERIOD_2024, market_cap)
        sy = shareholder_yield(APPLE_PERIOD_2024, market_cap)
        dcf = dcf_margin_of_safety(
            APPLE_PERIOD_2024,
            market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
        )
        am = acquirers_multiple(APPLE_PERIOD_2024, market_cap)

        for score in [ev, sy, dcf, am]:
            assert score.percentile_rank == 0.0, f"{score.name} percentile should be 0.0"

    def test_all_have_detail(self):
        """All value factors should include non-empty detail strings."""
        market_cap = APPLE_PROFILE.market_cap

        ev = ev_fcf(APPLE_PERIOD_2024, market_cap)
        sy = shareholder_yield(APPLE_PERIOD_2024, market_cap)
        dcf = dcf_margin_of_safety(
            APPLE_PERIOD_2024,
            market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
        )
        am = acquirers_multiple(APPLE_PERIOD_2024, market_cap)

        for score in [ev, sy, dcf, am]:
            assert len(score.detail) > 0, f"{score.name} should have detail"

    def test_imports_from_package(self):
        """All 4 value functions importable from margin_engine.scoring.quantitative."""
        from margin_engine.scoring.quantitative import acquirers_multiple as am
        from margin_engine.scoring.quantitative import dcf_margin_of_safety as dcf
        from margin_engine.scoring.quantitative import ev_fcf as ef
        from margin_engine.scoring.quantitative import shareholder_yield as sy

        assert callable(ef)
        assert callable(sy)
        assert callable(dcf)
        assert callable(am)
