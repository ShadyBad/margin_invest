"""Pydantic models for audit output schema (manifest + CSV rows)."""

from __future__ import annotations

import re
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FileHash(BaseModel):
    model_config = ConfigDict(frozen=True)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, v: str) -> str:
        if not _SHA256_RE.match(v):
            raise ValueError("sha256 must be 64 lowercase hex characters")
        return v


class DataProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    scores_count: int = Field(..., ge=0)
    v4_scores_count: int = Field(..., ge=0)
    pit_prices_min_date: date
    pit_prices_max_date: date
    pit_distinct_tickers: int = Field(..., ge=0)
    spy_coverage_days: int = Field(..., ge=0)


class PartAStats(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidate_count: int = Field(..., ge=0)
    windows_closed: list[int]


class PartBStats(BaseModel):
    model_config = ConfigDict(frozen=True)
    start: date
    end: date
    cohort_count: int = Field(..., ge=0)
    rebalance: str
    max_positions: int = Field(..., gt=0)
    selection: str


class AuditManifest(BaseModel):
    model_config = ConfigDict(frozen=True)
    audit_version: str = "1.0"
    audit_run_id: UUID
    report_date: date
    engine_git_sha: str
    engine_config_sha: str
    data_provenance: DataProvenance
    files: dict[str, FileHash]
    part_a: PartAStats
    part_b: PartBStats
