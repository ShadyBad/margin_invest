"""Voyage AI embedding client for risk factor chunks.

Provides batch embedding, a DB-backed cache, and persistence helpers.
The Voyage AI client is initialized lazily as a module-level singleton.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from margin_api.services.risk_diffing.chunker import RiskChunk

import voyageai

from margin_api.services.risk_diffing.config import (
    EMBEDDING_BATCH_SIZE,
    get_voyage_credential,
    get_voyage_model,
)

_client: voyageai.AsyncClient | None = None


def _get_client() -> voyageai.AsyncClient:
    """Return the module-level Voyage AI async client, creating it on first call."""
    global _client
    if _client is None:
        credential = get_voyage_credential()
        _client = voyageai.AsyncClient(credential)
    return _client


async def embed_chunks(chunks: list[RiskChunk]) -> list[list[float]]:
    """Embed a list of RiskChunks using the Voyage AI API.

    Chunks are sent in batches of EMBEDDING_BATCH_SIZE to stay within API limits.
    Returns a flat list of embedding vectors in the same order as the input chunks.
    """
    if not chunks:
        return []

    client = _get_client()
    model = get_voyage_model()
    results: list[list[float]] = []

    for batch_start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
        texts = [chunk.text for chunk in batch]
        response = await client.embed(texts, model=model, input_type="document")
        results.extend(response.embeddings)

    return results


async def get_cached_embeddings(
    session: AsyncSession,
    filing_text_id: int,
) -> dict[int, list[float]]:
    """Return cached embeddings for a filing keyed by chunk index.

    Queries the risk_factor_embeddings table. Returns an empty dict when
    no cached rows exist for the given filing_text_id.
    """
    from sqlalchemy import select

    from margin_api.db.models import RiskFactorEmbedding

    stmt = select(RiskFactorEmbedding).where(RiskFactorEmbedding.filing_text_id == filing_text_id)
    rows = (await session.execute(stmt)).scalars().all()
    return {row.chunk_index: row.embedding for row in rows}


async def store_embeddings(
    session: AsyncSession,
    filing_text_id: int,
    chunks: list[RiskChunk],
    embeddings: list[list[float]],
    model: str,
) -> None:
    """Persist chunk embeddings to the risk_factor_embeddings table.

    Creates one RiskFactorEmbedding row per chunk. The caller is responsible
    for committing (or rolling back) the session.
    """
    from margin_api.db.models import RiskFactorEmbedding

    for chunk, embedding in zip(chunks, embeddings):
        row = RiskFactorEmbedding(
            filing_text_id=filing_text_id,
            chunk_index=chunk.index,
            chunk_text_hash=chunk.text_hash,
            embedding=embedding,
            embedding_model=model,
        )
        session.add(row)
