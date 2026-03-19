"""Tests for the NLPAnalyzer service.

Tests are written first (TDD). Uses mocks for the Anthropic client.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.services.nlp_analyzer import NLPAnalyzer
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_RESPONSE_JSON = {
    "sentiment_value": 2.5,
    "moat_signals": ["strong brand", "switching costs"],
    "risk_flags": ["regulatory risk", "competition"],
    "management_quality": {"score": 4, "notes": "strong execution"},
    "competitive_position": {"rating": "leader", "notes": "dominant market share"},
    "segment_revenue": {"hardware": 0.55, "services": 0.45},
}


def _make_mock_message(content_json: dict) -> MagicMock:
    """Build a mock Anthropic Message with a text block."""
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = json.dumps(content_json)
    mock_message = MagicMock()
    mock_message.content = [mock_block]
    return mock_message


def _make_mock_session() -> AsyncMock:
    """Build a minimal async DB session mock."""
    session = AsyncMock(spec=AsyncSession)
    # execute() returns a result with .scalar_one_or_none() -> None (no cache hit)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    return session


# ---------------------------------------------------------------------------
# Tests: disabled mode
# ---------------------------------------------------------------------------


class TestNLPDisabled:
    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "false")
        analyzer = NLPAnalyzer()
        session = _make_mock_session()
        result = await analyzer.analyze(
            session=session,
            filing_text_id=1,
            ticker="AAPL",
            mda_text="Revenue increased 20%.",
            risk_text="Competition remains intense.",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_no_api_call_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "false")
        analyzer = NLPAnalyzer()
        session = _make_mock_session()

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            await analyzer.analyze(
                session=session,
                filing_text_id=1,
                ticker="AAPL",
                mda_text="some text",
                risk_text="some risks",
            )
            mock_anthropic.AsyncAnthropic.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: enabled mode
# ---------------------------------------------------------------------------


class TestNLPEnabled:
    @pytest.mark.asyncio
    async def test_returns_dict_when_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "true")

        mock_message = _make_mock_message(_SAMPLE_RESPONSE_JSON)
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        session = _make_mock_session()

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            analyzer = NLPAnalyzer()
            result = await analyzer.analyze(
                session=session,
                filing_text_id=1,
                ticker="AAPL",
                mda_text="Revenue increased 20%.",
                risk_text="Competition remains intense.",
            )

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_parses_sentiment_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "true")

        mock_message = _make_mock_message(_SAMPLE_RESPONSE_JSON)
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        session = _make_mock_session()

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            analyzer = NLPAnalyzer()
            result = await analyzer.analyze(
                session=session,
                filing_text_id=1,
                ticker="AAPL",
                mda_text="Revenue grew 20%.",
                risk_text="Some risks.",
            )

        assert result is not None
        assert result.get("sentiment_value") == 2.5

    @pytest.mark.asyncio
    async def test_parses_moat_signals(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "true")

        mock_message = _make_mock_message(_SAMPLE_RESPONSE_JSON)
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        session = _make_mock_session()

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            analyzer = NLPAnalyzer()
            result = await analyzer.analyze(
                session=session,
                filing_text_id=1,
                ticker="AAPL",
                mda_text="Revenue grew 20%.",
                risk_text="Some risks.",
            )

        assert result is not None
        assert "moat_signals" in result
        assert "strong brand" in result["moat_signals"]

    @pytest.mark.asyncio
    async def test_malformed_json_response_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "true")

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "This is not valid JSON at all!!!"
        mock_message = MagicMock()
        mock_message.content = [mock_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        session = _make_mock_session()

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            analyzer = NLPAnalyzer()
            result = await analyzer.analyze(
                session=session,
                filing_text_id=1,
                ticker="AAPL",
                mda_text="Revenue grew 20%.",
                risk_text="Some risks.",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_content_response_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "true")

        mock_message = MagicMock()
        mock_message.content = []

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        session = _make_mock_session()

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            analyzer = NLPAnalyzer()
            result = await analyzer.analyze(
                session=session,
                filing_text_id=1,
                ticker="AAPL",
                mda_text="Revenue grew 20%.",
                risk_text="Some risks.",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_api_exception_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "true")

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

        session = _make_mock_session()

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            analyzer = NLPAnalyzer()
            result = await analyzer.analyze(
                session=session,
                filing_text_id=1,
                ticker="AAPL",
                mda_text="Revenue grew 20%.",
                risk_text="Some risks.",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If a cache row exists, return it without calling the API."""
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "true")

        cached_row = MagicMock()
        cached_row.sentiment_value = 1.0
        cached_row.moat_signals = ["brand"]
        cached_row.risk_flags = []
        cached_row.management_quality = {}
        cached_row.competitive_position = {}
        cached_row.segment_revenue = {}
        cached_row.model_used = "claude-haiku-4-5-20251001"

        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cached_row
        session.execute.return_value = mock_result

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = AsyncMock()
            analyzer = NLPAnalyzer()
            result = await analyzer.analyze(
                session=session,
                filing_text_id=1,
                ticker="AAPL",
                mda_text="Revenue grew 20%.",
                risk_text="Some risks.",
            )

            # API should NOT be called when cache hit
            mock_anthropic.AsyncAnthropic.return_value.messages.create.assert_not_called()

        assert result is not None
        assert result["sentiment_value"] == 1.0


# ---------------------------------------------------------------------------
# Tests: daily cap
# ---------------------------------------------------------------------------


class TestDailyCapEnforced:
    @pytest.mark.asyncio
    async def test_daily_cap_returns_none_when_exceeded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MARGIN_NLP_ENABLED", "true")
        monkeypatch.setenv("MARGIN_NLP_MAX_FILINGS_PER_DAY", "2")

        mock_message = _make_mock_message(_SAMPLE_RESPONSE_JSON)
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        # Simulate the daily count already at 2 (the cap)
        session = AsyncMock(spec=AsyncSession)
        # First call is cache check (returns None), second is daily count (returns 2)
        mock_no_cache = MagicMock()
        mock_no_cache.scalar_one_or_none.return_value = None
        mock_count = MagicMock()
        mock_count.scalar_one_or_none.return_value = 2  # already at cap

        session.execute.side_effect = [mock_no_cache, mock_count]

        with patch("margin_api.services.nlp_analyzer.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            analyzer = NLPAnalyzer()
            result = await analyzer.analyze(
                session=session,
                filing_text_id=99,
                ticker="MSFT",
                mda_text="some text",
                risk_text="some risks",
            )

        assert result is None
