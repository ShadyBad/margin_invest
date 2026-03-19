"""Tests for ML ensemble override (promote/demote conviction by one level)."""

from margin_engine.ml.ensemble_override import OverrideConfig, apply_ml_override, demote, promote
from margin_engine.models.scoring import CompositeTier

# Helper: universe where the given value is at a known percentile.
# 100 values from 0.01 to 1.0 make percentile calculation straightforward.
_UNIVERSE = [i / 100.0 for i in range(1, 101)]  # 0.01 .. 1.00


class TestApplyMlOverride:
    """Tests for apply_ml_override()."""

    def test_no_override_when_model_not_qualified(self) -> None:
        """model_qualifies=False -> conviction unchanged, override_type='none'."""
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.HIGH,
            ml_alpha=0.95,
            vae_mean=0.90,
            vae_variance=0.10,  # high confidence
            model_qualifies=False,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.HIGH
        assert override_type == "none"

    def test_no_override_when_low_confidence(self) -> None:
        """vae_variance=0.50 -> confidence=0.50 < 0.60 -> unchanged."""
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.MEDIUM,
            ml_alpha=0.95,
            vae_mean=0.90,
            vae_variance=0.50,  # confidence = 1.0 - 0.50 = 0.50 < 0.60
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.MEDIUM
        assert override_type == "none"

    def test_promote_when_high_percentile_and_confident(self) -> None:
        """ml_percentile >= 85 AND confidence >= 0.75 -> promote one level."""
        # With composite=0, gbm_weight=0.60, vae_weight=0.40:
        # ml_signal = 0 * 0.0 + 0.60 * 0.95 + 0.40 * 0.90 = 0.57 + 0.36 = 0.93
        # In _UNIVERSE (0.01..1.00), values < 0.93: 0.01..0.92 = 92 values
        # ml_percentile = 92/100*100 = 92 >= 85 -> promote
        # confidence = 1.0 - 0.10 = 0.90 >= 0.75
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.MEDIUM,
            ml_alpha=0.95,
            vae_mean=0.90,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.HIGH
        assert override_type == "promoted"

    def test_demote_when_low_percentile_and_confident(self) -> None:
        """ml_percentile <= 5 AND confidence >= 0.80 -> demote two levels (HIGH -> NONE)."""
        # ml_signal = 0 * 0.0 + 0.60 * 0.05 + 0.40 * 0.03 = 0.03 + 0.012 = 0.042
        # values < 0.042: 0.01..0.04 = 4 values
        # ml_percentile = 4/100*100 = 4 <= 5 (bottom_2_percentile)
        # confidence = 1.0 - 0.10 = 0.90 >= 0.80 (min_confidence_2)
        # -> 2-level path fires: HIGH demoted 2 levels -> NONE
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.HIGH,
            ml_alpha=0.05,
            vae_mean=0.03,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.NONE
        assert override_type == "demoted"

    def test_promote_exceptional_stays_exceptional(self) -> None:
        """Cannot promote above EXCEPTIONAL."""
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.EXCEPTIONAL,
            ml_alpha=0.95,
            vae_mean=0.90,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.EXCEPTIONAL
        assert override_type == "none"

    def test_demote_none_stays_none(self) -> None:
        """Cannot demote below NONE."""
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.NONE,
            ml_alpha=0.05,
            vae_mean=0.03,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.NONE
        assert override_type == "none"

    def test_no_override_mid_percentile(self) -> None:
        """Percentile between 15 and 85 -> no override."""
        # ml_signal = 0 * 0.0 + 0.60 * 0.50 + 0.40 * 0.50 = 0.30 + 0.20 = 0.50
        # values < 0.50: 0.01..0.49 = 49 values
        # ml_percentile = 49/100*100 = 49 -> no override
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.HIGH,
            ml_alpha=0.50,
            vae_mean=0.50,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.HIGH
        assert override_type == "none"

    def test_no_promote_when_confidence_below_075(self) -> None:
        """High percentile but confidence < 0.75 -> no override."""
        # confidence = 1.0 - 0.30 = 0.70 < 0.75
        # ml_signal high enough for percentile >= 85 but confidence gate blocks
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.MEDIUM,
            ml_alpha=0.95,
            vae_mean=0.90,
            vae_variance=0.30,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.MEDIUM
        assert override_type == "none"


class TestOverrideConfig:
    """Tests for OverrideConfig dataclass defaults."""

    def test_default_values(self) -> None:
        """All 8 fields should match their specified defaults."""
        cfg = OverrideConfig()
        assert cfg.top_1_percentile == 85.0
        assert cfg.bottom_1_percentile == 15.0
        assert cfg.min_confidence_1 == 0.75
        assert cfg.top_2_percentile == 95.0
        assert cfg.bottom_2_percentile == 5.0
        assert cfg.min_confidence_2 == 0.80
        assert cfg.max_override_levels == 2
        assert cfg.early_exit_confidence == 0.60

    def test_disable_2_level(self) -> None:
        """OverrideConfig(max_override_levels=1) should be accepted."""
        cfg = OverrideConfig(max_override_levels=1)
        assert cfg.max_override_levels == 1


class TestTwoLevelOverride:
    """Tests for 2-level ML conviction override support."""

    def test_2_level_promote_top_5_high_confidence(self) -> None:
        """Top 5% + confidence >= 0.80 -> promote 2 levels (MEDIUM -> EXCEPTIONAL)."""
        # ml_signal = 0.60*0.99 + 0.40*0.98 = 0.594 + 0.392 = 0.986
        # values < 0.986 in _UNIVERSE (0.01..1.00): 0.01..0.98 = 98 values
        # ml_percentile = 98/100*100 = 98 >= 95 (top_2_percentile)
        # confidence = 1.0 - 0.10 = 0.90 >= 0.80 (min_confidence_2)
        # -> promote 2 levels: MEDIUM -> EXCEPTIONAL
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.MEDIUM,
            ml_alpha=0.99,
            vae_mean=0.98,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
            config=OverrideConfig(),
        )
        assert conviction == CompositeTier.EXCEPTIONAL
        assert override_type == "promoted"

    def test_2_level_demote_bottom_5_high_confidence(self) -> None:
        """Bottom 5% + confidence >= 0.80 -> demote 2 levels (EXCEPTIONAL -> MEDIUM)."""
        # ml_signal = 0.60*0.01 + 0.40*0.01 = 0.006 + 0.004 = 0.010
        # values < 0.010 in _UNIVERSE: none (smallest is 0.01) = 0 values
        # ml_percentile = 0/100*100 = 0 <= 5 (bottom_2_percentile)
        # confidence = 1.0 - 0.10 = 0.90 >= 0.80 (min_confidence_2)
        # -> demote 2 levels: EXCEPTIONAL -> MEDIUM
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.EXCEPTIONAL,
            ml_alpha=0.01,
            vae_mean=0.01,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
            config=OverrideConfig(),
        )
        assert conviction == CompositeTier.MEDIUM
        assert override_type == "demoted"

    def test_1_level_when_confidence_between_gates(self) -> None:
        """confidence >= 0.75 but < 0.80 -> only 1-level override (MEDIUM -> HIGH)."""
        # ml_signal = 0.60*0.99 + 0.40*0.98 = 0.986, percentile = 98 >= 95
        # confidence = 1.0 - 0.24 = 0.76 >= 0.75 but < 0.80
        # 2-level gate blocked by confidence; falls through to 1-level gate
        # percentile 98 >= 85 (top_1_percentile), confidence >= 0.75
        # -> promote 1 level: MEDIUM -> HIGH
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.MEDIUM,
            ml_alpha=0.99,
            vae_mean=0.98,
            vae_variance=0.24,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
            config=OverrideConfig(),
        )
        assert conviction == CompositeTier.HIGH
        assert override_type == "promoted"

    def test_no_override_below_confidence_075(self) -> None:
        """confidence=0.70 (>= 0.60 early_exit, < 0.75 gate) -> no override."""
        # confidence = 1.0 - 0.30 = 0.70: passes early_exit (0.60) but fails both gates
        # ml_signal low enough for bottom percentile but confidence blocks both 1 and 2-level
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.HIGH,
            ml_alpha=0.01,
            vae_mean=0.01,
            vae_variance=0.30,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
            config=OverrideConfig(),
        )
        assert conviction == CompositeTier.HIGH
        assert override_type == "none"

    def test_2_level_disabled_via_config(self) -> None:
        """max_override_levels=1 disables 2-level even with high confidence + top 5%."""
        # Same inputs as test_2_level_promote_top_5_high_confidence
        # but config caps at 1 level -> MEDIUM -> HIGH (not EXCEPTIONAL)
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.MEDIUM,
            ml_alpha=0.99,
            vae_mean=0.98,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
            config=OverrideConfig(max_override_levels=1),
        )
        assert conviction == CompositeTier.HIGH
        assert override_type == "promoted"

    def test_backward_compat_no_config(self) -> None:
        """Calling without config kwarg should use default OverrideConfig."""
        # Same inputs as test_promote_when_high_percentile_and_confident
        # ml_signal = 0.60*0.95 + 0.40*0.90 = 0.57 + 0.36 = 0.93
        # percentile = 92 >= 85, confidence = 0.90 >= 0.75
        # -> promote 1 level: MEDIUM -> HIGH
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.MEDIUM,
            ml_alpha=0.95,
            vae_mean=0.90,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.HIGH
        assert override_type == "promoted"


class TestPromoteDemote:
    """Tests for promote() and demote() helpers."""

    def test_promote_one_level(self) -> None:
        """MEDIUM + 1 level = HIGH."""
        assert promote(CompositeTier.MEDIUM, 1) == CompositeTier.HIGH

    def test_promote_two_levels(self) -> None:
        """MEDIUM + 2 levels = EXCEPTIONAL."""
        assert promote(CompositeTier.MEDIUM, 2) == CompositeTier.EXCEPTIONAL

    def test_promote_capped_at_exceptional(self) -> None:
        """HIGH + 2 levels should not go out of bounds — capped at EXCEPTIONAL."""
        assert promote(CompositeTier.HIGH, 2) == CompositeTier.EXCEPTIONAL

    def test_promote_exceptional_stays(self) -> None:
        """EXCEPTIONAL + 1 level stays EXCEPTIONAL."""
        assert promote(CompositeTier.EXCEPTIONAL, 1) == CompositeTier.EXCEPTIONAL

    def test_demote_one_level(self) -> None:
        """HIGH - 1 level = MEDIUM."""
        assert demote(CompositeTier.HIGH, 1) == CompositeTier.MEDIUM

    def test_demote_two_levels(self) -> None:
        """EXCEPTIONAL - 2 levels = MEDIUM."""
        assert demote(CompositeTier.EXCEPTIONAL, 2) == CompositeTier.MEDIUM

    def test_demote_floored_at_none(self) -> None:
        """MEDIUM - 2 levels should not go out of bounds — floored at NONE."""
        assert demote(CompositeTier.MEDIUM, 2) == CompositeTier.NONE

    def test_demote_none_stays(self) -> None:
        """NONE - 1 level stays NONE."""
        assert demote(CompositeTier.NONE, 1) == CompositeTier.NONE
