"""Tests for conviction threshold configuration loading."""

from pathlib import Path

from margin_engine.config.threshold_config import (
    ThresholdConfig,
    TrackAThresholds,
    TrackBThresholds,
    load_threshold_config,
)


class TestThresholdConfigDefaults:
    """Default values must match the previous hardcoded constants."""

    def test_track_a_exceptional_thresholds(self):
        config = ThresholdConfig()
        assert config.track_a.exceptional_power == 0.15
        assert config.track_a.exceptional_moat == 3
        assert config.track_a.exceptional_gap == 0.08

    def test_track_a_high_thresholds(self):
        config = ThresholdConfig()
        assert config.track_a.high_power == 0.08
        assert config.track_a.high_moat == 2
        assert config.track_a.high_gap == 0.03

    def test_track_a_medium_thresholds(self):
        config = ThresholdConfig()
        assert config.track_a.medium_power == 0.04
        assert config.track_a.medium_moat == 2

    def test_track_a_gate_thresholds(self):
        config = ThresholdConfig()
        assert config.track_a.min_gates_full == 4
        assert config.track_a.min_gates_medium == 3

    def test_track_b_exceptional_thresholds(self):
        config = ThresholdConfig()
        assert config.track_b.exceptional_asymmetry == 5.0
        assert config.track_b.exceptional_catalyst == 55.0
        assert config.track_b.exceptional_converging == 4

    def test_track_b_high_thresholds(self):
        config = ThresholdConfig()
        assert config.track_b.high_asymmetry == 3.0
        assert config.track_b.high_catalyst == 40.0
        assert config.track_b.high_converging == 3

    def test_track_b_medium_thresholds(self):
        config = ThresholdConfig()
        assert config.track_b.medium_asymmetry == 1.5

    def test_track_b_gate_thresholds(self):
        config = ThresholdConfig()
        assert config.track_b.min_gates_full == 4
        assert config.track_b.min_gates_medium == 3

    def test_hysteresis_buffer(self):
        config = ThresholdConfig()
        assert config.hysteresis_buffer == 0.10

    def test_all_20_constants_accounted_for(self):
        """Verify that all 20 original constants are represented in the config."""
        config = ThresholdConfig()
        # Track A: 10 values
        assert isinstance(config.track_a, TrackAThresholds)
        assert len(TrackAThresholds.model_fields) == 10

        # Track B: 9 values
        assert isinstance(config.track_b, TrackBThresholds)
        assert len(TrackBThresholds.model_fields) == 9

        # Plus hysteresis_buffer = 20 total


class TestYAMLLoadingPartialOverride:
    """YAML with only some values should override those and keep defaults."""

    def test_partial_track_a_override(self, tmp_path: Path):
        yaml_content = """
track_a:
  exceptional_power: 0.20
  high_gap: 0.05
"""
        yaml_file = tmp_path / "thresholds.yaml"
        yaml_file.write_text(yaml_content)
        config = load_threshold_config(yaml_file)

        # Overridden values
        assert config.track_a.exceptional_power == 0.20
        assert config.track_a.high_gap == 0.05

        # Defaults preserved within track_a
        assert config.track_a.exceptional_moat == 3
        assert config.track_a.exceptional_gap == 0.08
        assert config.track_a.medium_power == 0.04

        # Track B completely untouched
        assert config.track_b.exceptional_asymmetry == 5.0
        assert config.track_b.high_catalyst == 40.0

        # Hysteresis untouched
        assert config.hysteresis_buffer == 0.10

    def test_partial_track_b_override(self, tmp_path: Path):
        yaml_content = """
track_b:
  exceptional_asymmetry: 6.0
  medium_asymmetry: 2.0
"""
        yaml_file = tmp_path / "thresholds.yaml"
        yaml_file.write_text(yaml_content)
        config = load_threshold_config(yaml_file)

        assert config.track_b.exceptional_asymmetry == 6.0
        assert config.track_b.medium_asymmetry == 2.0
        # Defaults preserved
        assert config.track_b.high_catalyst == 40.0
        assert config.track_a.exceptional_power == 0.15

    def test_hysteresis_only_override(self, tmp_path: Path):
        yaml_content = """
hysteresis_buffer: 0.15
"""
        yaml_file = tmp_path / "thresholds.yaml"
        yaml_file.write_text(yaml_content)
        config = load_threshold_config(yaml_file)

        assert config.hysteresis_buffer == 0.15
        # All track thresholds untouched
        assert config.track_a.exceptional_power == 0.15
        assert config.track_b.exceptional_asymmetry == 5.0


class TestYAMLLoadingFullOverride:
    """YAML with all values overridden should use all overridden values."""

    def test_full_override(self, tmp_path: Path):
        yaml_content = """
track_a:
  exceptional_power: 0.20
  exceptional_moat: 4
  exceptional_gap: 0.10
  high_power: 0.10
  high_moat: 3
  high_gap: 0.05
  medium_power: 0.06
  medium_moat: 3
  min_gates_full: 5
  min_gates_medium: 4
track_b:
  exceptional_asymmetry: 6.0
  exceptional_catalyst: 60.0
  exceptional_converging: 5
  high_asymmetry: 4.0
  high_catalyst: 50.0
  high_converging: 4
  medium_asymmetry: 2.0
  min_gates_full: 5
  min_gates_medium: 4
hysteresis_buffer: 0.15
"""
        yaml_file = tmp_path / "thresholds.yaml"
        yaml_file.write_text(yaml_content)
        config = load_threshold_config(yaml_file)

        assert config.track_a.exceptional_power == 0.20
        assert config.track_a.exceptional_moat == 4
        assert config.track_a.exceptional_gap == 0.10
        assert config.track_a.high_power == 0.10
        assert config.track_a.high_moat == 3
        assert config.track_a.high_gap == 0.05
        assert config.track_a.medium_power == 0.06
        assert config.track_a.medium_moat == 3
        assert config.track_a.min_gates_full == 5
        assert config.track_a.min_gates_medium == 4

        assert config.track_b.exceptional_asymmetry == 6.0
        assert config.track_b.exceptional_catalyst == 60.0
        assert config.track_b.exceptional_converging == 5
        assert config.track_b.high_asymmetry == 4.0
        assert config.track_b.high_catalyst == 50.0
        assert config.track_b.high_converging == 4
        assert config.track_b.medium_asymmetry == 2.0
        assert config.track_b.min_gates_full == 5
        assert config.track_b.min_gates_medium == 4

        assert config.hysteresis_buffer == 0.15


class TestMissingAndEmptyYAML:
    """Edge cases for file loading."""

    def test_missing_file_returns_defaults(self):
        config = load_threshold_config(Path("/nonexistent/path/thresholds.yaml"))
        assert config.track_a.exceptional_power == 0.15
        assert config.track_b.exceptional_asymmetry == 5.0
        assert config.hysteresis_buffer == 0.10

    def test_none_path_returns_defaults(self):
        config = load_threshold_config(None)
        assert config.track_a.exceptional_power == 0.15
        assert config.track_b.exceptional_asymmetry == 5.0
        assert config.hysteresis_buffer == 0.10

    def test_empty_file_returns_defaults(self, tmp_path: Path):
        yaml_file = tmp_path / "thresholds.yaml"
        yaml_file.write_text("")
        config = load_threshold_config(yaml_file)
        assert config.track_a.exceptional_power == 0.15
        assert config.track_b.exceptional_asymmetry == 5.0
        assert config.hysteresis_buffer == 0.10

    def test_empty_yaml_document_returns_defaults(self, tmp_path: Path):
        yaml_file = tmp_path / "thresholds.yaml"
        yaml_file.write_text("---\n")
        config = load_threshold_config(yaml_file)
        assert config.track_a.exceptional_power == 0.15
