from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from margin_api.audit.schema import (
    AttributionMethod,
    AuditManifest,
    CandidatePartARow,
    ComponentAttributionRow,
    DataProvenance,
    FileHash,
    PartAStats,
    PartBStats,
)
from pydantic import ValidationError


def test_audit_manifest_constructs_with_required_fields() -> None:
    manifest = AuditManifest(
        audit_version="1.0",
        audit_run_id=uuid4(),
        report_date=date(2026, 4, 27),
        engine_git_sha="abc123" * 7,
        engine_config_sha="def456" * 7,
        data_provenance=DataProvenance(
            scores_count=1002,
            v4_scores_count=3,
            pit_prices_min_date=date(2015, 1, 2),
            pit_prices_max_date=date(2026, 4, 25),
            pit_distinct_tickers=5327,
            spy_coverage_days=2843,
        ),
        files={"candidates_part_a.csv": FileHash(sha256="a" * 64)},
        part_a=PartAStats(candidate_count=1002, windows_closed=[30, 60, 63]),
        part_b=PartBStats(
            start=date(2015, 1, 31),
            end=date(2026, 4, 25),
            cohort_count=135,
            rebalance="monthly",
            max_positions=50,
            selection="exceptional+high",
        ),
    )
    assert manifest.audit_version == "1.0"
    assert len(manifest.files) == 1


def test_audit_manifest_rejects_invalid_sha256() -> None:
    with pytest.raises(ValidationError):
        FileHash(sha256="not-hex")


def test_candidate_part_a_row_with_all_windows() -> None:
    row = CandidatePartARow(
        ticker="AAPL",
        scored_at=date(2026, 2, 15),
        conviction_level="high",
        composite_percentile=87.3,
        opportunity_type="compounder",
        asymmetry_ratio=2.1,
        candidate_return_30d=0.04,
        candidate_return_60d=0.07,
        candidate_return_63d=0.075,
        spy_return_30d=0.02,
        spy_return_60d=0.03,
        spy_return_63d=0.031,
        alpha_30d=0.02,
        alpha_60d=0.04,
        alpha_63d=0.044,
        hit_30d=True,
        hit_60d=True,
        hit_63d=True,
        data_status="ok",
    )
    assert row.alpha_30d == pytest.approx(0.02)


def test_candidate_part_a_row_data_unavailable() -> None:
    row = CandidatePartARow(
        ticker="DELISTED",
        scored_at=date(2026, 2, 15),
        conviction_level="medium",
        composite_percentile=71.0,
        opportunity_type=None,
        asymmetry_ratio=None,
        candidate_return_30d=None,
        candidate_return_60d=None,
        candidate_return_63d=None,
        spy_return_30d=0.02,
        spy_return_60d=0.03,
        spy_return_63d=0.031,
        alpha_30d=None,
        alpha_60d=None,
        alpha_63d=None,
        hit_30d=None,
        hit_60d=None,
        hit_63d=None,
        data_status="data_unavailable",
    )
    assert row.data_status == "data_unavailable"


def test_attribution_verdict_enum_strict() -> None:
    with pytest.raises(ValidationError):
        ComponentAttributionRow(
            component="bogus",
            method=AttributionMethod.TERCILE,
            window="30d",
            n_top=50,
            n_bottom=50,
            top_tercile_alpha=0.05,
            bottom_tercile_alpha=0.01,
            spread=0.04,
            rank_ic=None,
            ci_lo=0.02,
            ci_hi=0.06,
            p_value_raw=0.01,
            p_value_holm=0.05,
            verdict="invalid_verdict",  # type: ignore[arg-type]
        )
