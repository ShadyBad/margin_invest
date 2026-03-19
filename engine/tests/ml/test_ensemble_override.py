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
        """ml_percentile <= 15 AND confidence >= 0.75 -> demote one level."""
        # ml_signal = 0 * 0.0 + 0.60 * 0.05 + 0.40 * 0.03 = 0.03 + 0.012 = 0.042
        # values < 0.042: 0.01..0.04 = 4 values
        # ml_percentile = 4/100*100 = 4 <= 15 -> demote
        # confidence = 1.0 - 0.10 = 0.90 >= 0.75
        conviction, override_type = apply_ml_override(
            rules_conviction=CompositeTier.HIGH,
            ml_alpha=0.05,
            vae_mean=0.03,
            vae_variance=0.10,
            model_qualifies=True,
            universe_ml_alphas=_UNIVERSE,
        )
        assert conviction == CompositeTier.MEDIUM
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
