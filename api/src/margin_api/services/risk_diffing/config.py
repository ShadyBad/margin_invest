"""Configuration for the risk factor diffing pipeline.

All tunables are read from environment variables with sensible defaults.
"""

from __future__ import annotations

import os


def is_enabled() -> bool:
    """Check if risk diffing pipeline is enabled."""
    return os.environ.get("MARGIN_RISK_DIFF_ENABLED", "false").lower() in ("1", "true", "yes")


def get_voyage_model() -> str:
    return os.environ.get("MARGIN_VOYAGE_MODEL", "voyage-finance-2")


def get_voyage_credential() -> str:
    return os.environ.get("MARGIN_VOYAGE_CREDENTIAL", "")


def get_analysis_model() -> str:
    return os.environ.get("MARGIN_RISK_DIFF_ANALYSIS_MODEL", "claude-haiku-4-5-20251001")


def get_similarity_threshold() -> float:
    try:
        return float(os.environ.get("MARGIN_RISK_DIFF_SIMILARITY_THRESHOLD", "0.85"))
    except ValueError:
        return 0.85


def get_unchanged_threshold() -> float:
    """Above this cosine similarity, paragraphs are considered identical."""
    try:
        return float(os.environ.get("MARGIN_RISK_DIFF_UNCHANGED_THRESHOLD", "0.95"))
    except ValueError:
        return 0.95


def get_length_change_threshold() -> float:
    """Minimum fractional length change to flag a matched pair for review."""
    try:
        return float(os.environ.get("MARGIN_RISK_DIFF_LENGTH_CHANGE_THRESHOLD", "0.20"))
    except ValueError:
        return 0.20


def get_prompt_version() -> str:
    return os.environ.get("MARGIN_RISK_DIFF_PROMPT_VERSION", "risk_diff_v1")


def get_max_concurrency() -> int:
    try:
        return int(os.environ.get("MARGIN_RISK_DIFF_MAX_CONCURRENCY", "4"))
    except ValueError:
        return 4


def get_batch_size() -> int:
    try:
        return int(os.environ.get("MARGIN_RISK_DIFF_BATCH_SIZE", "50"))
    except ValueError:
        return 50


EMBEDDING_DIMENSIONS = 1024
EMBEDDING_BATCH_SIZE = 128
MIN_CHUNK_CHARS = 100
