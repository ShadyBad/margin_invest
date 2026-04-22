"""ARQ task entry point — orchestrates daily snapshot generation and publishing."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date
from typing import Any

from margin_api.archiver.hasher import compute_payload_hash
from margin_api.archiver.manifest import ManifestEntry, generate_manifest_json, generate_manifest_md
from margin_api.archiver.models import HashChain
from margin_api.archiver.publishers import PublishResult
from margin_api.archiver.publishers.github import GitHubPublisher
from margin_api.archiver.publishers.r2 import R2Publisher
from margin_api.archiver.scheduler import is_trading_day
from margin_api.archiver.snapshot import generate
from margin_api.db.session import get_engine, get_session_factory
from margin_api.services.analytics import track_event

logger = logging.getLogger(__name__)


async def archive_daily_snapshot(ctx: dict[str, Any], target_date: str | None = None) -> dict[str, Any]:
    """Generate and publish the daily picks snapshot.

    This is the ARQ cron entry point that wires together:
    - Trading day check (NYSE calendar)
    - Snapshot generation from published V4Scores
    - SHA-256 payload hashing and hash-chain linking
    - Parallel publishing to GitHub and Cloudflare R2
    - PostHog alerting on failures
    """
    today = date.fromisoformat(target_date) if target_date else date.today()
    date_str = today.isoformat()

    # Step 1: Skip non-trading days
    if not is_trading_day(today):
        logger.info("Skipping archive for %s: not a trading day", date_str)
        return {"status": "skipped", "reason": "not_trading_day", "date": date_str}

    # Step 2: Generate snapshot from published scores
    model_hash = os.environ.get("MARGIN_GIT_SHA", "unknown")
    engine = get_engine()
    session_factory = get_session_factory(engine)  # type: ignore[no-untyped-call]

    async with session_factory() as session:
        snapshot = await generate(session=session, snapshot_date=today, model_hash=model_hash)

    if snapshot is None:
        logger.warning("No published scores found for %s", date_str)
        track_event(
            distinct_id="archiver",
            event="archiver.scores_not_ready",
            properties={"severity": "warning", "date": date_str},
        )
        return {"status": "skipped", "reason": "scores_not_ready", "date": date_str}

    # Step 3: Fetch previous hash for chain linking
    prev = await _fetch_previous_hash(date_str)
    if prev is not None:
        snapshot.hash_chain = HashChain(
            previous_date=prev["date"],
            previous_payload_hash=prev["hash"],
        )

    # Step 4: Compute payload hash
    payload_hash = compute_payload_hash(snapshot.model_dump(mode="json"))
    snapshot.payload_hash = payload_hash

    # Step 5: Build manifest
    top_pick = snapshot.top_picks[0] if snapshot.top_picks else None
    entry = ManifestEntry(
        date=date_str,
        picks_count=len(snapshot.top_picks),
        top_ticker=top_pick.ticker if top_pick else "N/A",
        top_score=top_pick.composite_score if top_pick else 0.0,
        payload_hash=payload_hash,
        previous_hash=snapshot.hash_chain.previous_payload_hash,
    )
    manifest_md = generate_manifest_md([entry])
    manifest_json = generate_manifest_json([entry])

    snapshot_json = json.dumps(
        snapshot.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False
    )

    # Step 6: Publish in parallel
    github_result, r2_result = await asyncio.gather(
        _publish_to_github(date_str, snapshot_json, manifest_md, manifest_json, payload_hash),
        _publish_to_r2(date_str, snapshot_json, manifest_json, payload_hash),
    )

    # Step 7: Report results
    picks_count = len(snapshot.top_picks)
    result = {
        "date": date_str,
        "picks": picks_count,
        "payload_hash": payload_hash,
        "github": github_result.success,
        "r2": r2_result.success,
    }

    if github_result.success and r2_result.success:
        result["status"] = "published"
        logger.info(
            "Snapshot published for %s: %d picks, hash=%s",
            date_str,
            picks_count,
            payload_hash[:12],
        )
    elif github_result.success or r2_result.success:
        result["status"] = "partial"
        if not github_result.success:
            logger.error("GitHub publish failed for %s: %s", date_str, github_result.error)
            track_event(
                distinct_id="archiver",
                event="archiver.github_failed",
                properties={
                    "severity": "warning",
                    "date": date_str,
                    "error": github_result.error,
                },
            )
        if not r2_result.success:
            logger.error("R2 publish failed for %s: %s", date_str, r2_result.error)
            track_event(
                distinct_id="archiver",
                event="archiver.r2_failed",
                properties={
                    "severity": "warning",
                    "date": date_str,
                    "error": r2_result.error,
                },
            )
    else:
        result["status"] = "failed"
        logger.critical(
            "Both publishers failed for %s: github=%s, r2=%s",
            date_str,
            github_result.error,
            r2_result.error,
        )
        track_event(
            distinct_id="archiver",
            event="archiver.publish_failed",
            properties={
                "severity": "critical",
                "date": date_str,
                "github_error": github_result.error,
                "r2_error": r2_result.error,
            },
        )

    return result


async def _publish_to_github(
    date_str: str,
    snapshot_json: str,
    manifest_md: str,
    manifest_json: str,
    payload_hash: str,
) -> PublishResult:
    """Publish snapshot files to the GitHub archive repository."""
    token = os.environ.get("ARCHIVE_GITHUB_TOKEN")
    repo = os.environ.get("ARCHIVE_GITHUB_REPO")

    if not token:
        return PublishResult(
            publisher="github", success=False, error="ARCHIVE_GITHUB_TOKEN not set"
        )
    if not repo:
        return PublishResult(publisher="github", success=False, error="ARCHIVE_GITHUB_REPO not set")

    try:
        publisher = GitHubPublisher(credential=token, repo=repo)
        return await publisher.publish(
            date_str=date_str,
            snapshot_json=snapshot_json,
            manifest_md=manifest_md,
            manifest_json=manifest_json,
            payload_hash=payload_hash,
        )
    except Exception as e:
        return PublishResult(publisher="github", success=False, error=str(e))


async def _publish_to_r2(
    date_str: str,
    snapshot_json: str,
    manifest_json: str,
    payload_hash: str,
) -> PublishResult:
    """Publish snapshot files to Cloudflare R2."""
    access_key = os.environ.get("ARCHIVE_R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("ARCHIVE_R2_SECRET_ACCESS_KEY")
    bucket = os.environ.get("ARCHIVE_R2_BUCKET")
    endpoint = os.environ.get("ARCHIVE_R2_ENDPOINT")

    if not all([access_key, secret_key, bucket, endpoint]):
        return PublishResult(publisher="r2", success=False, error="R2 credentials not configured")

    assert access_key and secret_key and bucket and endpoint  # narrowed: guard above ensures non-None

    try:
        publisher = R2Publisher(
            access_key_id=access_key,
            auth_credential=secret_key,
            bucket=bucket,
            endpoint_url=endpoint,
        )
        return await publisher.publish(
            date_str=date_str,
            snapshot_json=snapshot_json,
            manifest_json=manifest_json,
            payload_hash=payload_hash,
        )
    except Exception as e:
        return PublishResult(publisher="r2", success=False, error=str(e))


async def _fetch_previous_hash(current_date_str: str) -> dict[str, Any] | None:
    """Fetch the most recent manifest entry from GitHub to chain hashes.

    Returns {"date": ..., "hash": ...} or None if no previous manifest exists.
    """
    token = os.environ.get("ARCHIVE_GITHUB_TOKEN")
    repo = os.environ.get("ARCHIVE_GITHUB_REPO")

    if not token or not repo:
        return None

    try:
        publisher = GitHubPublisher(credential=token, repo=repo)
        result = await publisher._get_file_content("manifest.json")
        if result is None:
            return None

        content, _sha = result
        entries = json.loads(content)
        if not entries:
            return None

        # Entries are sorted newest-first by generate_manifest_json
        newest = entries[0]
        return {"date": newest["date"], "hash": newest["payload_hash"]}
    except Exception:
        logger.debug("Could not fetch previous hash for chain linking", exc_info=True)
        return None
