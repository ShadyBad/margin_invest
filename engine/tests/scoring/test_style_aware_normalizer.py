"""Tests for style-aware two-stage normalization."""

from margin_engine.models.scoring import FactorScore, InvestmentStyle
from margin_engine.scoring.normalizer import (
    calibrate_cross_bucket,
    style_sector_neutral_ranks,
)


class TestStyleSectorNeutralRanks:
    def test_ranks_within_style_and_sector(self):
        """Scores ranked within (sector, style) bucket."""
        scores_by_bucket: dict[tuple[str, InvestmentStyle], list[FactorScore]] = {
            ("Technology", InvestmentStyle.GROWTH): [
                FactorScore(name="ev_fcf", raw_value=30.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=25.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=35.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=20.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=40.0, percentile_rank=0.0),
            ],
            ("Technology", InvestmentStyle.VALUE): [
                FactorScore(name="ev_fcf", raw_value=10.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=8.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=12.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=6.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=14.0, percentile_rank=0.0),
            ],
        }
        result = style_sector_neutral_ranks(scores_by_bucket, invert=True)
        assert len(result) == 10
        # Within Growth-Tech (inverted): 20 is cheapest = best percentile
        growth_scores = result[:5]
        cheapest_growth = [s for s in growth_scores if s.raw_value == 20.0][0]
        assert cheapest_growth.percentile_rank > 50.0

    def test_small_bucket_still_produces_results(self):
        """Buckets with < min_bucket_size still get ranked."""
        scores_by_bucket: dict[tuple[str, InvestmentStyle], list[FactorScore]] = {
            ("Technology", InvestmentStyle.GROWTH): [
                FactorScore(name="ev_fcf", raw_value=30.0, percentile_rank=0.0),
                FactorScore(name="ev_fcf", raw_value=25.0, percentile_rank=0.0),
            ],
        }
        result = style_sector_neutral_ranks(scores_by_bucket, invert=True, min_bucket_size=5)
        assert len(result) == 2

    def test_empty_input(self):
        result = style_sector_neutral_ranks({}, invert=False)
        assert result == []


class TestCrossBucketCalibration:
    def test_z_score_calibration_produces_0_to_100(self):
        """After z-score calibration, all scores in 0-100 range."""
        scores = [
            FactorScore(name="ev_fcf", raw_value=30.0, percentile_rank=90.0),
            FactorScore(name="ev_fcf", raw_value=25.0, percentile_rank=70.0),
            FactorScore(name="ev_fcf", raw_value=10.0, percentile_rank=80.0),
            FactorScore(name="ev_fcf", raw_value=8.0, percentile_rank=60.0),
        ]
        calibrated = calibrate_cross_bucket(scores)
        assert len(calibrated) == 4
        for s in calibrated:
            assert 0.0 <= s.percentile_rank <= 100.0

    def test_single_score_gets_50(self):
        scores = [FactorScore(name="ev_fcf", raw_value=30.0, percentile_rank=90.0)]
        calibrated = calibrate_cross_bucket(scores)
        assert calibrated[0].percentile_rank == 50.0
