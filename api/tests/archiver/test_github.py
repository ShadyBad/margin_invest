"""Tests for GitHubPublisher."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from margin_api.archiver.publishers.github import GitHubPublisher

MOCK_CREDENTIAL = "MOCK_GH_CREDENTIAL_FOR_TESTING"  # noqa: S105
REPO = "ShadyBad/daily-picks"
DATE_STR = "2026-04-21"
PAYLOAD_HASH = "abc123def456"

SNAPSHOT_JSON = json.dumps({"payload_hash": PAYLOAD_HASH, "snapshot_date": DATE_STR})
MANIFEST_MD = "# Manifest\n"
MANIFEST_JSON = json.dumps({"dates": [DATE_STR]})


def _make_publisher() -> GitHubPublisher:
    return GitHubPublisher(credential=MOCK_CREDENTIAL, repo=REPO)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_happy_path() -> None:
    """New file: _get_file_sha returns None, _create_or_update_file is called 3x."""
    publisher = _make_publisher()

    with (
        patch.object(publisher, "_get_file_content", new=AsyncMock(return_value=None)),
        patch.object(publisher, "_create_or_update_file", new=AsyncMock()) as mock_create,
    ):
        result = await publisher.publish(
            date_str=DATE_STR,
            snapshot_json=SNAPSHOT_JSON,
            manifest_md=MANIFEST_MD,
            manifest_json=MANIFEST_JSON,
            payload_hash=PAYLOAD_HASH,
        )

    assert result.success is True
    assert result.publisher == "github"
    assert result.skipped is False
    assert mock_create.call_count == 3


# ---------------------------------------------------------------------------
# Idempotency — same hash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_idempotent_same_hash() -> None:
    """File exists with matching hash — should skip without error."""
    publisher = _make_publisher()

    existing_content = json.dumps({"payload_hash": PAYLOAD_HASH})
    existing_sha = "deadbeef"

    with patch.object(
        publisher,
        "_get_file_content",
        new=AsyncMock(return_value=(existing_content, existing_sha)),
    ):
        result = await publisher.publish(
            date_str=DATE_STR,
            snapshot_json=SNAPSHOT_JSON,
            manifest_md=MANIFEST_MD,
            manifest_json=MANIFEST_JSON,
            payload_hash=PAYLOAD_HASH,
        )

    assert result.success is True
    assert result.skipped is True
    assert result.publisher == "github"


# ---------------------------------------------------------------------------
# Hash mismatch — must raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_hash_mismatch_raises() -> None:
    """File exists with a different hash — must raise RuntimeError."""
    publisher = _make_publisher()

    existing_content = json.dumps({"payload_hash": "completely_different_hash"})
    existing_sha = "deadbeef"

    with patch.object(
        publisher,
        "_get_file_content",
        new=AsyncMock(return_value=(existing_content, existing_sha)),
    ):
        with pytest.raises(RuntimeError, match="hash mismatch"):
            await publisher.publish(
                date_str=DATE_STR,
                snapshot_json=SNAPSHOT_JSON,
                manifest_md=MANIFEST_MD,
                manifest_json=MANIFEST_JSON,
                payload_hash=PAYLOAD_HASH,
            )


# ---------------------------------------------------------------------------
# _snapshot_path
# ---------------------------------------------------------------------------


def test_snapshot_path_format() -> None:
    publisher = _make_publisher()
    result = publisher._snapshot_path("2026-04-21")
    assert result == "snapshots/2026/04/21.json"
