"""Tests for deterministic MANIFEST generation."""

from __future__ import annotations

import json

from margin_api.archiver.manifest import ManifestEntry, generate_manifest_json, generate_manifest_md


def _sample_entries() -> list[ManifestEntry]:
    return [
        ManifestEntry(
            date="2026-04-21",
            picks_count=14,
            top_ticker="AAPL",
            top_score=87.3,
            payload_hash="c7d4e8f1" + "a" * 56,
            previous_hash="f9e2a1b3" + "b" * 56,
        ),
        ManifestEntry(
            date="2026-04-18",
            picks_count=12,
            top_ticker="MSFT",
            top_score=85.1,
            payload_hash="f9e2a1b3" + "b" * 56,
            previous_hash=None,
        ),
    ]


# --- MANIFEST.md tests ---


def test_md_idempotent() -> None:
    entries = _sample_entries()
    result1 = generate_manifest_md(entries)
    result2 = generate_manifest_md(entries)
    assert result1 == result2


def test_md_byte_identical_on_rerun() -> None:
    entries = _sample_entries()
    result1 = generate_manifest_md(entries).encode("utf-8")
    result2 = generate_manifest_md(entries).encode("utf-8")
    assert result1 == result2


def test_md_newest_first_ordering() -> None:
    entries = _sample_entries()
    result = generate_manifest_md(entries)
    idx_newer = result.index("2026-04-21")
    idx_older = result.index("2026-04-18")
    assert idx_newer < idx_older


def test_md_genesis_marker() -> None:
    entries = _sample_entries()
    result = generate_manifest_md(entries)
    assert "(genesis)" in result


def test_md_contains_verification_snippet() -> None:
    entries = _sample_entries()
    result = generate_manifest_md(entries)
    assert "hashlib" in result


# --- manifest.json tests ---


def test_json_idempotent() -> None:
    entries = _sample_entries()
    result1 = generate_manifest_json(entries)
    result2 = generate_manifest_json(entries)
    assert result1 == result2


def test_json_valid_json() -> None:
    entries = _sample_entries()
    result = generate_manifest_json(entries)
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) == 2


def test_json_newest_first() -> None:
    entries = _sample_entries()
    result = generate_manifest_json(entries)
    parsed = json.loads(result)
    assert parsed[0]["date"] == "2026-04-21"
    assert parsed[1]["date"] == "2026-04-18"


def test_json_all_fields_present() -> None:
    entries = _sample_entries()
    result = generate_manifest_json(entries)
    parsed = json.loads(result)
    required_fields = {
        "date",
        "picks_count",
        "top_ticker",
        "top_score",
        "payload_hash",
        "previous_hash",
    }
    for record in parsed:
        assert required_fields.issubset(record.keys()), f"Missing fields in record: {record}"
    # Check genesis entry has null previous_hash
    genesis = next(r for r in parsed if r["date"] == "2026-04-18")
    assert genesis["previous_hash"] is None
