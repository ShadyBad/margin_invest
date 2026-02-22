"""Tests for timing overlay — momentum as entry signal, not conviction."""

from margin_engine.scoring.timing_overlay import compute_timing_signal

# ---------------------------------------------------------------------------
# Track A (Compounder) timing
# ---------------------------------------------------------------------------


class TestTrackATiming:
    """Track A uses momentum direction for entry timing."""

    def test_positive_momentum_buy_now(self):
        """Momentum >= 50 -> buy_now (momentum confirms quality)."""
        result = compute_timing_signal(
            momentum_percentile=75.0,
            is_mispricing_track=False,
        )
        assert result == "buy_now"

    def test_exactly_50_buy_now(self):
        """Boundary: momentum == 50 -> buy_now."""
        result = compute_timing_signal(
            momentum_percentile=50.0,
            is_mispricing_track=False,
        )
        assert result == "buy_now"

    def test_negative_momentum_pullback(self):
        """Momentum < 50 -> add_on_pullback (wait for better entry)."""
        result = compute_timing_signal(
            momentum_percentile=30.0,
            is_mispricing_track=False,
        )
        assert result == "add_on_pullback"

    def test_zero_momentum_pullback(self):
        """Momentum = 0 -> add_on_pullback."""
        result = compute_timing_signal(
            momentum_percentile=0.0,
            is_mispricing_track=False,
        )
        assert result == "add_on_pullback"

    def test_perfect_momentum_buy_now(self):
        """Momentum = 100 -> buy_now."""
        result = compute_timing_signal(
            momentum_percentile=100.0,
            is_mispricing_track=False,
        )
        assert result == "buy_now"


# ---------------------------------------------------------------------------
# Track B (Mispricing) timing — inverted logic
# ---------------------------------------------------------------------------


class TestTrackBTiming:
    """Track B uses inverted momentum (contrarian confirmation)."""

    def test_negative_momentum_buy_now(self):
        """Momentum < 50 -> buy_now (contrarian confirmation: beaten down)."""
        result = compute_timing_signal(
            momentum_percentile=30.0,
            is_mispricing_track=True,
        )
        assert result == "buy_now"

    def test_positive_momentum_wait(self):
        """Momentum >= 50 -> wait_for_catalyst (not contrarian enough)."""
        result = compute_timing_signal(
            momentum_percentile=70.0,
            is_mispricing_track=True,
        )
        assert result == "wait_for_catalyst"

    def test_exactly_50_wait(self):
        """Boundary: momentum == 50 -> wait_for_catalyst."""
        result = compute_timing_signal(
            momentum_percentile=50.0,
            is_mispricing_track=True,
        )
        assert result == "wait_for_catalyst"

    def test_zero_momentum_buy_now(self):
        """Momentum = 0 -> buy_now (maximum contrarian signal)."""
        result = compute_timing_signal(
            momentum_percentile=0.0,
            is_mispricing_track=True,
        )
        assert result == "buy_now"


# ---------------------------------------------------------------------------
# SUE percentile (optional, not used in current logic)
# ---------------------------------------------------------------------------


class TestSuePercentile:
    """sue_percentile is accepted but does not change current logic."""

    def test_sue_does_not_affect_track_a(self):
        result = compute_timing_signal(
            momentum_percentile=75.0,
            is_mispricing_track=False,
            sue_percentile=10.0,
        )
        assert result == "buy_now"

    def test_sue_does_not_affect_track_b(self):
        result = compute_timing_signal(
            momentum_percentile=30.0,
            is_mispricing_track=True,
            sue_percentile=90.0,
        )
        assert result == "buy_now"

    def test_sue_none_accepted(self):
        result = compute_timing_signal(
            momentum_percentile=60.0,
            is_mispricing_track=False,
            sue_percentile=None,
        )
        assert result == "buy_now"


# ---------------------------------------------------------------------------
# V3 timing signals — 3-tier Track A with accumulate_slowly
# ---------------------------------------------------------------------------


class TestV3TimingSignals:
    def test_track_a_buy_now(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal

        assert compute_v3_timing_signal(60.0, is_mispricing_track=False) == "buy_now"

    def test_track_a_add_on_pullback(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal

        assert compute_v3_timing_signal(40.0, is_mispricing_track=False) == "add_on_pullback"

    def test_track_a_accumulate_slowly(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal

        assert compute_v3_timing_signal(20.0, is_mispricing_track=False) == "accumulate_slowly"

    def test_track_b_buy_now(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal

        assert compute_v3_timing_signal(30.0, is_mispricing_track=True) == "buy_now"

    def test_track_b_wait(self):
        from margin_engine.scoring.timing_overlay import compute_v3_timing_signal

        assert compute_v3_timing_signal(60.0, is_mispricing_track=True) == "wait_for_catalyst"
