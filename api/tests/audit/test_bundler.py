from __future__ import annotations

import hashlib
from datetime import date as _date
from uuid import UUID

import pandas as pd
from margin_api.audit.bundler import BundleArtifacts, build_manifest, emit_csv_bytes
from margin_api.audit.schema import AuditManifest


def test_emit_csv_bytes_deterministic() -> None:
    df = pd.DataFrame({"b": [2, 1], "a": [10.0, 20.0]})
    assert emit_csv_bytes(df) == emit_csv_bytes(df)


def test_emit_csv_bytes_columns_sorted_alphabetically() -> None:
    df = pd.DataFrame({"b": [2], "a": [10.0], "c": ["x"]})
    out = emit_csv_bytes(df)
    assert out.split(b"\n")[0] == b"a,b,c"


def test_emit_csv_bytes_floats_fixed_precision() -> None:
    df = pd.DataFrame({"v": [1.123456789]})
    assert b"1.123457" in emit_csv_bytes(df)


def test_emit_csv_bytes_no_index() -> None:
    df = pd.DataFrame({"v": [1, 2, 3]}, index=["x", "y", "z"])
    out = emit_csv_bytes(df)
    assert out.startswith(b"v\n")


def test_emit_csv_bytes_sha256_stable_on_reorder() -> None:
    df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    df2 = pd.DataFrame({"b": [3, 4], "a": [1, 2]})
    h1 = hashlib.sha256(emit_csv_bytes(df1)).hexdigest()
    h2 = hashlib.sha256(emit_csv_bytes(df2)).hexdigest()
    assert h1 == h2


def _sample_artifacts() -> BundleArtifacts:
    return BundleArtifacts(
        candidates_part_a=pd.DataFrame({"ticker": ["AAPL"]}),
        walk_forward_snapshots=pd.DataFrame({"cohort_date": [_date(2026, 1, 31)]}),
        component_attribution=pd.DataFrame({"component": ["x"]}),
        conviction_calibration=pd.DataFrame({"tier": ["high"]}),
        performance_metrics=pd.DataFrame({"metric": ["cagr"], "value": [0.1]}),
        v2_proposal_inputs=pd.DataFrame({"component": ["x"]}),
    )


def _common_kwargs(run_id: UUID | None = None) -> dict:
    return dict(
        report_date=_date(2026, 4, 27),
        engine_git_sha="a" * 40,
        engine_config_sha="b" * 64,
        scores_count=1002,
        v4_scores_count=3,
        pit_prices_min_date=_date(2015, 1, 2),
        pit_prices_max_date=_date(2026, 4, 25),
        pit_distinct_tickers=5327,
        spy_coverage_days=2843,
        cohort_count=135,
        run_id=run_id,
    )


def test_build_manifest_assembles_all_files() -> None:
    artifacts = _sample_artifacts()
    manifest = build_manifest(artifacts=artifacts, **_common_kwargs())
    assert isinstance(manifest, AuditManifest)
    assert isinstance(manifest.audit_run_id, UUID)
    assert set(manifest.files.keys()) == {
        "candidates_part_a.csv",
        "walk_forward_snapshots.csv",
        "component_attribution.csv",
        "conviction_calibration.csv",
        "performance_metrics.csv",
        "v2_proposal_inputs.csv",
    }
    for fh in manifest.files.values():
        assert len(fh.sha256) == 64


def test_manifest_content_hash_deterministic() -> None:
    artifacts = _sample_artifacts()
    fixed = UUID("00000000-0000-0000-0000-000000000001")
    m1 = build_manifest(artifacts=artifacts, **_common_kwargs(run_id=fixed))
    m2 = build_manifest(artifacts=artifacts, **_common_kwargs(run_id=fixed))
    assert {k: v.sha256 for k, v in m1.files.items()} == \
           {k: v.sha256 for k, v in m2.files.items()}
