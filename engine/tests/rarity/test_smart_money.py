"""Tests for smart money convergence scoring."""

from margin_engine.rarity.smart_money import compute_smart_money_convergence


def test_accumulation_only():
    score = compute_smart_money_convergence(
        accumulation_percentile=80.0,
        insider_cluster_percentile=20.0,
        accumulation_metadata=None,
        insider_metadata=None,
    )
    assert score <= 60


def test_accumulation_plus_insider():
    score = compute_smart_money_convergence(
        accumulation_percentile=80.0,
        insider_cluster_percentile=75.0,
        accumulation_metadata=None,
        insider_metadata={"cluster_buy_detected": True},
    )
    assert 60 < score <= 80


def test_full_convergence_with_metadata():
    score = compute_smart_money_convergence(
        accumulation_percentile=90.0,
        insider_cluster_percentile=85.0,
        accumulation_metadata={
            "n_quality_institutions_adding": 5,
            "n_consecutive_quarters_accumulated": 3,
        },
        insider_metadata={"cluster_buy_detected": True, "n_distinct_insiders": 4},
    )
    assert score > 80


def test_no_signals():
    score = compute_smart_money_convergence(
        accumulation_percentile=30.0,
        insider_cluster_percentile=25.0,
        accumulation_metadata=None,
        insider_metadata=None,
    )
    assert score < 40


def test_none_metadata_handled():
    score = compute_smart_money_convergence(
        accumulation_percentile=75.0,
        insider_cluster_percentile=70.0,
        accumulation_metadata=None,
        insider_metadata=None,
    )
    assert 0 <= score <= 100
