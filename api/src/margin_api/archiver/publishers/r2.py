"""Cloudflare R2 publisher — mirrors daily snapshot files via S3-compatible API."""

from __future__ import annotations

from typing import Any

import boto3

from margin_api.archiver.publishers import PublishResult


class R2Publisher:
    """Publishes daily picks snapshots to Cloudflare R2 via S3-compatible API."""

    def __init__(
        self,
        access_key_id: str,
        auth_credential: str,
        bucket: str,
        endpoint_url: str,
    ) -> None:
        self._access_key_id = access_key_id
        self._auth_credential = auth_credential
        self._bucket = bucket
        self._endpoint_url = endpoint_url

    def _get_client(self) -> Any:
        """Create and return a boto3 S3 client configured for R2."""
        creds = {
            "endpoint_url": self._endpoint_url,
            "aws_access_key_id": self._access_key_id,
            "aws_secret_access_key": self._auth_credential,
        }
        return boto3.client("s3", **creds)

    async def publish(
        self,
        date_str: str,
        snapshot_json: str,
        manifest_json: str,
        payload_hash: str,
    ) -> PublishResult:
        """Upload snapshot, SHA digest, and manifest to R2 for the given date."""
        client = self._get_client()
        key = self._snapshot_key(date_str)
        sha_key = self._sha_key(date_str)

        if self._object_exists(client, key):
            existing_hash = self._read_object(client, sha_key)
            if existing_hash == payload_hash:
                return PublishResult(publisher="r2", success=True, skipped=True)
            raise RuntimeError(
                f"[r2] hash mismatch for {date_str}: "
                f"existing={existing_hash}, new={payload_hash}"
            )

        client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=snapshot_json.encode("utf-8"),
            ContentType="application/json",
        )
        client.put_object(
            Bucket=self._bucket,
            Key=sha_key,
            Body=payload_hash.encode("utf-8"),
            ContentType="text/plain",
        )
        client.put_object(
            Bucket=self._bucket,
            Key="manifest.json",
            Body=manifest_json.encode("utf-8"),
            ContentType="application/json",
        )

        return PublishResult(publisher="r2", success=True)

    def _object_exists(self, client: Any, key: str) -> bool:
        """Return True if *key* exists in the bucket, False otherwise."""
        try:
            client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def _read_object(self, client: Any, key: str) -> str:
        """Read *key* from the bucket and return its content as a UTF-8 string."""
        response = client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read().decode("utf-8")

    @staticmethod
    def _snapshot_key(date_str: str) -> str:
        """Convert 'YYYY-MM-DD' to 'snapshots/YYYY/MM/DD.json'."""
        yyyy, mm, dd = date_str.split("-")
        return f"snapshots/{yyyy}/{mm}/{dd}.json"

    @staticmethod
    def _sha_key(date_str: str) -> str:
        """Return the SHA256 sidecar key for a given date string."""
        return R2Publisher._snapshot_key(date_str) + ".sha256"
