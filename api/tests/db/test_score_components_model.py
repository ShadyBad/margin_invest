"""Tests for ScoreComponent and ScoringRunManifest ORM models.

These models implement the persistence layer for component-level sub-score
logging. See docs/superpowers/specs/2026-05-02-component-subscore-logging-design.md.

The audit table itself (`score_components`) is paired with `scoring_run_manifest`,
which tracks every (run_id, asset_id, scoring_version) that orchestrate_ingest
dispatched. The reconciliation cron uses the manifest as its denominator.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from margin_api.db.models import (
    ScoreComponent,
    ScoringRunManifest,
    V3Score,
    V4Score,
)

# ---------------------------------------------------------------------------
# ScoreComponent
# ---------------------------------------------------------------------------


class TestScoreComponentModel:
    def test_factor_row(self) -> None:
        run_id = str(uuid4())
        sc = ScoreComponent(
            asset_id=42,
            ticker="AAPL",
            run_id=run_id,
            scoring_version="v3",
            component_type="factor",
            component_name="quality",
            value=87.4,
            metadata_json={"sector_neutral_rank": 92.1},
            computed_at=datetime.now(UTC),
        )
        assert sc.component_type == "factor"
        assert sc.component_name == "quality"
        assert sc.value == 87.4
        assert sc.passed is None
        assert sc.threshold is None
        assert sc.observed is None
        assert sc.metadata_json == {"sector_neutral_rank": 92.1}
        assert sc.run_id == run_id

    def test_filter_row(self) -> None:
        sc = ScoreComponent(
            asset_id=42,
            ticker="ENRN",
            run_id=str(uuid4()),
            scoring_version="v3",
            component_type="filter",
            component_name="beneish_m_score",
            passed=False,
            threshold=-1.78,
            observed=0.5,
            metadata_json={"filter_version": "v2"},
            computed_at=datetime.now(UTC),
        )
        assert sc.passed is False
        assert sc.threshold == -1.78
        assert sc.observed == 0.5
        assert sc.value is None

    def test_cascade_gate_row(self) -> None:
        sc = ScoreComponent(
            asset_id=42,
            ticker="V",
            run_id=str(uuid4()),
            scoring_version="v3",
            component_type="cascade_gate",
            component_name="gate_2_compounding_power",
            passed=True,
            threshold=0.15,
            observed=0.21,
            metadata_json={"gate_index": 2, "capital_light_bypass": False},
            computed_at=datetime.now(UTC),
        )
        assert sc.component_type == "cascade_gate"
        assert sc.passed is True

    def test_conviction_gate_with_override_metadata(self) -> None:
        sc = ScoreComponent(
            asset_id=42,
            ticker="MSFT",
            run_id=str(uuid4()),
            scoring_version="v3",
            component_type="conviction_gate",
            component_name="roic_trajectory_override",
            passed=True,
            metadata_json={
                "tier": "compounder",
                "override_fired": True,
                "quarters_window": 3,
                "slope_bps_per_quarter": 210,
            },
            computed_at=datetime.now(UTC),
        )
        assert sc.metadata_json["override_fired"] is True
        assert sc.metadata_json["quarters_window"] == 3

    def test_adjustment_row(self) -> None:
        sc = ScoreComponent(
            asset_id=42,
            ticker="XOM",
            run_id=str(uuid4()),
            scoring_version="v3",
            component_type="adjustment",
            component_name="sector_adapter_cyclical",
            value=-3.2,
            metadata_json={"target": "quality", "direction": "-"},
            computed_at=datetime.now(UTC),
        )
        assert sc.component_type == "adjustment"
        assert sc.value == -3.2

    def test_ml_contribution_row(self) -> None:
        sc = ScoreComponent(
            asset_id=42,
            ticker="NVDA",
            run_id=str(uuid4()),
            scoring_version="v4",
            component_type="ml_contribution",
            component_name="ml_alpha",
            value=0.034,
            metadata_json={"model_run_id": "run-abc-123"},
            computed_at=datetime.now(UTC),
        )
        assert sc.component_type == "ml_contribution"
        assert sc.scoring_version == "v4"

    def test_composite_output_row(self) -> None:
        sc = ScoreComponent(
            asset_id=42,
            ticker="AAPL",
            run_id=str(uuid4()),
            scoring_version="v3",
            component_type="composite_output",
            component_name="composite_score",
            value=72.5,
            metadata_json={"regime": "expansion", "style": "growth"},
            computed_at=datetime.now(UTC),
        )
        assert sc.component_type == "composite_output"
        assert sc.value == 72.5

    def test_metadata_json_accepts_explicit_empty_dict(self) -> None:
        """metadata_json column default fires at INSERT (not instantiation),
        so callers MUST pass an explicit dict if they want to reason about it
        pre-flush. Persistence layer does this; ad-hoc instantiation gets None.
        """
        sc = ScoreComponent(
            asset_id=42,
            ticker="AAPL",
            run_id=str(uuid4()),
            scoring_version="v3",
            component_type="factor",
            component_name="quality",
            value=87.4,
            metadata_json={},
            computed_at=datetime.now(UTC),
        )
        assert sc.metadata_json == {}


# ---------------------------------------------------------------------------
# ScoringRunManifest — tracks every (run_id, asset_id) dispatched
# ---------------------------------------------------------------------------


class TestScoringRunManifest:
    def test_orchestrate_ingest_manifest_row(self) -> None:
        """Default run_kind='orchestrate_ingest' applies at INSERT — orchestrate_ingest
        does not need to set it explicitly."""
        run_id = str(uuid4())
        manifest = ScoringRunManifest(
            run_id=run_id,
            asset_id=42,
            ticker="AAPL",
            scoring_version="v3",
            dispatched_at=datetime.now(UTC),
            run_kind="orchestrate_ingest",  # explicit for the test; default at INSERT in prod
        )
        assert manifest.run_id == run_id
        assert manifest.asset_id == 42
        assert manifest.scoring_version == "v3"
        assert manifest.run_kind == "orchestrate_ingest"

    def test_cli_rerun_excluded_from_reconciliation(self) -> None:
        manifest = ScoringRunManifest(
            run_id=str(uuid4()),
            asset_id=42,
            ticker="AAPL",
            scoring_version="v3",
            run_kind="cli_rerun",
        )
        assert manifest.run_kind == "cli_rerun"

    def test_manual_trigger_run_kind(self) -> None:
        manifest = ScoringRunManifest(
            run_id=str(uuid4()),
            asset_id=42,
            ticker="AAPL",
            scoring_version="v4",
            run_kind="manual",
        )
        assert manifest.run_kind == "manual"


# ---------------------------------------------------------------------------
# v3_scores / v4_scores get a new run_id column for audit join
# ---------------------------------------------------------------------------


class TestV3ScoreRunIdColumn:
    def test_v3_score_accepts_run_id(self) -> None:
        run_id = str(uuid4())
        v3 = V3Score(
            asset_id=42,
            run_id=run_id,
            scored_at=datetime.now(UTC),
            opportunity_type="compounder",
            conviction="strong",
            timing_signal="buy_now",
            max_position_pct=10.0,
            regime="expansion",
            composite_score=72.5,
        )
        assert v3.run_id == run_id

    def test_v3_score_run_id_nullable_for_pre_migration_rows(self) -> None:
        """Pre-migration rows have NULL run_id permanently. Audit window starts at deploy."""
        v3 = V3Score(
            asset_id=42,
            scored_at=datetime.now(UTC),
            opportunity_type="compounder",
            conviction="strong",
            timing_signal="buy_now",
            max_position_pct=10.0,
            regime="expansion",
            composite_score=72.5,
        )
        assert v3.run_id is None


class TestV4ScoreRunIdColumn:
    def test_v4_score_accepts_run_id(self) -> None:
        run_id = str(uuid4())
        v4 = V4Score(
            asset_id=42,
            run_id=run_id,
            scored_at=datetime.now(UTC),
            opportunity_type="compounder_growth",
            conviction="strong",
            rules_conviction="strong",
            style="growth",
            timing_signal="buy_now",
            max_position_pct=10.0,
            regime="expansion",
            composite_score=78.0,
        )
        assert v4.run_id == run_id

    def test_v4_score_run_id_nullable_for_pre_migration_rows(self) -> None:
        v4 = V4Score(
            asset_id=42,
            scored_at=datetime.now(UTC),
            opportunity_type="compounder_growth",
            conviction="strong",
            rules_conviction="strong",
            style="growth",
            timing_signal="buy_now",
            max_position_pct=10.0,
            regime="expansion",
            composite_score=78.0,
        )
        assert v4.run_id is None
