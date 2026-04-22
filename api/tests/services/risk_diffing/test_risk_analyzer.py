"""Tests for Claude-powered risk factor analyzer."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.services.risk_diffing.diff_engine import ChangeCandidate
from margin_api.services.risk_diffing.risk_analyzer import (
    SYSTEM_PROMPT,
    analyze_material_changes,
    build_user_prompt,
)


class TestBuildUserPrompt:
    def test_includes_new_change(self) -> None:
        candidates = [
            ChangeCandidate(
                change_type="new", old_text=None, new_text="New risk about AI.", similarity=None
            )
        ]
        prompt = build_user_prompt("AAPL", candidates)
        assert "NEW RISK FACTOR" in prompt
        assert "New risk about AI." in prompt

    def test_includes_removed_change(self) -> None:
        candidates = [
            ChangeCandidate(
                change_type="removed",
                old_text="Old risk about legacy systems.",
                new_text=None,
                similarity=None,
            )
        ]
        prompt = build_user_prompt("AAPL", candidates)
        assert "REMOVED RISK FACTOR" in prompt
        assert "Old risk about legacy systems." in prompt

    def test_includes_modified_change(self) -> None:
        candidates = [
            ChangeCandidate(
                change_type="modified",
                old_text="Old version.",
                new_text="New expanded version.",
                similarity=0.90,
            )
        ]
        prompt = build_user_prompt("AAPL", candidates)
        assert "MODIFIED RISK FACTOR" in prompt
        assert "Old version." in prompt
        assert "New expanded version." in prompt


class TestAnalyzeMaterialChanges:
    @pytest.mark.asyncio
    async def test_returns_structured_result(self) -> None:
        candidates = [
            ChangeCandidate(
                change_type="new", old_text=None, new_text="Risk about AI.", similarity=None
            )
        ]
        mock_response = {
            "material_changes": [
                {
                    "change_type": "new",
                    "topic": "AI regulation",
                    "severity": 6,
                    "summary_50_words": "New disclosure.",
                    "verbatim_new_text": "Risk about AI.",
                    "verbatim_old_text": None,
                }
            ],
            "overall_risk_delta_score": 3.0,
            "model_confidence": 0.85,
        }
        mock_block = MagicMock()
        mock_block.text = json.dumps(mock_response)
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.usage = MagicMock(input_tokens=500, output_tokens=200)
        with patch("margin_api.services.risk_diffing.risk_analyzer._get_client") as mc:
            mc.return_value.messages.create = AsyncMock(return_value=mock_message)
            session = AsyncMock()
            session.add = MagicMock()  # add() is sync in SQLAlchemy
            session.commit = AsyncMock()
            result = await analyze_material_changes(
                session=session, ticker="AAPL", candidates=candidates
            )
        assert result is not None
        assert result["overall_risk_delta_score"] == 3.0
        assert len(result["material_changes"]) == 1
        assert result["material_changes"][0]["severity"] == 6

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_candidates(self) -> None:
        session = AsyncMock()
        result = await analyze_material_changes(session=session, ticker="AAPL", candidates=[])
        assert result is None

    @pytest.mark.asyncio
    async def test_logs_to_llm_call_log(self) -> None:
        candidates = [
            ChangeCandidate(
                change_type="new", old_text=None, new_text="Risk text.", similarity=None
            )
        ]
        mock_block = MagicMock()
        mock_block.text = json.dumps(
            {
                "material_changes": [],
                "overall_risk_delta_score": 0.0,
                "model_confidence": 0.9,
            }
        )
        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.usage = MagicMock(input_tokens=100, output_tokens=50)
        with patch("margin_api.services.risk_diffing.risk_analyzer._get_client") as mc:
            mc.return_value.messages.create = AsyncMock(return_value=mock_message)
            session = AsyncMock()
            session.add = MagicMock()  # add() is sync in SQLAlchemy
            session.commit = AsyncMock()
            await analyze_material_changes(session=session, ticker="TEST", candidates=candidates)
        assert session.add.called


class TestSystemPrompt:
    def test_contains_severity_guide(self) -> None:
        assert "1-3" in SYSTEM_PROMPT or "1 to 3" in SYSTEM_PROMPT

    def test_contains_output_schema(self) -> None:
        assert "material_changes" in SYSTEM_PROMPT
        assert "overall_risk_delta_score" in SYSTEM_PROMPT
