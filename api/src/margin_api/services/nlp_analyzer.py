"""NLP Analyzer service for structured SEC filing analysis.

Calls the Anthropic Claude API to extract sentiment, moat signals, risk flags,
management quality, competitive position, and segment revenue from filing text.

All results are cached in the filing_sentiment_cache table keyed by
(filing_text_id, analysis_version) so each filing is only analyzed once.

The service is feature-gated by MARGIN_NLP_ENABLED (default "false") to avoid
unintended API charges. Set MARGIN_NLP_ENABLED=true to activate.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import UTC, datetime

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import FilingSentimentCache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_ANALYSIS_VERSION = "v1"
NLP_ANALYSIS_VERSION = _ANALYSIS_VERSION


def _is_enabled() -> bool:
    return os.environ.get("MARGIN_NLP_ENABLED", "false").lower() in ("1", "true", "yes")


def _get_model() -> str:
    return os.environ.get("MARGIN_NLP_MODEL", _DEFAULT_MODEL)


def _get_temperature() -> float:
    try:
        return float(os.environ.get("MARGIN_NLP_TEMPERATURE", "0"))
    except ValueError:
        return 0.0


def _get_max_filings_per_day() -> int:
    try:
        return int(os.environ.get("MARGIN_NLP_MAX_FILINGS_PER_DAY", "50"))
    except ValueError:
        return 50


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a financial analyst specializing in SEC filing analysis. \
Analyze the provided 10-K/10-Q filing text and return a JSON object with:
- sentiment_value: float from -5 (very negative) to +5 (very positive)
- moat_signals: list of strings describing competitive advantages found
- risk_flags: list of strings describing material risks found
- management_quality: object with "score" (1-5) and "notes" string
- competitive_position: object with "rating" (leader/strong/moderate/weak) and "notes" string
- segment_revenue: object mapping segment names to revenue share fractions (0.0-1.0)

Return ONLY valid JSON, no other text."""


def _build_user_prompt(mda_text: str | None, risk_text: str | None) -> str:
    parts = []
    if mda_text:
        parts.append(f"=== MD&A Section ===\n{mda_text[:15000]}")
    if risk_text:
        parts.append(f"=== Risk Factors Section ===\n{risk_text[:10000]}")
    return "\n\n".join(parts) if parts else "No filing text provided."


def _prompt_hash(user_prompt: str, model: str) -> str:
    """Stable hash of the prompt + model for cache keying."""
    content = f"{model}:{user_prompt}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class NLPAnalyzer:
    """Async service that calls Claude API for structured SEC filing analysis."""

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        """Lazy-initialize the Anthropic client only when NLP is enabled."""
        if self._client is None:
            self._client = anthropic.AsyncAnthropic()
        return self._client

    async def analyze(
        self,
        session: AsyncSession,
        filing_text_id: int,
        ticker: str,
        mda_text: str | None,
        risk_text: str | None,
    ) -> dict | None:
        """Analyze filing text with Claude and cache the result.

        If NLP is disabled, returns None immediately without any API call.
        If a cached result exists for (filing_text_id, analysis_version), returns it.
        If the daily cap is exceeded, returns None.

        Args:
            session: Async SQLAlchemy session for cache reads/writes.
            filing_text_id: PK of the FilingText row being analyzed.
            ticker: Ticker symbol (for logging and cache indexing).
            mda_text: MD&A section text (may be None).
            risk_text: Risk Factors section text (may be None).

        Returns:
            Dict with keys: sentiment_value, moat_signals, risk_flags,
            management_quality, competitive_position, segment_revenue.
            Returns None if disabled, capped, or on error.
        """
        if not _is_enabled():
            return None

        model = _get_model()
        user_prompt = _build_user_prompt(mda_text, risk_text)
        p_hash = _prompt_hash(user_prompt, model)

        # Check cache first
        cached = await self._check_cache(session, filing_text_id)
        if cached is not None:
            return self._row_to_dict(cached)

        # Check daily cap
        if await self._daily_cap_exceeded(session):
            logger.warning(
                "[nlp] Daily cap of %d reached — skipping %s (filing_id=%d)",
                _get_max_filings_per_day(),
                ticker,
                filing_text_id,
            )
            return None

        # Call API
        try:
            result = await self._call_api(model, user_prompt)
        except Exception:
            logger.exception("[nlp] API call failed for %s (filing_id=%d)", ticker, filing_text_id)
            return None

        if result is None:
            return None

        # Persist to cache
        await self._store_cache(session, filing_text_id, ticker, p_hash, result, model)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _check_cache(
        self, session: AsyncSession, filing_text_id: int
    ) -> FilingSentimentCache | None:
        stmt = select(FilingSentimentCache).where(
            FilingSentimentCache.filing_text_id == filing_text_id,
            FilingSentimentCache.analysis_version == _ANALYSIS_VERSION,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _daily_cap_exceeded(self, session: AsyncSession) -> bool:
        cap = _get_max_filings_per_day()
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count())
            .select_from(FilingSentimentCache)
            .where(
                FilingSentimentCache.created_at >= today_start,
                FilingSentimentCache.analysis_version == _ANALYSIS_VERSION,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar_one_or_none() or 0
        return int(count) >= cap

    async def _call_api(self, model: str, user_prompt: str) -> dict | None:
        """Make the Anthropic API call and parse the JSON response."""
        client = self._get_client()
        message = await client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=_get_temperature(),
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        if not message.content:
            logger.warning("[nlp] Empty response from API")
            return None

        first_block = message.content[0]
        if not hasattr(first_block, "text"):
            logger.warning("[nlp] Unexpected content block type: %s", type(first_block))
            return None

        raw_text = first_block.text.strip()
        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, ValueError):
            logger.warning("[nlp] Failed to parse JSON response: %.200s", raw_text)
            return None

    async def _store_cache(
        self,
        session: AsyncSession,
        filing_text_id: int,
        ticker: str,
        prompt_hash: str,
        result: dict,
        model: str,
    ) -> None:
        """Persist analysis result to filing_sentiment_cache."""
        try:
            row = FilingSentimentCache(
                filing_text_id=filing_text_id,
                ticker=ticker,
                analysis_version=_ANALYSIS_VERSION,
                prompt_hash=prompt_hash,
                sentiment_value=result.get("sentiment_value"),
                moat_signals=result.get("moat_signals"),
                risk_flags=result.get("risk_flags"),
                management_quality=result.get("management_quality"),
                competitive_position=result.get("competitive_position"),
                segment_revenue=result.get("segment_revenue"),
                model_used=model,
                created_at=datetime.now(UTC),
            )
            session.add(row)
            await session.commit()
        except Exception:
            logger.exception(
                "[nlp] Failed to store cache row for filing_text_id=%d", filing_text_id
            )
            await session.rollback()

    @staticmethod
    def _row_to_dict(row: FilingSentimentCache) -> dict:
        return {
            "sentiment_value": row.sentiment_value,
            "moat_signals": row.moat_signals,
            "risk_flags": row.risk_flags,
            "management_quality": row.management_quality,
            "competitive_position": row.competitive_position,
            "segment_revenue": row.segment_revenue,
            "model_used": row.model_used,
        }
