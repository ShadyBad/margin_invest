"""Tests for filter configuration loading."""

import pytest
from margin_engine.config.filter_config import FilterConfig, load_filter_config


class TestFilterConfig:
    def test_default_config_loads(self):
        """Default config should load without a YAML file."""
        config = FilterConfig()
        assert config.liquidity.min_years_of_history == 5
        assert config.beneish.threshold == -1.78
        assert config.altman.threshold == 1.1

    def test_load_from_yaml(self, tmp_path):
        """Config should load from a YAML file."""
        yaml_content = """
liquidity:
  min_years_of_history: 3
  dollar_volume:
    mega: 100_000_000
beneish:
  threshold: -2.0
"""
        yaml_file = tmp_path / "filters.yaml"
        yaml_file.write_text(yaml_content)
        config = load_filter_config(yaml_file)
        assert config.liquidity.min_years_of_history == 3
        assert config.liquidity.dollar_volume.mega == 100_000_000
        assert config.beneish.threshold == -2.0
        # Defaults preserved for unspecified fields
        assert config.altman.threshold == 1.1

    def test_liquidity_dollar_volume_tiers(self):
        """Dollar volume has per-tier defaults."""
        config = FilterConfig()
        assert config.liquidity.dollar_volume.mega == 50_000_000
        assert config.liquidity.dollar_volume.large == 20_000_000
        assert config.liquidity.dollar_volume.mid == 5_000_000
        assert config.liquidity.dollar_volume.small == 2_000_000

    def test_sector_overrides(self):
        """Sector overrides have defaults matching current hardcoded values."""
        config = FilterConfig()
        assert config.interest_coverage.sector_overrides["information technology"] == 3.0
        assert config.interest_coverage.sector_overrides["utilities"] == 1.2
        assert config.current_ratio.sector_overrides["utilities"] == 0.6

    def test_missing_yaml_returns_defaults(self):
        """When YAML file doesn't exist, return defaults."""
        from pathlib import Path
        config = load_filter_config(Path("/nonexistent/path/filters.yaml"))
        assert config.liquidity.min_years_of_history == 5

    def test_fcf_distress_defaults(self):
        config = FilterConfig()
        assert config.fcf_distress.positive_years_required == 3
        assert config.fcf_distress.lookback_years == 5
        assert config.fcf_distress.min_fcf_margin == -0.05

    def test_market_cap_minimum_defaults(self):
        config = FilterConfig()
        assert config.liquidity.market_cap_minimum.default == 300_000_000
        assert config.liquidity.market_cap_minimum.utilities == 1_000_000_000
        assert config.liquidity.market_cap_minimum.energy == 500_000_000

    def test_altman_defaults(self):
        """Altman Z-score config has correct defaults."""
        config = FilterConfig()
        assert config.altman.threshold == 1.1
        assert config.altman.equity_tl_cap == 10.0
        assert config.altman.exempt_sectors == ["Utilities"]

    def test_position_impact_defaults(self):
        """Position impact is disabled by default."""
        config = FilterConfig()
        assert config.liquidity.position_impact.enabled is False
        assert config.liquidity.position_impact.max_days == 5
        assert config.liquidity.position_impact.participation_rate == 0.10

    def test_mediocrity_gate_defaults(self):
        """Mediocrity gate matches current hardcoded values."""
        config = FilterConfig()
        assert config.mediocrity_gate.min_roic_5yr_median == 0.08
        assert config.mediocrity_gate.gross_margin.default == 0.20
        assert config.mediocrity_gate.gross_margin.energy == 0.15
        assert config.mediocrity_gate.gross_margin.utilities == 0.10
        assert config.mediocrity_gate.fcf_positive_years == 4
        assert config.mediocrity_gate.fcf_lookback_years == 5
        assert config.mediocrity_gate.max_consecutive_revenue_decline == 3

    def test_current_ratio_defaults(self):
        """Current ratio config has correct defaults."""
        config = FilterConfig()
        assert config.current_ratio.default == 0.8
        assert config.current_ratio.sector_overrides["information technology"] == 0.8
        assert config.current_ratio.quick_ratio_rescue == 0.5
        assert config.current_ratio.max_3yr_decline_pct == 30.0

    def test_interest_coverage_defaults(self):
        """Interest coverage config has correct defaults."""
        config = FilterConfig()
        assert config.interest_coverage.default == 1.5
        assert config.interest_coverage.median_lookback_years == 3
        assert config.interest_coverage.median_minimum == 1.0

    def test_load_from_yaml_partial_override(self, tmp_path):
        """Partial YAML should override only specified fields, keeping all other defaults."""
        yaml_content = """
mediocrity_gate:
  min_roic_5yr_median: 0.10
  gross_margin:
    default: 0.25
"""
        yaml_file = tmp_path / "filters.yaml"
        yaml_file.write_text(yaml_content)
        config = load_filter_config(yaml_file)
        # Overridden values
        assert config.mediocrity_gate.min_roic_5yr_median == 0.10
        assert config.mediocrity_gate.gross_margin.default == 0.25
        # Defaults preserved within the same section
        assert config.mediocrity_gate.gross_margin.energy == 0.15
        assert config.mediocrity_gate.fcf_positive_years == 4
        # Other sections completely untouched
        assert config.beneish.threshold == -1.78

    def test_excluded_sectors_default(self):
        """Excluded sectors matches current hardcoded values."""
        config = FilterConfig()
        assert "Financials" in config.liquidity.excluded_sectors
        assert "Real Estate" in config.liquidity.excluded_sectors

    def test_liquidity_dollar_volume_window(self):
        """Dollar volume window default matches design doc."""
        config = FilterConfig()
        assert config.liquidity.dollar_volume_window_days == 60

    def test_fcf_distress_allow_positive_trend_rescue(self):
        """FCF distress config has trend rescue enabled by default."""
        config = FilterConfig()
        assert config.fcf_distress.allow_positive_trend_rescue is True
