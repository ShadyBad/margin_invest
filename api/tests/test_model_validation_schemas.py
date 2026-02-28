"""Tests for model validation API schemas."""

from __future__ import annotations

from margin_api.schemas.model_validation import (
    GateCheckResponse,
    MetricDistributionResponse,
    ModelComparisonResponse,
    SeedDetailResponse,
    SeedValidationHistoryResponse,
    SeedValidationReportResponse,
)

# ---------------------------------------------------------------------------
# MetricDistributionResponse
# ---------------------------------------------------------------------------


def test_metric_distribution_instantiation():
    dist = MetricDistributionResponse(
        mean=0.45,
        median=0.44,
        std=0.03,
        min=0.38,
        max=0.52,
        ci_lower=0.39,
        ci_upper=0.51,
        cv=0.067,
    )
    assert dist.mean == 0.45
    assert dist.median == 0.44
    assert dist.std == 0.03
    assert dist.min == 0.38
    assert dist.max == 0.52
    assert dist.ci_lower == 0.39
    assert dist.ci_upper == 0.51
    assert dist.cv == 0.067


def test_metric_distribution_negative_values():
    dist = MetricDistributionResponse(
        mean=-0.1,
        median=-0.05,
        std=0.02,
        min=-0.3,
        max=0.01,
        ci_lower=-0.25,
        ci_upper=0.0,
        cv=-0.2,
    )
    assert dist.mean == -0.1
    assert dist.min == -0.3


# ---------------------------------------------------------------------------
# GateCheckResponse
# ---------------------------------------------------------------------------


def test_gate_check_passed():
    gate = GateCheckResponse(
        name="rank_ic_median",
        value=0.22,
        threshold=0.15,
        passed=True,
    )
    assert gate.name == "rank_ic_median"
    assert gate.value == 0.22
    assert gate.threshold == 0.15
    assert gate.passed is True


def test_gate_check_failed():
    gate = GateCheckResponse(
        name="rank_ic_cv",
        value=0.85,
        threshold=0.50,
        passed=False,
    )
    assert gate.passed is False


# ---------------------------------------------------------------------------
# ModelComparisonResponse
# ---------------------------------------------------------------------------


def test_model_comparison_significant():
    comp = ModelComparisonResponse(
        p_value=0.002,
        effect_size=0.45,
        significant=True,
        label="new_vs_incumbent",
        n_compared=30,
        mean_difference=0.08,
    )
    assert comp.p_value == 0.002
    assert comp.effect_size == 0.45
    assert comp.significant is True
    assert comp.label == "new_vs_incumbent"
    assert comp.n_compared == 30
    assert comp.mean_difference == 0.08


def test_model_comparison_not_significant():
    comp = ModelComparisonResponse(
        p_value=0.35,
        effect_size=0.05,
        significant=False,
        label="new_vs_incumbent",
        n_compared=30,
        mean_difference=0.01,
    )
    assert comp.significant is False


# ---------------------------------------------------------------------------
# SeedDetailResponse
# ---------------------------------------------------------------------------


def test_seed_detail_selected():
    detail = SeedDetailResponse(
        seed=42,
        rank_ic=0.28,
        n_clusters=5,
        n_samples=150,
        selected=True,
    )
    assert detail.seed == 42
    assert detail.rank_ic == 0.28
    assert detail.n_clusters == 5
    assert detail.n_samples == 150
    assert detail.selected is True


def test_seed_detail_not_selected():
    detail = SeedDetailResponse(
        seed=99,
        rank_ic=0.12,
        n_clusters=3,
        n_samples=150,
        selected=False,
    )
    assert detail.selected is False


# ---------------------------------------------------------------------------
# SeedValidationReportResponse
# ---------------------------------------------------------------------------


def _make_report(**overrides) -> SeedValidationReportResponse:
    """Helper to build a full report with sensible defaults."""
    defaults = dict(
        run_group_id="rg-20260227-001",
        created_at="2026-02-27T12:00:00Z",
        n_seeds=30,
        gate_passed=True,
        selected_seed=42,
        metric_distributions={
            "rank_ic": MetricDistributionResponse(
                mean=0.22,
                median=0.21,
                std=0.03,
                min=0.15,
                max=0.30,
                ci_lower=0.16,
                ci_upper=0.28,
                cv=0.14,
            ),
        },
        gate_checks=[
            GateCheckResponse(
                name="rank_ic_median",
                value=0.21,
                threshold=0.15,
                passed=True,
            ),
        ],
        seed_details=[
            SeedDetailResponse(
                seed=42,
                rank_ic=0.28,
                n_clusters=5,
                n_samples=150,
                selected=True,
            ),
        ],
        environment_snapshot={"python_version": "3.13.5", "numpy_version": "2.0.0"},
    )
    defaults.update(overrides)
    return SeedValidationReportResponse(**defaults)


def test_report_all_required_fields():
    report = _make_report()
    assert report.run_group_id == "rg-20260227-001"
    assert report.created_at == "2026-02-27T12:00:00Z"
    assert report.n_seeds == 30
    assert report.gate_passed is True
    assert report.selected_seed == 42
    assert "rank_ic" in report.metric_distributions
    assert len(report.gate_checks) == 1
    assert len(report.seed_details) == 1
    assert report.environment_snapshot["python_version"] == "3.13.5"


def test_report_comparison_defaults_to_none():
    report = _make_report()
    assert report.comparison is None


def test_report_with_comparison():
    comp = ModelComparisonResponse(
        p_value=0.01,
        effect_size=0.4,
        significant=True,
        label="new_vs_incumbent",
        n_compared=30,
        mean_difference=0.07,
    )
    report = _make_report(comparison=comp)
    assert report.comparison is not None
    assert report.comparison.significant is True


def test_report_selected_seed_none_when_gate_failed():
    report = _make_report(gate_passed=False, selected_seed=None)
    assert report.gate_passed is False
    assert report.selected_seed is None


def test_report_multiple_metric_distributions():
    distributions = {
        "rank_ic": MetricDistributionResponse(
            mean=0.22,
            median=0.21,
            std=0.03,
            min=0.15,
            max=0.30,
            ci_lower=0.16,
            ci_upper=0.28,
            cv=0.14,
        ),
        "cluster_stability": MetricDistributionResponse(
            mean=0.85,
            median=0.86,
            std=0.02,
            min=0.80,
            max=0.90,
            ci_lower=0.81,
            ci_upper=0.89,
            cv=0.024,
        ),
    }
    report = _make_report(metric_distributions=distributions)
    assert len(report.metric_distributions) == 2
    assert "cluster_stability" in report.metric_distributions


def test_report_multiple_gate_checks():
    checks = [
        GateCheckResponse(name="rank_ic_median", value=0.21, threshold=0.15, passed=True),
        GateCheckResponse(name="rank_ic_cv", value=0.30, threshold=0.50, passed=True),
        GateCheckResponse(name="cluster_stability", value=0.85, threshold=0.70, passed=True),
    ]
    report = _make_report(gate_checks=checks)
    assert len(report.gate_checks) == 3


def test_report_multiple_seed_details():
    seeds = [
        SeedDetailResponse(
            seed=i, rank_ic=0.15 + i * 0.01, n_clusters=5, n_samples=150, selected=(i == 5)
        )
        for i in range(30)
    ]
    report = _make_report(seed_details=seeds, n_seeds=30)
    assert len(report.seed_details) == 30
    selected = [s for s in report.seed_details if s.selected]
    assert len(selected) == 1


def test_report_empty_environment_snapshot():
    report = _make_report(environment_snapshot={})
    assert report.environment_snapshot == {}


# ---------------------------------------------------------------------------
# SeedValidationHistoryResponse
# ---------------------------------------------------------------------------


def test_history_with_reports():
    reports = [_make_report(run_group_id=f"rg-{i}") for i in range(3)]
    history = SeedValidationHistoryResponse(reports=reports, total=3)
    assert len(history.reports) == 3
    assert history.total == 3


def test_history_empty_reports():
    history = SeedValidationHistoryResponse(reports=[], total=0)
    assert history.reports == []
    assert history.total == 0


def test_history_total_can_exceed_reports_length():
    """Total reflects DB count; reports may be paginated."""
    reports = [_make_report()]
    history = SeedValidationHistoryResponse(reports=reports, total=50)
    assert len(history.reports) == 1
    assert history.total == 50


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


def test_report_serialization_round_trip():
    report = _make_report()
    data = report.model_dump()
    restored = SeedValidationReportResponse(**data)
    assert restored.run_group_id == report.run_group_id
    assert restored.metric_distributions["rank_ic"].mean == 0.22
    assert restored.gate_checks[0].name == "rank_ic_median"
    assert restored.seed_details[0].seed == 42


def test_history_serialization_round_trip():
    history = SeedValidationHistoryResponse(
        reports=[_make_report()],
        total=1,
    )
    data = history.model_dump()
    restored = SeedValidationHistoryResponse(**data)
    assert len(restored.reports) == 1
    assert restored.total == 1
