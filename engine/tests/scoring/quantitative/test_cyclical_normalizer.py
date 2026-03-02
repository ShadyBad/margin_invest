import pytest
from margin_engine.scoring.quantitative.cyclical_normalizer import normalize_metric


class TestNormalizeMetric:
    def test_non_cyclical_returns_current(self):
        """Non-cyclical companies use current value unchanged."""
        result, detail = normalize_metric(
            current_value=100.0,
            historical_values=[80.0, 90.0, 100.0, 110.0, 120.0, 130.0, 140.0],
            is_cyclical=False,
        )
        assert result == 100.0
        assert "current" in detail.lower()

    def test_cyclical_uses_7yr_median(self):
        """Cyclical company uses 7-year median."""
        # Sorted: [30, 40, 50, 60, 120, 130, 150] -> median = 60
        values = [50.0, 120.0, 30.0, 150.0, 40.0, 130.0, 60.0]
        result, detail = normalize_metric(
            current_value=150.0,
            historical_values=values,
            is_cyclical=True,
        )
        assert result == pytest.approx(60.0, abs=1.0)
        assert "median" in detail.lower()

    def test_cyclical_insufficient_history_uses_current(self):
        """Cyclical with <3 years falls back to current."""
        result, detail = normalize_metric(
            current_value=100.0,
            historical_values=[90.0, 110.0],
            is_cyclical=True,
        )
        assert result == 100.0

    def test_cyclical_at_trough(self):
        """At trough, normalized value should be higher than current."""
        values = [100.0, 120.0, 130.0, 110.0, 90.0, 140.0, 80.0]
        result, _ = normalize_metric(
            current_value=30.0,
            historical_values=values,
            is_cyclical=True,
        )
        assert result > 30.0

    def test_cyclical_at_peak(self):
        """At peak, normalized value should be lower than current."""
        values = [50.0, 60.0, 70.0, 80.0, 65.0, 55.0, 75.0]
        # Median of sorted [50, 55, 60, 65, 70, 75, 80] = 65
        result, _ = normalize_metric(
            current_value=200.0,
            historical_values=values,
            is_cyclical=True,
        )
        assert result < 200.0
        assert result == pytest.approx(65.0, abs=1.0)

    def test_filters_negative_values(self):
        """Negative values in history should be filtered out."""
        values = [-50.0, -20.0, 100.0, 120.0, 130.0, 110.0, 90.0]
        result, detail = normalize_metric(
            current_value=130.0,
            historical_values=values,
            is_cyclical=True,
        )
        # Only positive values: [100, 120, 130, 110, 90] -> median = 110
        assert result == pytest.approx(110.0, abs=1.0)

    def test_all_negative_history_uses_current(self):
        """If all historical values are negative, fall back to current."""
        result, _ = normalize_metric(
            current_value=50.0,
            historical_values=[-10.0, -20.0, -30.0, -15.0],
            is_cyclical=True,
        )
        assert result == 50.0

    def test_lookback_window_limits(self):
        """With >7 years of data, only last 7 are used."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        result, _ = normalize_metric(
            current_value=100.0,
            historical_values=values,
            is_cyclical=True,
            lookback=7,
        )
        # Last 7: [40, 50, 60, 70, 80, 90, 100] -> median = 70
        assert result == pytest.approx(70.0, abs=1.0)

    def test_custom_lookback(self):
        """Custom lookback period works."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result, _ = normalize_metric(
            current_value=50.0,
            historical_values=values,
            is_cyclical=True,
            lookback=3,
        )
        # Last 3: [30, 40, 50] -> median = 40
        assert result == pytest.approx(40.0, abs=1.0)
