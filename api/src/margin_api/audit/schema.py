"""Pydantic models for audit output schema (manifest + CSV rows)."""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
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


class AttributionVerdict(str, Enum):
    KEEP = "keep"
    DEMOTE = "demote"
    CUT = "cut"
    UNDERPOWERED = "underpowered"


class AttributionMethod(str, Enum):
    TERCILE = "tercile"
    RANK_IC = "rank_ic"


class DataStatus(str, Enum):
    OK = "ok"
    DATA_UNAVAILABLE = "data_unavailable"
    PARTIAL = "partial"


class CandidatePartARow(BaseModel):
    model_config = ConfigDict(frozen=True)
    ticker: str
    scored_at: date
    conviction_level: str
    composite_percentile: float
    opportunity_type: str | None = None
    asymmetry_ratio: float | None = None
    candidate_return_30d: float | None = None
    candidate_return_60d: float | None = None
    candidate_return_63d: float | None = None
    spy_return_30d: float | None = None
    spy_return_60d: float | None = None
    spy_return_63d: float | None = None
    alpha_30d: float | None = None
    alpha_60d: float | None = None
    alpha_63d: float | None = None
    hit_30d: bool | None = None
    hit_60d: bool | None = None
    hit_63d: bool | None = None
    data_status: DataStatus = DataStatus.OK


class WalkForwardSnapshotRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    cohort_date: date
    cohort_size: int = Field(..., ge=0)
    portfolio_return: float
    benchmark_return: float
    excess_return: float
    turnover: float
    gross_return: float
    cost_drag_bps: float


class ComponentAttributionRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    component: str
    method: AttributionMethod
    window: str
    n_top: int | None = None
    n_bottom: int | None = None
    top_tercile_alpha: float | None = None
    bottom_tercile_alpha: float | None = None
    spread: float | None = None
    rank_ic: float | None = None
    ci_lo: float
    ci_hi: float
    p_value_raw: float = Field(..., ge=0.0, le=1.0)
    p_value_holm: float = Field(..., ge=0.0, le=1.0)
    verdict: AttributionVerdict


class ConvictionCalibrationRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    tier: str
    n: int = Field(..., ge=0)
    mean_alpha_60d: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float | None = None
    anova_p: float = Field(..., ge=0.0, le=1.0)
    monotonic: bool


class PerformanceMetricRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric: str
    value: float


class V2ProposalInputRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    component: str
    current_weight: float
    attribution_spread: float
    marginal_alpha_loss_when_zeroed: float | None = None
    proposed_action: AttributionVerdict
    proposed_new_weight: float
