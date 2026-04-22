"""GitHub Contents API publisher — commits daily snapshot files to a public repo."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from margin_api.archiver.publishers import PublishResult

GITHUB_API = "https://api.github.com"


class GitHubPublisher:
    """Publishes daily picks snapshots to a GitHub repository via the Contents API."""

    def __init__(self, credential: str, repo: str) -> None:
        self._repo = repo
        self._headers = {
            "Authorization": f"Bearer {credential}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def publish(
        self,
        date_str: str,
        snapshot_json: str,
        manifest_md: str,
        manifest_json: str,
        payload_hash: str,
    ) -> PublishResult:
        """Write snapshot + manifests to the repo for the given date."""
        path = self._snapshot_path(date_str)

        existing = await self._get_file_content(path)
        if existing is not None:
            content_str, _sha = existing
            try:
                existing_hash = json.loads(content_str).get("payload_hash", "")
            except (json.JSONDecodeError, AttributeError):
                existing_hash = ""

            if existing_hash == payload_hash:
                return PublishResult(publisher="github", success=True, skipped=True)

            raise RuntimeError(
                f"[github] hash mismatch for {date_str}: "
                f"existing={existing_hash}, new={payload_hash}"
            )

        await self._create_or_update_file(
            path,
            snapshot_json,
            f"snapshot({date_str}): add daily picks",
        )
        await self._create_or_update_file(
            "MANIFEST.md",
            manifest_md,
            f"snapshot({date_str}): update MANIFEST.md",
        )
        await self._create_or_update_file(
            "manifest.json",
            manifest_json,
            f"snapshot({date_str}): update manifest.json",
        )

        return PublishResult(publisher="github", success=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_file_content(self, path: str) -> tuple[str, str] | None:
        """Return (decoded_content, sha) for *path*, or None if the file does not exist."""
        url = f"{GITHUB_API}/repos/{self._repo}/contents/{path}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()
        encoded = data["content"].replace("\n", "")
        decoded = base64.b64decode(encoded).decode("utf-8")
        return decoded, data["sha"]

    async def _get_file_sha(self, path: str) -> str | None:
        """Return just the SHA for *path*, or None if the file does not exist."""
        result = await self._get_file_content(path)
        if result is None:
            return None
        return result[1]

    async def _create_or_update_file(
        self,
        path: str,
        content: str,
        message: str,
    ) -> None:
        """PUT the file to the GitHub Contents API, including SHA when updating."""
        url = f"{GITHUB_API}/repos/{self._repo}/contents/{path}"
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        body: dict[str, Any] = {"message": message, "content": encoded}

        existing_sha = await self._get_file_sha(path)
        if existing_sha is not None:
            body["sha"] = existing_sha

        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=self._headers, json=body)

        response.raise_for_status()

    @staticmethod
    def _snapshot_path(date_str: str) -> str:
        """Convert 'YYYY-MM-DD' to 'snapshots/YYYY/MM/DD.json'."""
        yyyy, mm, dd = date_str.split("-")
        return f"snapshots/{yyyy}/{mm}/{dd}.json"
