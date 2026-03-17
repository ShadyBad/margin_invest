"""Tests for Track A / Track B pillar extraction logic."""

from margin_engine.models.scoring import CompositeScore, FactorBreakdown, FactorScore
from margin_engine.rarity.pillar_extraction import extract_pillar_percentiles


def _fb(name: str, pctl: float, weight: float = 0.25) -> FactorBreakdown:
    return FactorBreakdown(
        factor_name=name,
        weight=weight,
        sub_scores=[FactorScore(name=f"{name}_main", raw_value=1.0, percentile_rank=pctl)],
    )


def _make_composite(
    ticker: str = "TEST",
    q: float = 80.0,
    v: float = 75.0,
    m: float = 70.0,
    g: float | None = 65.0,
    catalyst: float | None = None,
    winning_track: str = "compounder",
) -> CompositeScore:
    growth = _fb("growth", g) if g is not None else None
    cat = _fb("catalyst", catalyst) if catalyst is not None else None
    mom = (
        _fb("momentum", m)
        if winning_track != "mispricing"
        else FactorBreakdown(factor_name="momentum", weight=0.0, sub_scores=[])
    )
    return CompositeScore(
        ticker=ticker,
        composite_percentile=75.0,
        composite_raw_score=75.0,
        quality=_fb("quality", q),
        value=_fb("value", v),
        momentum=mom,
        growth=growth,
        catalyst=cat,
        filters_passed=[],
        data_coverage=0.9,
        winning_track=winning_track,
    )


def test_track_a_returns_four_pillars():
    cs = _make_composite(q=92, v=85, m=78, g=88)
    pillars = extract_pillar_percentiles(cs)
    assert pillars == {"quality": 92.0, "value": 85.0, "momentum": 78.0, "growth": 88.0}


def test_track_b_returns_three_pillars_with_catalyst():
    cs = _make_composite(q=90, v=82, g=None, catalyst=75, winning_track="mispricing")
    pillars = extract_pillar_percentiles(cs)
    assert pillars == {"quality": 90.0, "value": 82.0, "catalyst": 75.0}
    assert "momentum" not in pillars
    assert "growth" not in pillars


def test_track_a_no_growth_returns_three_pillars():
    cs = _make_composite(q=80, v=70, m=60, g=None)
    pillars = extract_pillar_percentiles(cs)
    assert pillars == {"quality": 80.0, "value": 70.0, "momentum": 60.0}
