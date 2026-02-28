"""Reproducibility environment capture and data hashing."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version

_TRACKED_LIBRARIES = (
    "numpy",
    "scikit-learn",
    "lightgbm",
    "torch",
    "pandas",
    "scipy",
)


def capture_environment() -> dict:
    """Capture a snapshot of the runtime environment for reproducibility.

    Returns:
        Dict with python_version, platform, libraries, git_commit,
        and determinism_flags.
    """
    return {
        "python_version": platform.python_version(),
        "platform": f"{sys.platform}-{platform.machine()}",
        "libraries": _get_library_versions(),
        "git_commit": _get_git_commit(),
        "determinism_flags": _get_determinism_flags(),
    }


def compute_data_hash(tickers: list[str], timestamp: str) -> str:
    """Compute a deterministic SHA-256 hash of tickers + timestamp.

    Tickers are sorted for order-independence.

    Args:
        tickers: List of ticker symbols.
        timestamp: ISO-8601 timestamp string.

    Returns:
        64-character lowercase hex digest.
    """
    payload = json.dumps(
        {"tickers": sorted(tickers), "timestamp": timestamp},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_library_versions() -> dict[str, str]:
    """Get installed versions for tracked libraries."""
    libs: dict[str, str] = {}
    for pkg in _TRACKED_LIBRARIES:
        try:
            libs[pkg] = version(pkg)
        except PackageNotFoundError:
            libs[pkg] = "not installed"
    return libs


def _get_git_commit() -> str:
    """Get the current git commit hash."""
    # Prefer explicit env var (set in CI/containers)
    commit = os.environ.get("GIT_COMMIT")
    if commit:
        return commit

    # Fall back to subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "unknown"


def _get_determinism_flags() -> dict:
    """Collect determinism-related settings."""
    flags: dict = {
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "not set"),
    }

    try:
        import torch

        flags["torch_deterministic"] = torch.are_deterministic_algorithms_enabled()
        flags["torch_cudnn_benchmark"] = torch.backends.cudnn.benchmark
    except ImportError:
        pass

    return flags
