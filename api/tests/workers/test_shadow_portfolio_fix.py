"""Tests for shadow portfolio worker including unpublished scores."""


def test_build_shadow_positions_includes_unpublished():
    """Shadow portfolio should tag unpublished scores as 'staged'."""
    from margin_api.workers import _build_shadow_positions

    class FakeV4Score:
        def __init__(self, score, conviction, published):
            self.composite_score = score
            self.conviction = conviction
            self.published = published

    rows = [
        (FakeV4Score(85.0, "high", False), "TEST"),
        (FakeV4Score(90.0, "exceptional", True), "PUB"),
    ]

    positions = _build_shadow_positions(rows)
    assert len(positions) == 2
    assert positions[0]["ticker"] == "TEST"
    assert positions[0]["source"] == "staged"
    assert positions[1]["ticker"] == "PUB"
    assert positions[1]["source"] == "published"


def test_build_shadow_positions_empty():
    """Empty rows produce empty positions."""
    from margin_api.workers import _build_shadow_positions

    positions = _build_shadow_positions([])
    assert positions == []
