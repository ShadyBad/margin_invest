"""Deterministic MANIFEST generation for the daily picks archive."""

from __future__ import annotations

import json

from pydantic import BaseModel


class ManifestEntry(BaseModel):
    date: str
    picks_count: int
    top_ticker: str
    top_score: float
    payload_hash: str
    previous_hash: str | None


def generate_manifest_md(entries: list[ManifestEntry]) -> str:
    sorted_entries = sorted(entries, key=lambda e: e.date, reverse=True)
    lines = [
        "# Margin Invest Daily Picks Archive",
        "",
        "Tamper-evident archive of daily scored picks. Each snapshot is SHA-256 hashed",
        "and linked to the previous day's hash, forming a verifiable chain.",
        "",
        "## How to Verify",
        "",
        "```python",
        "import hashlib, json",
        'snapshot = json.load(open("snapshots/2026/04/21.json"))',
        'payload_hash = snapshot.pop("payload_hash")',
        'canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()',
        "assert hashlib.sha256(canonical).hexdigest() == payload_hash",
        "```",
        "",
        "## Archive Index",
        "",
        "| Date | Picks | Top Pick | Payload Hash | Chain |",
        "|------|-------|----------|-------------|-------|",
    ]
    for e in sorted_entries:
        chain = f"`{e.previous_hash[:12]}...`" if e.previous_hash else "(genesis)"
        lines.append(
            f"| {e.date} | {e.picks_count} "
            f"| {e.top_ticker} ({e.top_score:.1f}) "
            f"| `{e.payload_hash[:12]}...` "
            f"| <- {chain} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate_manifest_json(entries: list[ManifestEntry]) -> str:
    sorted_entries = sorted(entries, key=lambda e: e.date, reverse=True)
    data = [e.model_dump(mode="json") for e in sorted_entries]
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
