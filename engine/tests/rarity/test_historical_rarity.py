"""Tests for historical frequency rarity scoring."""

from margin_engine.rarity.historical_rarity import compute_historical_frequency


def test_no_history_returns_neutral():
    score = compute_historical_frequency("Q90+V85+M80+G75", [])
    assert score == 50.0


def test_insufficient_quarters_returns_neutral():
    snapshots = [
        {"signature": "Q90+V85+M80+G75", "quarter": "2025-Q1"},
        {"signature": "Q85+V80+M75+G70", "quarter": "2025-Q2"},
    ]
    score = compute_historical_frequency("Q90+V85+M80+G75", snapshots)
    assert score == 50.0


def test_never_seen_signature_is_rare():
    snapshots = [{"signature": "Q60+V55+M50+G45", "quarter": f"2024-Q{i}"} for i in range(1, 5)] + [
        {"signature": "Q70+V65+M60+G55", "quarter": f"2025-Q{i}"} for i in range(1, 5)
    ]
    score = compute_historical_frequency("Q95+V90+M85+G88", snapshots)
    assert score > 80


def test_common_signature_is_not_rare():
    sig = "Q70+V65+M60+G55"
    snapshots = [{"signature": sig, "quarter": f"2024-Q{i}"} for i in range(1, 5)]
    snapshots += [{"signature": sig, "quarter": f"2025-Q{i}"} for i in range(1, 5)]
    score = compute_historical_frequency(sig, snapshots)
    assert score < 30
