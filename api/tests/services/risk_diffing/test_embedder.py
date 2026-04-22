"""Tests for the Voyage AI embedder module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.services.risk_diffing.chunker import RiskChunk
from margin_api.services.risk_diffing.embedder import (
    embed_chunks,
    get_cached_embeddings,
    store_embeddings,
)

_GET_CLIENT = "margin_api.services.risk_diffing.embedder._get_client"


def _make_chunk(index: int, text: str = "Some risk factor text here.") -> RiskChunk:
    return RiskChunk(index=index, text=text, text_hash=f"hash{index:03d}")


def _make_embedding(dims: int = 1024) -> list[float]:
    return [0.1] * dims


class TestEmbedChunks:
    @pytest.mark.asyncio
    async def test_returns_embeddings_for_all_chunks(self) -> None:
        chunks = [_make_chunk(0), _make_chunk(1)]
        fake_embeddings = [_make_embedding(), _make_embedding()]

        mock_result = MagicMock()
        mock_result.embeddings = fake_embeddings

        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(return_value=mock_result)

        with patch(_GET_CLIENT, return_value=mock_client):
            result = await embed_chunks(chunks)

        assert len(result) == 2
        assert len(result[0]) == 1024
        assert len(result[1]) == 1024

    @pytest.mark.asyncio
    async def test_batches_large_chunk_lists(self) -> None:
        chunks = [_make_chunk(i) for i in range(300)]
        # 300 chunks → 3 batches of 128, 128, 44
        call_count = 0

        async def fake_embed(texts: list[str], **kwargs: object) -> MagicMock:
            nonlocal call_count
            result = MagicMock()
            result.embeddings = [_make_embedding() for _ in texts]
            call_count += 1
            return result

        mock_client = AsyncMock()
        mock_client.embed = fake_embed

        with patch(_GET_CLIENT, return_value=mock_client):
            result = await embed_chunks(chunks)

        assert call_count == 3
        assert len(result) == 300

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self) -> None:
        mock_client = AsyncMock()

        with patch(_GET_CLIENT, return_value=mock_client):
            result = await embed_chunks([])

        assert result == []
        mock_client.embed.assert_not_called()


class TestEmbeddingCache:
    @pytest.mark.asyncio
    async def test_get_cached_returns_empty_on_miss(self) -> None:
        mock_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_execute_result)

        result = await get_cached_embeddings(mock_session, filing_text_id=42)

        assert result == {}

    @pytest.mark.asyncio
    async def test_store_adds_rows(self) -> None:
        mock_session = MagicMock()
        mock_session.add = MagicMock()

        chunks = [_make_chunk(0), _make_chunk(1)]
        embeddings = [_make_embedding(), _make_embedding()]

        await store_embeddings(
            session=mock_session,
            filing_text_id=7,
            chunks=chunks,
            embeddings=embeddings,
            model="voyage-finance-2",
        )

        assert mock_session.add.call_count == 2
