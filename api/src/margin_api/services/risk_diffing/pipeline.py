"""Pipeline orchestrator for the filing diffing workflow.

Coordinates chunking, embedding, semantic diffing, and LLM analysis for a
single ticker, persisting results to the risk_factor_analyses table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from margin_api.services.risk_diffing.config import (
    get_analysis_model,
    get_length_change_threshold,
    get_prompt_version,
    get_similarity_threshold,
    get_unchanged_threshold,
    get_voyage_model,
)
from margin_api.services.risk_diffing.diff_engine import classify_changes
from margin_api.services.risk_diffing.embedder import (
    embed_chunks,
    get_cached_embeddings,
    store_embeddings,
)
from margin_api.services.risk_diffing.risk_analyzer import analyze_material_changes

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of processing one ticker through the diffing pipeline."""

    ticker: str
    status: str  # "processed" | "skipped" | "error"
    reason: str = ""
    cost_usd: float = field(default=0.0)


async def diff_single_ticker(session: AsyncSession, ticker: str) -> PipelineResult:
    """Run the full diffing pipeline for a single ticker.

    Steps:
    1. Fetch the two most recent 10-K FilingText rows for the ticker.
    2. Skip if fewer than 2 exist or either lacks risk factor text.
    3. Chunk both filings risk factor sections.
    4. Retrieve or compute embeddings for each filing (with DB cache).
    5. Classify semantic changes between the two filings.
    6. If changes exist, call the LLM analyzer.
    7. Persist a RiskFactorAnalysis row.
    8. Return a PipelineResult with status "processed".
    """
    # Lazy-import DB models inside the function to isolate the ORM layer
    # and allow unit tests to patch without loading the full database stack.
    from sqlalchemy import select

    from margin_api.db.models import FilingText, RiskFactorAnalysis
    from margin_api.services.risk_diffing.chunker import chunk_risk_factors

    try:
        stmt = (
            select(FilingText)
            .where(FilingText.ticker == ticker)
            .where(FilingText.filing_type == "10-K")
            .order_by(FilingText.period_end.desc())
            .limit(2)
        )
        rows = (await session.execute(stmt)).scalars().all()

        if len(rows) < 2:
            return PipelineResult(
                ticker=ticker,
                status="skipped",
                reason="fewer than 2 10-K filings available",
            )

        current, prior = rows[0], rows[1]

        if not current.risk_factors_text or not prior.risk_factors_text:
            return PipelineResult(
                ticker=ticker,
                status="skipped",
                reason="one or both filings are missing risk_factors_text",
            )

        # Chunk both filings
        current_chunks = chunk_risk_factors(current.risk_factors_text)
        prior_chunks = chunk_risk_factors(prior.risk_factors_text)

        # Embeddings: check DB cache first, embed and store on a cache miss
        voyage_model = get_voyage_model()

        async def _get_or_embed(filing_id: int, chunks: list) -> list[list[float]]:
            cached = await get_cached_embeddings(session, filing_id)
            if cached:
                return [cached[i] for i in sorted(cached)]
            if not chunks:
                return []
            embeddings = await embed_chunks(chunks)
            await store_embeddings(session, filing_id, chunks, embeddings, voyage_model)
            return embeddings

        current_embeddings = await _get_or_embed(current.id, current_chunks)
        prior_embeddings = await _get_or_embed(prior.id, prior_chunks)

        # Semantic diff
        candidates = classify_changes(
            old_embeddings=prior_embeddings,
            new_embeddings=current_embeddings,
            old_texts=[c.text for c in prior_chunks],
            new_texts=[c.text for c in current_chunks],
            similarity_threshold=get_similarity_threshold(),
            unchanged_threshold=get_unchanged_threshold(),
            length_change_threshold=get_length_change_threshold(),
        )

        # LLM analysis (only when there are candidates)
        analysis: dict | None = None
        if candidates:
            analysis = await analyze_material_changes(session, ticker, candidates)

        # Persist the result row
        prompt_version = get_prompt_version()
        analysis_model = get_analysis_model()

        row = RiskFactorAnalysis(
            ticker=ticker,
            filing_text_id=current.id,
            prior_filing_text_id=prior.id,
            material_changes=analysis.get("material_changes") if analysis else None,
            overall_risk_delta_score=(
                analysis.get("overall_risk_delta_score") if analysis else None
            ),
            model_confidence=analysis.get("model_confidence") if analysis else None,
            analysis_tokens_used=analysis.get("analysis_tokens_used") if analysis else None,
            analysis_cost_usd=analysis.get("analysis_cost_usd") if analysis else None,
            prompt_version=prompt_version,
            embedding_model=voyage_model,
            analysis_model=analysis_model if analysis else None,
        )
        session.add(row)

        cost_usd = float(analysis.get("analysis_cost_usd", 0.0)) if analysis else 0.0
        logger.info(
            "[risk_diffing] processed %s: %d candidates, cost=$%.4f",
            ticker,
            len(candidates),
            cost_usd,
        )
        return PipelineResult(ticker=ticker, status="processed", cost_usd=cost_usd)

    except Exception:
        logger.exception("[risk_diffing] pipeline error for %s", ticker)
        await session.rollback()
        return PipelineResult(
            ticker=ticker,
            status="error",
            reason="unexpected exception; see logs",
        )
