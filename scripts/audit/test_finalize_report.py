from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit.finalize_report import (
    BundleHashMismatch,
    download_and_verify_bundle,
)


def _write_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    file_names = [
        "candidates_part_a.csv",
        "walk_forward_snapshots.csv",
        "component_attribution.csv",
        "conviction_calibration.csv",
        "performance_metrics.csv",
        "v2_proposal_inputs.csv",
    ]
    for name in file_names:
        (bundle / name).write_bytes(f"col1\nval-{name}\n".encode())
    files = {
        name: {"sha256": hashlib.sha256((bundle / name).read_bytes()).hexdigest()}
        for name in file_names
    }
    manifest = {
        "audit_version": "1.0",
        "audit_run_id": "00000000-0000-0000-0000-000000000001",
        "report_date": "2026-04-27",
        "engine_git_sha": "a" * 40,
        "engine_config_sha": "b" * 64,
        "data_provenance": {
            "scores_count": 1, "v4_scores_count": 0,
            "pit_prices_min_date": "2015-01-02",
            "pit_prices_max_date": "2026-04-25",
            "pit_distinct_tickers": 1, "spy_coverage_days": 1,
        },
        "files": files,
        "part_a": {"candidate_count": 1, "windows_closed": [30, 60, 63]},
        "part_b": {
            "start": "2015-01-31", "end": "2026-04-27",
            "cohort_count": 1, "rebalance": "monthly",
            "max_positions": 50, "selection": "exceptional+high",
        },
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    return bundle


def test_download_and_verify_bundle_passes_with_valid_hashes(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    manifest = download_and_verify_bundle(local_dir=bundle)
    assert manifest.audit_version == "1.0"


def test_download_and_verify_bundle_raises_on_hash_mismatch(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    (bundle / "candidates_part_a.csv").write_bytes(b"tampered")
    with pytest.raises(BundleHashMismatch):
        download_and_verify_bundle(local_dir=bundle)
