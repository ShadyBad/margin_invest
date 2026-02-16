"""Cloudflare R2 avatar storage service."""

from __future__ import annotations

import os
import time

import boto3


class AvatarStorageService:
    """Manages avatar image uploads and deletions on Cloudflare R2."""

    def __init__(self) -> None:
        account_id = os.environ["R2_ACCOUNT_ID"]
        self.bucket_name = os.environ.get("R2_BUCKET_NAME", "margin-avatars")
        self.public_url = os.environ["R2_PUBLIC_URL"].rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )

    def _storage_key(self, user_id: int) -> str:
        return f"avatars/{user_id}.webp"

    def get_public_url(self, user_id: int) -> str:
        return f"{self.public_url}/{self._storage_key(user_id)}"

    def upload(self, user_id: int, image_bytes: bytes) -> str:
        """Upload avatar bytes to R2. Returns the public URL."""
        key = self._storage_key(user_id)
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=image_bytes,
            ContentType="image/webp",
        )
        return f"{self.public_url}/{key}?v={int(time.time())}"

    def delete(self, user_id: int) -> None:
        """Delete avatar from R2."""
        key = self._storage_key(user_id)
        self._client.delete_object(Bucket=self.bucket_name, Key=key)
