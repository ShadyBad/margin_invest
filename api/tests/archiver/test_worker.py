"""Tests for the archiver worker orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.archiver.models import HashChain
from margin_api.archiver.publishers import PublishResult

MODULE = "margin_api.archiver.worker"

_mock_ctx = lambda: {"redis": MagicMock()}  # noqa: E731


@pytest.mark.asyncio
async def test_skips_non_trading_day():
    """archive_daily_snapshot returns skipped when the date is not a trading day."""
    with patch(f"{MODULE}.is_trading_day", return_value=False):
        from margin_api.archiver.worker import archive_daily_snapshot

        result = await archive_daily_snapshot(_mock_ctx(), target_date="2026-04-19")

    assert result["status"] == "skipped"
    assert result["reason"] == "not_trading_day"
    assert result["date"] == "2026-04-19"


@pytest.mark.asyncio
async def test_alerts_when_scores_not_ready():
    """archive_daily_snapshot fires a PostHog event when no scores are available."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_sf = MagicMock()
    mock_sf.return_value = mock_session

    with (
        patch(f"{MODULE}.is_trading_day", return_value=True),
        patch(f"{MODULE}.generate", new_callable=AsyncMock, return_value=None),
        patch(f"{MODULE}.get_engine", return_value=MagicMock()),
        patch(f"{MODULE}.get_session_factory", return_value=mock_sf),
        patch(f"{MODULE}.track_event") as mock_track,
    ):
        from margin_api.archiver.worker import archive_daily_snapshot

        result = await archive_daily_snapshot(_mock_ctx(), target_date="2026-04-21")

    assert result["status"] == "skipped"
    assert result["reason"] == "scores_not_ready"
    mock_track.assert_called_once_with(
        distinct_id="archiver",
        event="archiver.scores_not_ready",
        properties={"severity": "warning", "date": "2026-04-21"},
    )


@pytest.mark.asyncio
async def test_full_success():
    """archive_daily_snapshot publishes to both GitHub and R2 successfully."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_sf = MagicMock()
    mock_sf.return_value = mock_session

    mock_snapshot = MagicMock()
    mock_snapshot.snapshot_date = "2026-04-21"
    mock_snapshot.top_picks = [MagicMock(ticker="AAPL", composite_score=87.3)]
    mock_snapshot.model_dump.return_value = {
        "snapshot_date": "2026-04-21",
        "payload_hash": "",
    }
    mock_snapshot.hash_chain = HashChain()

    with (
        patch(f"{MODULE}.is_trading_day", return_value=True),
        patch(f"{MODULE}.generate", new_callable=AsyncMock, return_value=mock_snapshot),
        patch(f"{MODULE}.get_engine", return_value=MagicMock()),
        patch(f"{MODULE}.get_session_factory", return_value=mock_sf),
        patch(f"{MODULE}._fetch_previous_hash", new_callable=AsyncMock, return_value=None),
        patch(f"{MODULE}._publish_to_github", new_callable=AsyncMock) as mock_gh,
        patch(f"{MODULE}._publish_to_r2", new_callable=AsyncMock) as mock_r2,
        patch(f"{MODULE}.compute_payload_hash", return_value="abc123def456"),
    ):
        mock_gh.return_value = PublishResult(publisher="github", success=True)
        mock_r2.return_value = PublishResult(publisher="r2", success=True)

        from margin_api.archiver.worker import archive_daily_snapshot

        result = await archive_daily_snapshot(_mock_ctx(), target_date="2026-04-21")

    assert result["status"] == "published"
    assert result["github"] is True
    assert result["r2"] is True
    assert result["picks"] == 1
    assert result["payload_hash"] == "abc123def456"


@pytest.mark.asyncio
async def test_partial_failure_github_down():
    """archive_daily_snapshot reports partial when GitHub fails but R2 succeeds."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_sf = MagicMock()
    mock_sf.return_value = mock_session

    mock_snapshot = MagicMock()
    mock_snapshot.snapshot_date = "2026-04-21"
    mock_snapshot.top_picks = [MagicMock(ticker="AAPL", composite_score=87.3)]
    mock_snapshot.model_dump.return_value = {
        "snapshot_date": "2026-04-21",
        "payload_hash": "",
    }
    mock_snapshot.hash_chain = HashChain()

    with (
        patch(f"{MODULE}.is_trading_day", return_value=True),
        patch(f"{MODULE}.generate", new_callable=AsyncMock, return_value=mock_snapshot),
        patch(f"{MODULE}.get_engine", return_value=MagicMock()),
        patch(f"{MODULE}.get_session_factory", return_value=mock_sf),
        patch(f"{MODULE}._fetch_previous_hash", new_callable=AsyncMock, return_value=None),
        patch(f"{MODULE}._publish_to_github", new_callable=AsyncMock) as mock_gh,
        patch(f"{MODULE}._publish_to_r2", new_callable=AsyncMock) as mock_r2,
        patch(f"{MODULE}.compute_payload_hash", return_value="abc123def456"),
        patch(f"{MODULE}.track_event") as mock_track,
    ):
        mock_gh.return_value = PublishResult(
            publisher="github", success=False, error="Connection refused"
        )
        mock_r2.return_value = PublishResult(publisher="r2", success=True)

        from margin_api.archiver.worker import archive_daily_snapshot

        result = await archive_daily_snapshot(_mock_ctx(), target_date="2026-04-21")

    assert result["status"] == "partial"
    assert result["github"] is False
    assert result["r2"] is True
    mock_track.assert_called_once_with(
        distinct_id="archiver",
        event="archiver.github_failed",
        properties={
            "severity": "warning",
            "date": "2026-04-21",
            "error": "Connection refused",
        },
    )
