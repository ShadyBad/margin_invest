"""Audit bundler: deterministic CSV emit + manifest + R2 upload + hash verify."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pandas as pd

from margin_api.audit.schema import (
    AuditManifest,
    DataProvenance,
    FileHash,
    PartAStats,
    PartBStats,
)

CSV_FLOAT_FORMAT = "%.6f"


def emit_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to bytes deterministically.

    Columns sorted alphabetically; floats to 6 decimals; no index; LF terminator.
    """
    sorted_df = df.reindex(columns=sorted(df.columns))
    buf = io.StringIO()
    sorted_df.to_csv(
        buf,
        index=False,
        float_format=CSV_FLOAT_FORMAT,
        lineterminator="\n",
    )
    return buf.getvalue().encode("utf-8")


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class BundleArtifacts:
    candidates_part_a: pd.DataFrame
    walk_forward_snapshots: pd.DataFrame
    component_attribution: pd.DataFrame
    conviction_calibration: pd.DataFrame
    performance_metrics: pd.DataFrame
    v2_proposal_inputs: pd.DataFrame


def _file_hashes(artifacts: BundleArtifacts) -> dict[str, FileHash]:
    pairs = [
        ("candidates_part_a.csv", artifacts.candidates_part_a),
        ("walk_forward_snapshots.csv", artifacts.walk_forward_snapshots),
        ("component_attribution.csv", artifacts.component_attribution),
        ("conviction_calibration.csv", artifacts.conviction_calibration),
        ("performance_metrics.csv", artifacts.performance_metrics),
        ("v2_proposal_inputs.csv", artifacts.v2_proposal_inputs),
    ]
    return {name: FileHash(sha256=compute_sha256(emit_csv_bytes(df))) for name, df in pairs}


def build_manifest(
    *,
    artifacts: BundleArtifacts,
    report_date: date,
    engine_git_sha: str,
    engine_config_sha: str,
    scores_count: int,
    v4_scores_count: int,
    pit_prices_min_date: date,
    pit_prices_max_date: date,
    pit_distinct_tickers: int,
    spy_coverage_days: int,
    cohort_count: int,
    run_id: UUID | None = None,
) -> AuditManifest:
    return AuditManifest(
        audit_version="1.0",
        audit_run_id=run_id or uuid4(),
        report_date=report_date,
        engine_git_sha=engine_git_sha,
        engine_config_sha=engine_config_sha,
        data_provenance=DataProvenance(
            scores_count=scores_count,
            v4_scores_count=v4_scores_count,
            pit_prices_min_date=pit_prices_min_date,
            pit_prices_max_date=pit_prices_max_date,
            pit_distinct_tickers=pit_distinct_tickers,
            spy_coverage_days=spy_coverage_days,
        ),
        files=_file_hashes(artifacts),
        part_a=PartAStats(
            candidate_count=len(artifacts.candidates_part_a),
            windows_closed=[30, 60, 63],
        ),
        part_b=PartBStats(
            start=date(2015, 1, 31),
            end=report_date,
            cohort_count=cohort_count,
            rebalance="monthly",
            max_positions=50,
            selection="exceptional+high",
        ),
    )


def upload_bundle(
    *,
    s3_client: Any,
    bucket: str,
    prefix: str,
    artifacts: BundleArtifacts,
    manifest: AuditManifest,
) -> None:
    """Upload all 6 CSVs + manifest.json to R2 under the given prefix.

    Manifest is written LAST so a partial upload is detectable by an absent
    manifest.json — Stage 2 refuses to consume bundles missing manifest.json.
    """
    if not prefix.endswith("/"):
        prefix = prefix + "/"
    pairs = [
        ("candidates_part_a.csv", artifacts.candidates_part_a),
        ("walk_forward_snapshots.csv", artifacts.walk_forward_snapshots),
        ("component_attribution.csv", artifacts.component_attribution),
        ("conviction_calibration.csv", artifacts.conviction_calibration),
        ("performance_metrics.csv", artifacts.performance_metrics),
        ("v2_proposal_inputs.csv", artifacts.v2_proposal_inputs),
    ]
    for name, df in pairs:
        s3_client.put_object(
            Bucket=bucket,
            Key=f"{prefix}{name}",
            Body=emit_csv_bytes(df),
            ContentType="text/csv",
        )
    s3_client.put_object(
        Bucket=bucket,
        Key=f"{prefix}manifest.json",
        Body=manifest.model_dump_json(indent=2).encode("utf-8"),
        ContentType="application/json",
    )
