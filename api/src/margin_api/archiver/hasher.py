"""Canonical JSON serialization and SHA-256 hashing for tamper-evident snapshots."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: dict[str, Any]) -> bytes:
    """Serialize dict to deterministic JSON bytes: sorted keys, no whitespace, UTF-8."""
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_payload_hash(snapshot_dict: dict[str, Any]) -> str:
    """Compute SHA-256 of the snapshot with payload_hash excluded."""
    without_hash = {k: v for k, v in snapshot_dict.items() if k != "payload_hash"}
    return sha256_hex(canonical_json(without_hash))


def compute_input_data_hash(score_rows: list[dict[str, Any]]) -> str:
    """Compute SHA-256 of the V4Score batch, sorted by ticker for determinism."""
    sorted_rows = sorted(score_rows, key=lambda r: r.get("ticker", ""))
    return sha256_hex(canonical_json({"scores": sorted_rows}))
