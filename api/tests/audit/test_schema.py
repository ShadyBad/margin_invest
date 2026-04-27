from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from margin_api.audit.schema import AuditManifest, DataProvenance, FileHash, PartAStats, PartBStats
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
