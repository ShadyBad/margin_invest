"""Tests for EdgarIndexCache model."""

from __future__ import annotations

from margin_api.db.models import EdgarIndexCache


class TestEdgarIndexCacheModel:
    """Verify EdgarIndexCache model fields exist."""

    def test_tablename(self) -> None:
        assert EdgarIndexCache.__tablename__ == "edgar_index_cache"

    def test_has_required_columns(self) -> None:
        cols = {c.name for c in EdgarIndexCache.__table__.columns}
        assert "id" in cols
        assert "year" in cols
        assert "quarter" in cols
        assert "entries_json" in cols
        assert "entry_count" in cols
        assert "fetched_at" in cols
        assert "cache_key" in cols
