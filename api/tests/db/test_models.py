"""Tests for DB model definitions."""

from margin_api.db.models import SignalTransition, Score


def test_signal_transition_model_exists():
    assert SignalTransition.__tablename__ == "signal_transitions"


def test_score_has_price_columns():
    """Score model should have price target columns."""
    columns = {c.name for c in Score.__table__.columns}
    assert "intrinsic_value" in columns
    assert "buy_price" in columns
    assert "sell_price" in columns
    assert "actual_price" in columns
