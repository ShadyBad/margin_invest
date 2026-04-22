"""Paragraph chunker for SEC 10-K risk factor sections.

Splits the risk_factors_text into individual risk factor paragraphs,
merges short fragments, drops boilerplate preamble, and computes
SHA-256 fingerprints for deduplication.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from margin_api.services.risk_diffing.config import MIN_CHUNK_CHARS

_WHITESPACE_RE = re.compile(r"\s+")

_PREAMBLE_PATTERNS = [
    re.compile(
        r"in addition to the other information.*?(?:risk factors|following)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"you should carefully consider.*?(?:risk factors|following)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"the following (?:discussion of )?risk factors",
        re.IGNORECASE,
    ),
]


@dataclass(frozen=True)
class RiskChunk:
    """A single risk factor paragraph with metadata."""

    index: int
    text: str
    text_hash: str


def _normalize_for_hash(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.lower()).strip()


def _compute_hash(text: str) -> str:
    normalized = _normalize_for_hash(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _is_boilerplate(text: str) -> bool:
    for pattern in _PREAMBLE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def chunk_risk_factors(text: str | None) -> list[RiskChunk]:
    """Split risk factor text into individual paragraphs."""
    if not text or not text.strip():
        return []
    raw_paragraphs = re.split(r"\n\s*\n", text.strip())
    paragraphs: list[str] = []
    for p in raw_paragraphs:
        cleaned = p.strip()
        if not cleaned:
            continue
        if _is_boilerplate(cleaned):
            continue
        paragraphs.append(cleaned)
    # Merge fragments that are too short to stand alone (orphan phrases like "See above.")
    # Uses a small orphan threshold (1/5 of MIN_CHUNK_CHARS) so that short-but-complete
    # sentences (>20 chars) are kept as distinct chunks.
    orphan_threshold = MIN_CHUNK_CHARS // 5
    merged: list[str] = []
    for para in paragraphs:
        if len(para) < orphan_threshold and merged:
            merged[-1] = merged[-1] + " " + para
        else:
            merged.append(para)
    return [RiskChunk(index=i, text=t, text_hash=_compute_hash(t)) for i, t in enumerate(merged)]
