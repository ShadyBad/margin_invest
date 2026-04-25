"""Tests for the filing diffing pipeline orchestrator."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_filing(
    id: int,
    ticker: str = "AAPL",
    risk_factors_text: str | None = "Some risk factor text about competition and markets.",
    period_end: datetime.date | None = None,
    filing_type: str = "10-K",
) -> MagicMock:
    ft = MagicMock()
    ft.id = id
    ft.ticker = ticker
    ft.filing_type = filing_type
    ft.period_end = period_end or datetime.date(2024 - id, 12, 31)
    ft.risk_factors_text = risk_factors_text
    return ft


class TestDiffSingleTicker:
    @pytest.mark.asyncio
    async def test_skips_when_fewer_than_two_filings(self) -> None:
        """Return skipped when only one 10-K is available for the ticker."""
        from margin_api.services.risk_diffing.pipeline import diff_single_ticker

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_filing(1)]
        session.execute = AsyncMock(return_value=mock_result)

        result = await diff_single_ticker(session=session, ticker="AAPL")

        assert result.status == "skipped"
        assert "fewer than 2" in result.reason

    @pytest.mark.asyncio
    async def test_skips_when_risk_text_is_none(self) -> None:
        """Return skipped when either filing has no risk_factors_text."""
        from margin_api.services.risk_diffing.pipeline import diff_single_ticker

        session = AsyncMock()
        filings = [
            _make_filing(1, risk_factors_text="Current year risk factors text here."),
            _make_filing(2, risk_factors_text=None),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = filings
        session.execute = AsyncMock(return_value=mock_result)

        result = await diff_single_ticker(session=session, ticker="AAPL")

        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_processes_ticker_successfully(self) -> None:
        """Return processed when both filings have valid text and analysis succeeds."""
        from margin_api.services.risk_diffing.pipeline import diff_single_ticker

        session = AsyncMock()
        current_filing = _make_filing(
            1,
            risk_factors_text=(
                "We face significant competition from established technology companies. "
                "Our business depends on attracting and retaining qualified personnel. "
                "We are subject to various regulatory requirements that may change."
            ),
        )
        prior_filing = _make_filing(
            2,
            risk_factors_text=(
                "We face competition from established technology companies. "
                "Our business depends on retaining qualified personnel. "
                "We are subject to regulatory requirements."
            ),
        )
        mock_db_result = MagicMock()
        mock_db_result.scalars.return_value.all.return_value = [current_filing, prior_filing]
        session.execute = AsyncMock(return_value=mock_db_result)
        session.add = MagicMock()

        fake_embeddings = [[0.1] * 1024, [0.2] * 1024, [0.3] * 1024]
        fake_analysis = {
            "material_changes": [
                {
                    "change_type": "expanded",
                    "topic": "Competition risk",
                    "severity": 4,
                    "summary_50_words": "Expanded to mention significant competition.",
                    "verbatim_new_text": "We face significant competition.",
                    "verbatim_old_text": "We face competition.",
                }
            ],
            "overall_risk_delta_score": 1.5,
            "model_confidence": 0.88,
            "analysis_tokens_used": 700,
            "analysis_cost_usd": 0.0007,
        }

        from margin_api.services.risk_diffing.diff_engine import ChangeCandidate

        fake_candidates = [
            ChangeCandidate(
                change_type="modified",
                old_text="We face competition.",
                new_text="We face significant competition.",
                similarity=0.92,
            )
        ]

        with (
            patch(
                "margin_api.services.risk_diffing.pipeline.embed_chunks",
                new=AsyncMock(return_value=fake_embeddings),
            ),
            patch(
                "margin_api.services.risk_diffing.pipeline.get_cached_embeddings",
                new=AsyncMock(return_value={}),
            ),
            patch(
                "margin_api.services.risk_diffing.pipeline.store_embeddings",
                new=AsyncMock(),
            ),
            patch(
                "margin_api.services.risk_diffing.pipeline.classify_changes",
                return_value=fake_candidates,
            ),
            patch(
                "margin_api.services.risk_diffing.pipeline.analyze_material_changes",
                new=AsyncMock(return_value=fake_analysis),
            ),
        ):
            result = await diff_single_ticker(session=session, ticker="AAPL")

        assert result.status == "processed"
        assert session.add.called
