"""Tests for R2Publisher."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from margin_api.archiver.publishers.r2 import R2Publisher

MOCK_KEY = "MOCK_R2_KEY_FOR_TESTING"  # noqa: S105
MOCK_AUTH = "MOCK_R2_AUTH_FOR_TESTING"  # noqa: S105
BUCKET = "daily-picks"
ENDPOINT = "https://example.r2.cloudflarestorage.com"
DATE_STR = "2026-04-21"
PAYLOAD_HASH = "abc123def456"
SNAPSHOT_JSON = '{"picks": []}'
MANIFEST_JSON = '{"dates": ["2026-04-21"]}'


def _make_publisher() -> R2Publisher:
    return R2Publisher(
        access_key_id=MOCK_KEY,
        auth_credential=MOCK_AUTH,
        bucket=BUCKET,
        endpoint_url=ENDPOINT,
    )


@pytest.mark.asyncio
async def test_publish_happy_path() -> None:
    """Object does not exist — 3 put_object calls, success=True."""
    publisher = _make_publisher()
    mock_client = MagicMock()
    mock_client.head_object.side_effect = Exception("Not Found")

    with patch.object(publisher, "_get_client", return_value=mock_client):
        result = await publisher.publish(DATE_STR, SNAPSHOT_JSON, MANIFEST_JSON, PAYLOAD_HASH)

    assert result.success is True
    assert result.skipped is False
    assert mock_client.put_object.call_count == 3


@pytest.mark.asyncio
async def test_publish_idempotent_same_hash() -> None:
    """Object exists with matching hash — returns skipped=True without uploading."""
    publisher = _make_publisher()
    mock_client = MagicMock()
    mock_client.head_object.return_value = {}
    body_mock = MagicMock()
    body_mock.read.return_value = PAYLOAD_HASH.encode("utf-8")
    mock_client.get_object.return_value = {"Body": body_mock}

    with patch.object(publisher, "_get_client", return_value=mock_client):
        result = await publisher.publish(DATE_STR, SNAPSHOT_JSON, MANIFEST_JSON, PAYLOAD_HASH)

    assert result.success is True
    assert result.skipped is True
    mock_client.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_publish_hash_mismatch_raises() -> None:
    """Object exists with a different hash — must raise RuntimeError."""
    publisher = _make_publisher()
    mock_client = MagicMock()
    mock_client.head_object.return_value = {}
    body_mock = MagicMock()
    body_mock.read.return_value = b"completely_different_hash"
    mock_client.get_object.return_value = {"Body": body_mock}

    with patch.object(publisher, "_get_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="hash mismatch"):
            await publisher.publish(DATE_STR, SNAPSHOT_JSON, MANIFEST_JSON, PAYLOAD_HASH)


def test_key_format() -> None:
    """Verify snapshot and SHA key format for a given date string."""
    publisher = _make_publisher()
    snapshot_key = publisher._snapshot_key("2026-04-21")
    sha_key = publisher._sha_key("2026-04-21")

    assert snapshot_key == "snapshots/2026/04/21.json"
    assert sha_key == "snapshots/2026/04/21.json.sha256"
