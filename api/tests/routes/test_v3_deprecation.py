"""Tests for V3 routes deprecation."""


def test_v3_list_docstring_deprecated():
    from margin_api.routes.v3_scores import list_v3_scores

    assert "deprecated" in list_v3_scores.__doc__.lower()


def test_v3_get_docstring_deprecated():
    from margin_api.routes.v3_scores import get_v3_score

    assert "deprecated" in get_v3_score.__doc__.lower()
