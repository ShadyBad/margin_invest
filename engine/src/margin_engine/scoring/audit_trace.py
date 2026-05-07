"""Score audit trace — engine-side primitive for component-level sub-score logging.

Pure dataclass module. ZERO web / DB / framework imports. The api/ layer is
responsible for persistence (api/services/score_audit.py).

Design spec: docs/superpowers/specs/2026-05-02-component-subscore-logging-design.md

Engine purity is load-bearing — verified by test_audit_trace_module_has_no_forbidden_imports
in engine/tests/scoring/test_audit_trace.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

ComponentType = Literal[
    "factor",
    "cascade_gate",
    "conviction_gate",
    "filter",
    "adjustment",
    "ml_contribution",
    "composite_output",
]
"""The 7-value enum for component_type. This is a one-way door — adding a value
is fine; renaming or removing one breaks every saved audit query."""

GateKind = Literal["cascade", "conviction", "filter"]
"""Drives record_gate's dispatch into the corresponding component_type."""

ScoringVersion = Literal["v3", "v4", "v3_track_c"]
"""Tracks which scoring pipeline produced this trace."""

_GATE_KIND_TO_TYPE: dict[GateKind, ComponentType] = {
    "cascade": "cascade_gate",
    "conviction": "conviction_gate",
    "filter": "filter",
}


@dataclass
class ComponentEntry:
    """One row destined for the score_components table.

    `value` carries scalar measures (factor percentile, ML weight, composite output).
    `passed`/`threshold`/`observed` carry gate or filter outcomes.
    `metadata` carries free-form structured detail per component_type contract
    (see Metadata schema discipline section in the design spec).
    """

    component_type: ComponentType
    component_name: str
    value: float | None = None
    passed: bool | None = None
    threshold: float | None = None
    observed: float | None = None
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class AuditTraceProtocol(Protocol):
    """Structural type for any object that can record audit components.

    Both `ScoreAuditTrace` and `_NullTrace` satisfy this Protocol. Orchestrators
    annotate `trace: AuditTraceProtocol = NULL_TRACE` so call sites are
    unconditional and the null path requires no `if trace is not None` checks.

    `runtime_checkable` allows isinstance() checks at the persistence boundary.
    Note: `runtime_checkable` only validates method names, not signatures —
    full type safety relies on mypy strict + Literal-typed parameters.
    """

    def record_factor(self, name: str, percentile: float, **metadata: object) -> None: ...

    def record_gate(
        self,
        kind: GateKind,
        name: str,
        passed: bool,
        threshold: float | None = None,
        observed: float | None = None,
        **metadata: object,
    ) -> None: ...

    def record_adjustment(self, name: str, value: float, **metadata: object) -> None: ...

    def record_ml(self, name: str, value: float, **metadata: object) -> None: ...

    def record_composite(self, name: str, value: float, **metadata: object) -> None: ...


@dataclass
class ScoreAuditTrace:
    """Real audit trace. Populated as v3/v4 pipelines execute.

    The api/ layer flushes `entries` to score_components in a fail-closed-warn
    pattern (see api/services/score_audit.py). The trace itself is pure data —
    it does not know how to persist itself.
    """

    run_id: UUID
    asset_id: int
    ticker: str
    scoring_version: ScoringVersion
    entries: list[ComponentEntry] = field(default_factory=list)

    def record_factor(self, name: str, percentile: float, **metadata: object) -> None:
        """Record a 5-factor sub-score (Quality, Value, Growth, Momentum, Anti-consensus)."""
        self.entries.append(
            ComponentEntry(
                component_type="factor",
                component_name=name,
                value=percentile,
                metadata=dict(metadata),
            )
        )

    def record_gate(
        self,
        kind: GateKind,
        name: str,
        passed: bool,
        threshold: float | None = None,
        observed: float | None = None,
        **metadata: object,
    ) -> None:
        """Record a cascade gate, conviction gate, or filter verdict.

        `kind` dispatches to the corresponding component_type. Collapsing these
        three into one verb avoids the dev-error trap of two recorders with
        identical signatures (initial spec design had separate verbs).
        """
        self.entries.append(
            ComponentEntry(
                component_type=_GATE_KIND_TO_TYPE[kind],
                component_name=name,
                passed=passed,
                threshold=threshold,
                observed=observed,
                metadata=dict(metadata),
            )
        )

    def record_adjustment(self, name: str, value: float, **metadata: object) -> None:
        """Record a v3/v4 adjustment (sector adapter delta, growth-stage class,
        dual-track fusion weight, market regime).
        """
        self.entries.append(
            ComponentEntry(
                component_type="adjustment",
                component_name=name,
                value=value,
                metadata=dict(metadata),
            )
        )

    def record_ml(self, name: str, value: float, **metadata: object) -> None:
        """Record a v4 ML contribution (rules_weight, ml_weight, ml_alpha, ml_confidence)."""
        self.entries.append(
            ComponentEntry(
                component_type="ml_contribution",
                component_name=name,
                value=value,
                metadata=dict(metadata),
            )
        )

    def record_composite(self, name: str, value: float, **metadata: object) -> None:
        """Record the final composite output (composite_score, composite_tier as scalar, signal)."""
        self.entries.append(
            ComponentEntry(
                component_type="composite_output",
                component_name=name,
                value=value,
                metadata=dict(metadata),
            )
        )


class _NullTrace:
    """Null Object — silently no-ops every recorder.

    Default for orchestrators called from contexts that do not need audit
    persistence (tests, ad-hoc scoring). Implements `AuditTraceProtocol`
    structurally; intentionally does NOT subclass `ScoreAuditTrace` so it
    carries no fake `run_id` / `asset_id` / `ticker` / `entries` fields.

    Per qa Q9 in the design spec: forcing the null object to fake a UUID
    and an asset_id violates the dataclass type contract.
    """

    __slots__ = ()

    def record_factor(self, *args: object, **kwargs: object) -> None:
        return None

    def record_gate(self, *args: object, **kwargs: object) -> None:
        return None

    def record_adjustment(self, *args: object, **kwargs: object) -> None:
        return None

    def record_ml(self, *args: object, **kwargs: object) -> None:
        return None

    def record_composite(self, *args: object, **kwargs: object) -> None:
        return None


NULL_TRACE: AuditTraceProtocol = _NullTrace()
"""Module-level singleton for orchestrators to use as the default `trace` argument.

Usage (in v3_orchestrator.score / v4_orchestrator.score):
    def score(..., trace: AuditTraceProtocol = NULL_TRACE) -> CompositeScore: ...
"""
