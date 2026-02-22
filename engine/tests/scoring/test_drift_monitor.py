"""Tests for style drift monitoring."""

from margin_engine.scoring.drift_monitor import (
    check_concentration,
)


def test_no_alerts_balanced():
    """Balanced portfolio produces no alerts."""
    sector_weights = {"Technology": 0.25, "Healthcare": 0.25, "Industrials": 0.25, "Energy": 0.25}
    style_weights = {"value": 0.4, "growth": 0.3, "blend": 0.3}
    alerts = check_concentration(sector_weights, style_weights)
    assert len(alerts) == 0


def test_sector_concentration_alert():
    """Sector > 40% triggers alert."""
    sector_weights = {"Technology": 0.55, "Healthcare": 0.25, "Industrials": 0.20}
    style_weights = {"value": 0.4, "growth": 0.3, "blend": 0.3}
    alerts = check_concentration(sector_weights, style_weights)
    assert any(a.alert_type == "sector_concentration" for a in alerts)
    assert any("Technology" in a.message for a in alerts)


def test_style_concentration_alert():
    """Style > 50% triggers alert."""
    sector_weights = {"Technology": 0.30, "Healthcare": 0.70}
    style_weights = {"growth": 0.65, "value": 0.20, "blend": 0.15}
    alerts = check_concentration(sector_weights, style_weights)
    assert any(a.alert_type == "style_concentration" for a in alerts)


def test_custom_thresholds():
    """Custom thresholds should be respected."""
    sector_weights = {"Technology": 0.35}
    style_weights = {"growth": 0.45}
    alerts = check_concentration(
        sector_weights, style_weights,
        max_sector_pct=0.30, max_style_pct=0.40,
    )
    assert len(alerts) == 2
