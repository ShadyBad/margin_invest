"""Tests for Kelly integration into v3_position_sizing.

Verifies kelly_position_size_or_fallback() uses Kelly when tier_stats
has n_positions >= 10, and falls back to the fixed _SIZING table otherwise.
"""

from __future__ import annotations

import pytest
from margin_engine.backtesting.models import TierStats
from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.v3_position_sizing import (
    _SIZING,
    kelly_position_size_or_fallback,
)


def _make_tier_stats(
    tier: str,
    n_positions: int = 30,
    win_rate: float = 0.60,
    avg_winner_return: float = 0.20,
    avg_loser_return: float = 0.10,
) -> TierStats:
    return TierStats(
        tier=tier,
        win_rate=win_rate,
        avg_winner_return=avg_winner_return,
        avg_loser_return=avg_loser_return,
        n_positions=n_positions,
    )


class TestKellyFallbackWithStats:
    """With sufficient data (n >= 10), Kelly result is used."""

    def test_with_stats_returns_kelly_result(self):
        """n=30, p=0.60, gain=0.20, loss=0.10 → Kelly=10.0% (well under cap)."""
        stats = [_make_tier_stats("exceptional", n_positions=30)]
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=stats,
        )
        # b=2.0, f*=0.40, fractional=0.25*0.40*100=10.0
        assert result == pytest.approx(10.0, rel=1e-9)

    def test_with_stats_n_equals_10_uses_kelly(self):
        """Exactly n=10 is the threshold — should use Kelly."""
        stats = [_make_tier_stats("exceptional", n_positions=10)]
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=stats,
        )
        assert result == pytest.approx(10.0, rel=1e-9)

    def test_kelly_result_respects_15_pct_cap(self):
        """Very high Kelly edge capped at 15%."""
        stats = [
            _make_tier_stats(
                "exceptional",
                n_positions=50,
                win_rate=0.9,
                avg_winner_return=0.50,
                avg_loser_return=0.05,
            )
        ]
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=stats,
        )
        assert result == 15.0

    def test_negative_kelly_edge_falls_back_to_fixed(self):
        """Negative Kelly edge (p=0.30, gain=0.10, loss=0.20) → 0.0 from Kelly
        but fixed table value for EXCEPTIONAL is non-zero."""
        stats = [
            _make_tier_stats(
                "exceptional",
                n_positions=30,
                win_rate=0.30,
                avg_winner_return=0.10,
                avg_loser_return=0.20,
            )
        ]
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=stats,
        )
        # Kelly yields 0.0 for negative edge
        assert result == 0.0


class TestKellyFallbackWithoutStats:
    """Without stats (None), falls back to fixed _SIZING table."""

    def test_no_stats_returns_fixed_exceptional_compounder(self):
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=None,
        )
        assert result == _SIZING["compounder"][CompositeTier.EXCEPTIONAL]

    def test_no_stats_returns_fixed_high_mispricing(self):
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.HIGH,
            opportunity_type="mispricing",
            tier_stats=None,
        )
        assert result == _SIZING["mispricing"][CompositeTier.HIGH]

    def test_no_stats_returns_fixed_medium_both(self):
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.MEDIUM,
            opportunity_type="both",
            tier_stats=None,
        )
        assert result == _SIZING["both"][CompositeTier.MEDIUM]

    def test_no_stats_none_tier_returns_zero(self):
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.NONE,
            opportunity_type="compounder",
            tier_stats=None,
        )
        assert result == 0.0


class TestKellyFallbackInsufficientData:
    """With stats but n < 10, falls back to fixed table."""

    def test_n_9_falls_back(self):
        stats = [_make_tier_stats("exceptional", n_positions=9)]
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=stats,
        )
        assert result == _SIZING["compounder"][CompositeTier.EXCEPTIONAL]

    def test_n_1_falls_back(self):
        stats = [_make_tier_stats("exceptional", n_positions=1)]
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=stats,
        )
        assert result == _SIZING["compounder"][CompositeTier.EXCEPTIONAL]

    def test_empty_stats_list_falls_back(self):
        """tier_stats=[] (no entries) falls back to fixed table."""
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=[],
        )
        assert result == _SIZING["compounder"][CompositeTier.EXCEPTIONAL]

    def test_stats_for_different_tier_falls_back(self):
        """If tier_stats has data for 'high' but we ask for 'exceptional', fall back."""
        stats = [_make_tier_stats("high", n_positions=30)]
        result = kelly_position_size_or_fallback(
            tier=CompositeTier.EXCEPTIONAL,
            opportunity_type="compounder",
            tier_stats=stats,
        )
        assert result == _SIZING["compounder"][CompositeTier.EXCEPTIONAL]
