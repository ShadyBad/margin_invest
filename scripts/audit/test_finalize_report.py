from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit.finalize_report import (
    BundleHashMismatch,
    download_and_verify_bundle,
    render_report,
)


def _write_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    # Write properly formatted CSVs
    (bundle / "performance_metrics.csv").write_text(
        "metric,value\nexcess_cagr,0.05\nsharpe,1.2\nmax_drawdown,-0.25\n"
    )
    (bundle / "component_attribution.csv").write_text(
        "component,method,window,n_top,n_bottom,spread,rank_ic,ci_lo,ci_hi,p_value_holm,verdict\n"
        "filter_1,tercile,30d,10,10,0.05,0.10,0.01,0.09,0.05,keep\n"
        "filter_2,tercile,30d,8,12,0.04,0.08,0.00,0.08,0.10,monitor\n"
    )
    (bundle / "conviction_calibration.csv").write_text(
        "tier,n,mean_alpha_60d,sharpe,sortino,max_drawdown,anova_p,monotonic\n"
        "exceptional,25,0.08,1.5,2.0,-0.15,0.01,true\n"
        "high,50,0.05,1.2,1.8,-0.20,0.02,true\n"
    )
    (bundle / "v2_proposal_inputs.csv").write_text(
        "component,current_weight,attribution_spread,marginal_alpha_loss_when_zeroed,proposed_action,proposed_new_weight\n"
        "filter_1,0.3,0.05,0.01,hold,0.3\n"
        "filter_2,0.2,0.04,,cut,0.0\n"
    )
    (bundle / "candidates_part_a.csv").write_text(
        "ticker,alpha_30d,alpha_60d\nAAPL,0.02,0.03\nMSFT,0.01,0.02\n"
    )
    (bundle / "walk_forward_snapshots.csv").write_text(
        "date,snapshot_data\n2026-04-27,test\n"
    )

    file_names = [
        "candidates_part_a.csv",
        "walk_forward_snapshots.csv",
        "component_attribution.csv",
        "conviction_calibration.csv",
        "performance_metrics.csv",
        "v2_proposal_inputs.csv",
    ]
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


def test_render_report_outputs_required_sections(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    out_path = tmp_path / "report.md"
    render_report(
        local_dir=bundle,
        out_path=out_path,
        r2_prefix="audits/2026-04-27/",
        r2_url="https://r2.example.com/audits/2026-04-27/",
        with_marginal_attribution=False,
    )
    text = out_path.read_text()
    for section in [
        "## 1. Executive Summary",
        "## 2. Methodology",
        "## 3. Component Inventory",
        "## 4. Performance Metrics",
        "## 5. Component Attribution",
        "## 6. Conviction Calibration",
        "## 7. Live Forward Track Record",
        "## 8. Kill List",
        "## 9. Statistical Power Disclaimer",
        "## 10. Reproducibility Footer",
    ]:
        assert section in text, f"missing required section: {section}"
    assert "Manifest content hash" in text
