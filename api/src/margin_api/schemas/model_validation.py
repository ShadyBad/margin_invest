"""Model validation API response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MetricDistributionResponse(BaseModel):
    """Descriptive statistics for a single metric across seeds."""

    mean: float
    median: float
    std: float
    min: float
    max: float
    ci_lower: float
    ci_upper: float
    cv: float


class GateCheckResponse(BaseModel):
    """Result of a single promotion gate check."""

    name: str
    value: float
    threshold: float
    passed: bool


class ModelComparisonResponse(BaseModel):
    """Statistical comparison between candidate and incumbent model."""

    p_value: float
    effect_size: float
    significant: bool
    label: str
    n_compared: int
    mean_difference: float


class SeedDetailResponse(BaseModel):
    """Per-seed training result."""

    seed: int
    rank_ic: float
    n_clusters: int
    n_samples: int
    selected: bool


class SeedValidationReportResponse(BaseModel):
    """Full seed validation report for a single training run group."""

    run_group_id: str
    created_at: str
    n_seeds: int
    gate_passed: bool
    selected_seed: int | None
    metric_distributions: dict[str, MetricDistributionResponse]
    gate_checks: list[GateCheckResponse]
    seed_details: list[SeedDetailResponse]
    environment_snapshot: dict
    comparison: ModelComparisonResponse | None = None


class SeedValidationHistoryResponse(BaseModel):
    """Paginated list of seed validation reports."""

    reports: list[SeedValidationReportResponse]
    total: int
