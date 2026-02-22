"""Tests for price ingestion batch upserts."""

from __future__ import annotations


class TestPreparePriceValues:
    def test_insert_new_bars(self):
        from margin_api.services.price_ingestion import prepare_price_values

        bars = [
            {
                "time": "2025-01-15T10:00:00+00:00",
                "open": 150.0,
                "high": 151.0,
                "low": 149.5,
                "close": 150.5,
                "volume": 1000,
            },
            {
                "time": "2025-01-15T10:05:00+00:00",
                "open": 150.5,
                "high": 152.0,
                "low": 150.0,
                "close": 151.5,
                "volume": 2000,
            },
        ]
        values = prepare_price_values("AAPL", bars, "test")
        assert len(values) == 2
        assert values[0]["ticker"] == "AAPL"
        assert values[0]["source"] == "test"
        assert values[1]["close"] == 151.5

    def test_prepare_empty_bars(self):
        from margin_api.services.price_ingestion import prepare_price_values

        values = prepare_price_values("AAPL", [], "test")
        assert values == []

    def test_prepare_handles_missing_volume(self):
        from margin_api.services.price_ingestion import prepare_price_values

        bars = [
            {
                "time": "2025-01-15T10:00:00+00:00",
                "open": 150.0,
                "high": 151.0,
                "low": 149.5,
                "close": 150.5,
            },
        ]
        values = prepare_price_values("AAPL", bars, "test")
        assert values[0]["volume"] is None


class TestChunkBars:
    def test_batch_chunking(self):
        from margin_api.services.price_ingestion import chunk_bars

        bars = list(range(2500))
        chunks = list(chunk_bars(bars, batch_size=1000))
        assert len(chunks) == 3
        assert len(chunks[0]) == 1000
        assert len(chunks[1]) == 1000
        assert len(chunks[2]) == 500

    def test_single_chunk(self):
        from margin_api.services.price_ingestion import chunk_bars

        bars = list(range(500))
        chunks = list(chunk_bars(bars, batch_size=1000))
        assert len(chunks) == 1
        assert len(chunks[0]) == 500

    def test_empty_bars(self):
        from margin_api.services.price_ingestion import chunk_bars

        chunks = list(chunk_bars([], batch_size=1000))
        assert len(chunks) == 0
