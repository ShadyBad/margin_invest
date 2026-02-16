"""Tests for AvatarStorageService (Cloudflare R2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


ENV_VARS = {
    "R2_ACCOUNT_ID": "fake-account-id",
    "R2_BUCKET_NAME": "test-bucket",
    "R2_PUBLIC_URL": "https://cdn.example.com",
    "R2_ACCESS_KEY_ID": "fake-key",
    "R2_SECRET_ACCESS_KEY": "fake-secret",
}


@patch("boto3.client")
def test_init_reads_env_vars(mock_boto_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)

    from margin_api.services.storage import AvatarStorageService

    svc = AvatarStorageService()

    assert svc.bucket_name == "test-bucket"
    assert svc.public_url == "https://cdn.example.com"
    mock_boto_client.assert_called_once_with(
        "s3",
        endpoint_url="https://fake-account-id.r2.cloudflarestorage.com",
        aws_access_key_id="fake-key",
        aws_secret_access_key="fake-secret",
        region_name="auto",
    )


@patch("boto3.client")
def test_storage_key(mock_boto_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)

    from margin_api.services.storage import AvatarStorageService

    svc = AvatarStorageService()
    assert svc._storage_key(42) == "avatars/42.webp"


@patch("boto3.client")
def test_get_public_url(mock_boto_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)

    from margin_api.services.storage import AvatarStorageService

    svc = AvatarStorageService()
    assert svc.get_public_url(42) == "https://cdn.example.com/avatars/42.webp"


@patch("boto3.client")
def test_get_public_url_strips_trailing_slash(
    mock_boto_client: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("R2_PUBLIC_URL", "https://cdn.example.com/")

    from margin_api.services.storage import AvatarStorageService

    svc = AvatarStorageService()
    assert svc.get_public_url(42) == "https://cdn.example.com/avatars/42.webp"


@patch("boto3.client")
def test_upload_calls_put_object(
    mock_boto_client: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)

    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    from margin_api.services.storage import AvatarStorageService

    svc = AvatarStorageService()
    image_data = b"\x00\x01\x02"
    url = svc.upload(42, image_data)

    mock_s3.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="avatars/42.webp",
        Body=image_data,
        ContentType="image/webp",
    )
    assert url.startswith("https://cdn.example.com/avatars/42.webp?v=")
    # Verify the cache-buster is a numeric timestamp
    version = url.split("?v=")[1]
    assert version.isdigit()


@patch("boto3.client")
def test_delete_calls_delete_object(
    mock_boto_client: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key, value in ENV_VARS.items():
        monkeypatch.setenv(key, value)

    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    from margin_api.services.storage import AvatarStorageService

    svc = AvatarStorageService()
    svc.delete(42)

    mock_s3.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="avatars/42.webp",
    )
