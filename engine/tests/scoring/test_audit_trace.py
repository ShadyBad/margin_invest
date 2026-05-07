"""Tests for the score audit trace extraction layer.

The audit trace is the engine-side primitive that collects component-level
sub-scores as v3/v4 pipelines execute. The persistence layer in api/ flushes
the trace to score_components.

Engine purity is load-bearing: this module must not import anything from
api/, sqlalchemy, or any web framework. AC #7 in the design spec verifies
this via an ast.parse test (test_engine_purity).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import get_args
from uuid import UUID, uuid4

import pytest
from margin_engine.scoring.audit_trace import (
    NULL_TRACE,
    AuditTraceProtocol,
    ComponentEntry,
    ComponentType,
    GateKind,
    ScoreAuditTrace,
    _NullTrace,
)

# ---------------------------------------------------------------------------
# ComponentType / GateKind literals (locked enum)
# ---------------------------------------------------------------------------


def test_component_type_locked_to_seven_values() -> None:
    """ComponentType is a one-way door — adding a value invalidates audit queries."""
    assert set(get_args(ComponentType)) == {
        "factor",
        "cascade_gate",
        "conviction_gate",
        "filter",
        "adjustment",
        "ml_contribution",
        "composite_output",
    }


def test_gate_kind_locked_to_three_values() -> None:
    """GateKind drives record_gate dispatch into one of 3 cascade-shaped types."""
    assert set(get_args(GateKind)) == {"cascade", "conviction", "filter"}


# ---------------------------------------------------------------------------
# ComponentEntry dataclass
# ---------------------------------------------------------------------------


def test_component_entry_defaults() -> None:
    entry = ComponentEntry(component_type="factor", component_name="quality")
    assert entry.value is None
    assert entry.passed is None
    assert entry.threshold is None
    assert entry.observed is None
    assert entry.metadata == {}


def test_component_entry_factor_shape() -> None:
    entry = ComponentEntry(
        component_type="factor",
        component_name="quality",
        value=87.4,
        metadata={"sector_neutral_rank": 92.1},
    )
    assert entry.value == 87.4
    assert entry.passed is None
    assert entry.metadata == {"sector_neutral_rank": 92.1}


def test_component_entry_gate_shape() -> None:
    entry = ComponentEntry(
        component_type="cascade_gate",
        component_name="gate_2_compounding_power",
        passed=True,
        threshold=0.15,
        observed=0.21,
        metadata={"gate_index": 2, "capital_light_bypass": False},
    )
    assert entry.passed is True
    assert entry.threshold == 0.15
    assert entry.observed == 0.21
    assert entry.value is None


# ---------------------------------------------------------------------------
# ScoreAuditTrace recorders
# ---------------------------------------------------------------------------


@pytest.fixture
def trace() -> ScoreAuditTrace:
    return ScoreAuditTrace(
        run_id=uuid4(),
        asset_id=42,
        ticker="AAPL",
        scoring_version="v3",
    )


def test_score_audit_trace_constructs_empty(trace: ScoreAuditTrace) -> None:
    assert trace.entries == []
    assert isinstance(trace.run_id, UUID)
    assert trace.asset_id == 42
    assert trace.ticker == "AAPL"
    assert trace.scoring_version == "v3"


def test_record_factor_appends_entry(trace: ScoreAuditTrace) -> None:
    trace.record_factor("quality", 87.4, sector_neutral_rank=92.1)

    assert len(trace.entries) == 1
    e = trace.entries[0]
    assert e.component_type == "factor"
    assert e.component_name == "quality"
    assert e.value == 87.4
    assert e.passed is None
    assert e.metadata == {"sector_neutral_rank": 92.1}


def test_record_gate_dispatches_kind_to_component_type(trace: ScoreAuditTrace) -> None:
    trace.record_gate("filter", "beneish_m_score", passed=True, threshold=-1.78, observed=-2.31)
    trace.record_gate(
        "cascade", "gate_2_compounding_power", passed=True, threshold=0.15, observed=0.21
    )
    trace.record_gate("conviction", "roic_trajectory_override", passed=True)

    types = [e.component_type for e in trace.entries]
    assert types == ["filter", "cascade_gate", "conviction_gate"]


def test_record_gate_preserves_threshold_observed(trace: ScoreAuditTrace) -> None:
    trace.record_gate("filter", "beneish_m_score", passed=False, threshold=-1.78, observed=0.5)
    e = trace.entries[0]
    assert e.passed is False
    assert e.threshold == -1.78
    assert e.observed == 0.5
    assert e.value is None


def test_record_gate_metadata_passes_through(trace: ScoreAuditTrace) -> None:
    trace.record_gate(
        "conviction",
        "roic_trajectory_override",
        passed=True,
        override_fired=True,
        quarters_window=3,
        slope_bps_per_quarter=210,
    )
    e = trace.entries[0]
    assert e.metadata == {
        "override_fired": True,
        "quarters_window": 3,
        "slope_bps_per_quarter": 210,
    }


def test_record_adjustment(trace: ScoreAuditTrace) -> None:
    trace.record_adjustment("sector_adapter_cyclical", -3.2, target="quality", direction="-")
    e = trace.entries[0]
    assert e.component_type == "adjustment"
    assert e.component_name == "sector_adapter_cyclical"
    assert e.value == -3.2
    assert e.metadata == {"target": "quality", "direction": "-"}


def test_record_ml(trace: ScoreAuditTrace) -> None:
    trace.record_ml("ml_alpha", 0.034, model_run_id="run-abc-123")
    e = trace.entries[0]
    assert e.component_type == "ml_contribution"
    assert e.component_name == "ml_alpha"
    assert e.value == 0.034
    assert e.metadata == {"model_run_id": "run-abc-123"}


def test_record_composite(trace: ScoreAuditTrace) -> None:
    trace.record_composite("composite_score", 72.5, regime="expansion", style="growth")
    e = trace.entries[0]
    assert e.component_type == "composite_output"
    assert e.component_name == "composite_score"
    assert e.value == 72.5
    assert e.metadata == {"regime": "expansion", "style": "growth"}


def test_recorders_preserve_call_order(trace: ScoreAuditTrace) -> None:
    trace.record_factor("quality", 87.4)
    trace.record_gate("filter", "beneish_m_score", passed=True)
    trace.record_gate("cascade", "gate_2", passed=True)
    trace.record_composite("composite_score", 72.5)

    names = [e.component_name for e in trace.entries]
    assert names == ["quality", "beneish_m_score", "gate_2", "composite_score"]


# ---------------------------------------------------------------------------
# _NullTrace — no-op singleton (Null Object pattern)
# ---------------------------------------------------------------------------


def test_null_trace_records_factor_no_op() -> None:
    null = _NullTrace()
    null.record_factor("quality", 87.4)
    # No state, no list to inspect — call must not raise.


def test_null_trace_records_all_methods_no_op() -> None:
    null = _NullTrace()
    null.record_factor("quality", 87.4)
    null.record_gate("filter", "beneish_m_score", passed=True, threshold=-1.78, observed=-2.31)
    null.record_gate("cascade", "gate_2", passed=True)
    null.record_gate("conviction", "roic_override", passed=True)
    null.record_adjustment("sector_adapter", -3.2)
    null.record_ml("ml_alpha", 0.034)
    null.record_composite("composite_score", 72.5)
    # All must not raise.


def test_null_trace_does_not_carry_run_id_or_asset_id() -> None:
    """Per qa Q9 — _NullTrace MUST NOT be forced to fake run_id/asset_id."""
    null = _NullTrace()
    assert not hasattr(null, "run_id")
    assert not hasattr(null, "asset_id")
    assert not hasattr(null, "ticker")
    assert not hasattr(null, "entries")


def test_null_trace_singleton_constant() -> None:
    """NULL_TRACE module constant exists and is a _NullTrace instance."""
    assert isinstance(NULL_TRACE, _NullTrace)


# ---------------------------------------------------------------------------
# AuditTraceProtocol — structural typing
# ---------------------------------------------------------------------------


def test_score_audit_trace_satisfies_protocol(trace: ScoreAuditTrace) -> None:
    assert isinstance(trace, AuditTraceProtocol)


def test_null_trace_satisfies_protocol() -> None:
    assert isinstance(_NullTrace(), AuditTraceProtocol)


def test_null_trace_constant_satisfies_protocol() -> None:
    assert isinstance(NULL_TRACE, AuditTraceProtocol)


# ---------------------------------------------------------------------------
# Engine purity — AC #7
# ---------------------------------------------------------------------------


def test_audit_trace_module_has_no_forbidden_imports() -> None:
    """audit_trace.py MUST NOT import sqlalchemy, api/, or web frameworks.

    Engine purity is the contract: this module must remain testable in
    isolation, with zero database / web / app dependencies. Any drift here
    breaks the design and likely cannot be reverted without a refactor.
    """
    module_path = (
        Path(__file__).resolve().parents[2] / "src" / "margin_engine" / "scoring" / "audit_trace.py"
    )
    assert module_path.exists(), f"audit_trace.py not found at {module_path}"

    tree = ast.parse(module_path.read_text())

    forbidden_prefixes = (
        "sqlalchemy",
        "asyncpg",
        "fastapi",
        "starlette",
        "pydantic",  # engine uses pydantic elsewhere but audit_trace stays pure stdlib
        "margin_api",
        "anthropic",
        "voyageai",
        "redis",
        "arq",
    )

    bad_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name.startswith(p) for p in forbidden_prefixes):
                    bad_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if any(module.startswith(p) for p in forbidden_prefixes):
                bad_imports.append(module)

    assert not bad_imports, (
        f"audit_trace.py imports forbidden modules: {bad_imports}. "
        f"Engine purity contract violated (design spec AC #7)."
    )
