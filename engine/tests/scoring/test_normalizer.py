"""Tests for percentile ranking normalizer."""

import pytest
from margin_engine.models.scoring import (
    CompositeScore,
    ConvictionLevel,
    FactorBreakdown,
    FactorScore,
)
from margin_engine.scoring.normalizer import (
    compute_percentile_ranks,
    rerank_composites,
    sector_neutral_ranks,
)


def _make_score(
    raw_value: float,
    name: str = "test_factor",
    detail: str = "",
) -> FactorScore:
    """Helper to build a FactorScore with percentile_rank=0.0."""
    return FactorScore(name=name, raw_value=raw_value, percentile_rank=0.0, detail=detail)


class TestComputePercentileRanks:
    def test_basic_five_scores(self):
        """5 stocks: [0.10, 0.25, 0.25, 0.40, 0.50] -> [20, 50, 50, 80, 100]."""
        scores = [
            _make_score(0.10),
            _make_score(0.25),
            _make_score(0.25),
            _make_score(0.40),
            _make_score(0.50),
        ]
        result = compute_percentile_ranks(scores)
        percentiles = [s.percentile_rank for s in result]
        assert percentiles == pytest.approx([20.0, 50.0, 50.0, 80.0, 100.0])

    def test_tie_handling(self):
        """All tied values at positions 2-4 should average to (2+3+4)/3 = 3."""
        scores = [
            _make_score(1.0),
            _make_score(2.0),
            _make_score(2.0),
            _make_score(2.0),
            _make_score(5.0),
        ]
        result = compute_percentile_ranks(scores)
        percentiles = [s.percentile_rank for s in result]
        # ranks: [1, 3, 3, 3, 5], percentiles: [20, 60, 60, 60, 100]
        assert percentiles == pytest.approx([20.0, 60.0, 60.0, 60.0, 100.0])

    def test_inverted_ranking(self):
        """With invert=True, lower raw_value gets higher percentile."""
        scores = [
            _make_score(0.10),
            _make_score(0.25),
            _make_score(0.40),
        ]
        result = compute_percentile_ranks(scores, invert=True)
        percentiles = {s.raw_value: s.percentile_rank for s in result}
        # Inverted: sorted descending [0.40, 0.25, 0.10]
        # ranks: 1, 2, 3 -> percentiles: 33.33, 66.67, 100.0
        # So 0.10 (best when inverted) gets highest percentile
        assert percentiles[0.10] > percentiles[0.25] > percentiles[0.40]

    def test_single_score_gets_50(self):
        """A single score should receive percentile 50.0."""
        scores = [_make_score(42.0)]
        result = compute_percentile_ranks(scores)
        assert result[0].percentile_rank == pytest.approx(50.0)

    def test_empty_list(self):
        """Empty input returns empty output."""
        result = compute_percentile_ranks([])
        assert result == []

    def test_all_same_value(self):
        """All identical raw_values should all get percentile 50.0."""
        scores = [_make_score(3.0) for _ in range(4)]
        result = compute_percentile_ranks(scores)
        for s in result:
            assert s.percentile_rank == pytest.approx(50.0)

    def test_preserves_name_and_detail(self):
        """Original FactorScore fields (name, detail) must be preserved."""
        scores = [
            _make_score(1.0, name="ev_fcf", detail="EV/FCF ratio"),
            _make_score(2.0, name="ev_fcf", detail="EV/FCF ratio"),
        ]
        result = compute_percentile_ranks(scores)
        for s in result:
            assert s.name == "ev_fcf"
            assert s.detail == "EV/FCF ratio"

    def test_percentiles_in_valid_range(self):
        """All percentile ranks must be in [0, 100]."""
        scores = [_make_score(v) for v in [0.5, 1.2, 3.7, 9.1, 15.0, 20.3]]
        result = compute_percentile_ranks(scores)
        for s in result:
            assert 0.0 <= s.percentile_rank <= 100.0

    def test_returns_new_objects(self):
        """compute_percentile_ranks should return new FactorScore objects, not mutate."""
        scores = [_make_score(1.0), _make_score(2.0)]
        result = compute_percentile_ranks(scores)
        # Original objects should still have percentile_rank=0.0
        assert scores[0].percentile_rank == 0.0
        assert scores[1].percentile_rank == 0.0
        # Result objects should have updated percentiles
        assert result[0].percentile_rank != 0.0 or result[1].percentile_rank != 0.0

    def test_preserves_raw_value(self):
        """Raw values must not be modified."""
        scores = [_make_score(1.5), _make_score(3.0), _make_score(7.0)]
        result = compute_percentile_ranks(scores)
        raw_values = [s.raw_value for s in result]
        assert raw_values == pytest.approx([1.5, 3.0, 7.0])

    def test_two_scores(self):
        """Two scores: ranks [1, 2], percentiles [50, 100]."""
        scores = [_make_score(10.0), _make_score(20.0)]
        result = compute_percentile_ranks(scores)
        percentiles = [s.percentile_rank for s in result]
        assert percentiles == pytest.approx([50.0, 100.0])

    def test_inverted_with_ties(self):
        """Inverted ranking with ties should still average correctly."""
        scores = [
            _make_score(1.0),
            _make_score(2.0),
            _make_score(2.0),
            _make_score(3.0),
        ]
        result = compute_percentile_ranks(scores, invert=True)
        percentiles = {s.raw_value: s.percentile_rank for s in result}
        # Inverted sort descending: [3.0, 2.0, 2.0, 1.0]
        # ranks: [1, 2.5, 2.5, 4], percentiles: [25, 62.5, 62.5, 100]
        assert percentiles[1.0] > percentiles[2.0] > percentiles[3.0]
        assert percentiles[1.0] == pytest.approx(100.0)
        assert percentiles[3.0] == pytest.approx(25.0)


class TestSectorNeutralRanks:
    def test_two_sectors_different_distributions(self):
        """Sector-neutral ranking should rank within each sector independently."""
        tech_scores = [
            _make_score(0.10),
            _make_score(0.50),
            _make_score(0.90),
        ]
        energy_scores = [
            _make_score(0.05),
            _make_score(0.06),
            _make_score(0.07),
        ]
        scores_by_sector = {
            "Information Technology": tech_scores,
            "Energy": energy_scores,
        }
        result = sector_neutral_ranks(scores_by_sector)
        # Within tech: [0.10, 0.50, 0.90] -> percentiles [33.33, 66.67, 100]
        # Within energy: [0.05, 0.06, 0.07] -> percentiles [33.33, 66.67, 100]
        # The lowest energy score (0.05) should get same percentile as lowest tech (0.10)
        tech_result = [s for s in result if s.raw_value in (0.10, 0.50, 0.90)]
        energy_result = [s for s in result if s.raw_value in (0.05, 0.06, 0.07)]
        tech_pcts = sorted(s.percentile_rank for s in tech_result)
        energy_pcts = sorted(s.percentile_rank for s in energy_result)
        assert tech_pcts == pytest.approx(energy_pcts)

    def test_sector_neutral_preserves_fields(self):
        """Sector-neutral ranking should preserve name and detail."""
        scores_by_sector = {
            "Information Technology": [
                _make_score(1.0, name="roic", detail="ROIC spread"),
                _make_score(2.0, name="roic", detail="ROIC spread"),
            ],
        }
        result = sector_neutral_ranks(scores_by_sector)
        for s in result:
            assert s.name == "roic"
            assert s.detail == "ROIC spread"

    def test_sector_neutral_inverted(self):
        """Sector-neutral with invert=True should rank lower raw_value higher."""
        scores_by_sector = {
            "Energy": [
                _make_score(5.0),
                _make_score(10.0),
                _make_score(15.0),
            ],
        }
        result = sector_neutral_ranks(scores_by_sector, invert=True)
        percentiles = {s.raw_value: s.percentile_rank for s in result}
        assert percentiles[5.0] > percentiles[10.0] > percentiles[15.0]

    def test_sector_neutral_empty_sector(self):
        """Empty sector should contribute nothing to output."""
        scores_by_sector = {
            "Energy": [_make_score(1.0), _make_score(2.0)],
            "Materials": [],
        }
        result = sector_neutral_ranks(scores_by_sector)
        assert len(result) == 2

    def test_sector_neutral_single_stock_sector(self):
        """A sector with a single stock should get percentile 50.0."""
        scores_by_sector = {
            "Energy": [_make_score(1.0), _make_score(2.0), _make_score(3.0)],
            "Materials": [_make_score(99.0)],
        }
        result = sector_neutral_ranks(scores_by_sector)
        materials_score = [s for s in result if s.raw_value == 99.0]
        assert len(materials_score) == 1
        assert materials_score[0].percentile_rank == pytest.approx(50.0)

    def test_sector_neutral_percentiles_in_range(self):
        """All sector-neutral percentiles must be in [0, 100]."""
        scores_by_sector = {
            "Information Technology": [_make_score(v) for v in [0.1, 0.5, 0.9]],
            "Energy": [_make_score(v) for v in [1.0, 2.0, 3.0, 4.0]],
        }
        result = sector_neutral_ranks(scores_by_sector)
        for s in result:
            assert 0.0 <= s.percentile_rank <= 100.0


# ---------------------------------------------------------------------------
# rerank_composites tests
# ---------------------------------------------------------------------------

def _make_composite(
    ticker: str,
    raw_score: float,
) -> CompositeScore:
    """Helper to build a CompositeScore with a given raw weighted-average score."""
    dummy_factor = FactorScore(name="test", raw_value=1.0, percentile_rank=50.0)
    return CompositeScore(
        ticker=ticker,
        composite_percentile=raw_score,
        composite_raw_score=raw_score,
        quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[dummy_factor]),
        value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[dummy_factor]),
        momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[dummy_factor]),
        filters_passed=[],
        data_coverage=1.0,
    )


class TestRerankComposites:
    def test_five_composites_proper_percentiles(self):
        """Raw scores [30, 40, 50, 60, 70] -> percentiles [20, 40, 60, 80, 100]."""
        composites = [
            _make_composite("A", 30.0),
            _make_composite("B", 40.0),
            _make_composite("C", 50.0),
            _make_composite("D", 60.0),
            _make_composite("E", 70.0),
        ]
        result = rerank_composites(composites)
        percentiles = [c.composite_percentile for c in result]
        assert percentiles == pytest.approx([20.0, 40.0, 60.0, 80.0, 100.0])

    def test_single_composite_gets_50(self):
        """A single composite should get percentile 50.0."""
        composites = [_make_composite("AAPL", 72.5)]
        result = rerank_composites(composites)
        assert result[0].composite_percentile == pytest.approx(50.0)

    def test_empty_list_returns_empty(self):
        """Empty input returns empty output."""
        result = rerank_composites([])
        assert result == []

    def test_all_identical_raw_scores_get_50(self):
        """All identical raw_scores should all get percentile 50.0."""
        composites = [_make_composite(f"T{i}", 55.0) for i in range(4)]
        result = rerank_composites(composites)
        for c in result:
            assert c.composite_percentile == pytest.approx(50.0)

    def test_ties_are_averaged(self):
        """Tied raw_scores should share the average percentile."""
        composites = [
            _make_composite("A", 30.0),
            _make_composite("B", 50.0),
            _make_composite("C", 50.0),
            _make_composite("D", 50.0),
            _make_composite("E", 70.0),
        ]
        result = rerank_composites(composites)
        # ranks: [1, 3, 3, 3, 5], percentiles: [20, 60, 60, 60, 100]
        percentiles = [c.composite_percentile for c in result]
        assert percentiles == pytest.approx([20.0, 60.0, 60.0, 60.0, 100.0])

    def test_original_objects_not_mutated(self):
        """rerank_composites should return new objects, not mutate inputs."""
        composites = [_make_composite("A", 30.0), _make_composite("B", 70.0)]
        original_pcts = [c.composite_percentile for c in composites]
        result = rerank_composites(composites)
        # Originals unchanged
        assert [c.composite_percentile for c in composites] == original_pcts
        # Results are different objects
        assert result[0] is not composites[0]

    def test_composite_raw_score_preserved(self):
        """composite_raw_score should be unchanged after re-ranking."""
        composites = [
            _make_composite("A", 30.0),
            _make_composite("B", 70.0),
        ]
        result = rerank_composites(composites)
        assert result[0].composite_raw_score == pytest.approx(30.0)
        assert result[1].composite_raw_score == pytest.approx(70.0)

    def test_conviction_levels_after_rerank(self):
        """After re-ranking 100 composites, the top ticker should not be 'none'."""
        composites = [_make_composite(f"T{i}", 40.0 + i * 0.2) for i in range(100)]
        result = rerank_composites(composites)
        # Top ticker (T99) should have percentile 100.0 -> exceptional
        top = max(result, key=lambda c: c.composite_percentile)
        assert top.conviction_level != ConvictionLevel.NONE
        assert top.composite_percentile >= 99.95

    def test_preserves_all_fields(self):
        """Ticker, quality, value, momentum, filters, data_coverage should be preserved."""
        composites = [_make_composite("AAPL", 60.0), _make_composite("MSFT", 80.0)]
        result = rerank_composites(composites)
        assert result[0].ticker == "AAPL"
        assert result[1].ticker == "MSFT"
        assert result[0].data_coverage == 1.0
        assert result[0].quality.factor_name == "quality"

    def test_percentiles_in_valid_range(self):
        """All re-ranked percentiles must be in [0, 100]."""
        composites = [_make_composite(f"T{i}", 20.0 + i * 4.0) for i in range(20)]
        result = rerank_composites(composites)
        for c in result:
            assert 0.0 <= c.composite_percentile <= 100.0

    def test_raw_score_differs_from_percentile_after_rerank(self):
        """After re-ranking, composite_raw_score and composite_percentile should differ."""
        composites = [
            _make_composite("A", 45.0),
            _make_composite("B", 52.0),
            _make_composite("C", 58.0),
            _make_composite("D", 63.0),
            _make_composite("E", 71.0),
        ]
        result = rerank_composites(composites)

        # Raw scores should be preserved as-is
        raw_scores = [c.composite_raw_score for c in result]
        assert raw_scores == pytest.approx([45.0, 52.0, 58.0, 63.0, 71.0])

        # Percentiles should be [20, 40, 60, 80, 100]
        percentiles = [c.composite_percentile for c in result]
        assert percentiles == pytest.approx([20.0, 40.0, 60.0, 80.0, 100.0])

        # The top stock's raw score (71.0) is NOT 100.0
        top = max(result, key=lambda c: c.composite_percentile)
        assert top.composite_raw_score == pytest.approx(71.0)
        assert top.composite_raw_score != top.composite_percentile

    def test_top_stock_raw_score_not_100(self):
        """The highest-ranked stock should NOT have raw_score = 100
        unless all factors genuinely average to 100."""
        composites = [_make_composite(f"T{i}", 40.0 + i * 0.5) for i in range(10)]
        result = rerank_composites(composites)
        top = max(result, key=lambda c: c.composite_percentile)
        # Top raw score is 40.0 + 9*0.5 = 44.5, definitely not 100
        assert top.composite_raw_score == pytest.approx(44.5)
        assert top.composite_raw_score < 100.0
