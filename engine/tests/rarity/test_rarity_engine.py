"""Integration tests for the rarity engine orchestrator."""

from margin_engine.models.scoring import CompositeScore, FactorBreakdown, FactorScore
from margin_engine.rarity.models import RarityConfig, RarityRegime
from margin_engine.rarity.rarity_engine import compute_rarity_for_universe


def _fb(name: str, pctl: float, weight: float = 0.25) -> FactorBreakdown:
    return FactorBreakdown(
        factor_name=name,
        weight=weight,
        sub_scores=[FactorScore(name=f"{name}_main", raw_value=1.0, percentile_rank=pctl)],
    )


def _make_composite(
    ticker: str, q: float, v: float, m: float, g: float, raw: float = 75.0
) -> CompositeScore:
    return CompositeScore(
        ticker=ticker,
        composite_percentile=raw,
        composite_raw_score=raw,
        quality=_fb("quality", q),
        value=_fb("value", v),
        momentum=_fb("momentum", m),
        growth=_fb("growth", g),
        filters_passed=[],
        data_coverage=0.9,
        winning_track="compounder",
    )


def test_basic_universe_scoring():
    composites = [
        _make_composite("AAA", q=92, v=88, m=85, g=90, raw=80),
        _make_composite("BBB", q=70, v=65, m=60, g=55, raw=65),
        _make_composite("CCC", q=80, v=78, m=76, g=74, raw=72),
    ]
    config = RarityConfig()
    results = compute_rarity_for_universe(
        composites=composites,
        regime=RarityRegime.EXPANSION,
        historical_snapshots=[],
        config=config,
    )
    assert len(results) == 3
    scores = {r.ticker: r.rarity_score for r in results}
    assert scores["AAA"] > scores["BBB"]
    assert scores["AAA"] > scores["CCC"]


def test_gate_cascade_filters():
    composites = [
        _make_composite("TOP", q=92, v=88, m=85, g=90, raw=80),  # EXCEPTIONAL
        _make_composite("MED", q=70, v=65, m=60, g=55, raw=68),  # MEDIUM tier
        _make_composite("LOW", q=50, v=45, m=40, g=35, raw=50),  # NONE tier
    ]
    config = RarityConfig()
    results = compute_rarity_for_universe(
        composites=composites,
        regime=RarityRegime.EXPANSION,
        historical_snapshots=[],
        config=config,
    )
    top_result = next(r for r in results if r.ticker == "TOP")
    assert top_result.passed_gates[0] is True  # Gate 1: EXCEPTIONAL

    med_result = next(r for r in results if r.ticker == "MED")
    assert med_result.passed_gates[0] is False  # Gate 1: MEDIUM not in (EXCEPTIONAL, HIGH)

    low_result = next(r for r in results if r.ticker == "LOW")
    assert low_result.passed_gates[0] is False  # Gate 1: NONE tier


def test_empty_universe():
    results = compute_rarity_for_universe(
        composites=[],
        regime=RarityRegime.EXPANSION,
        historical_snapshots=[],
        config=RarityConfig(),
    )
    assert results == []
