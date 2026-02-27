"""Post-hoc robustness validation for regime characterization results.

Three validation functions test whether gate characterization results are
stable, robust to individual crises, and whether regime decomposition is
complete:

- **Boundary sensitivity**: Do small perturbations in gate boundaries
  cause large rank changes?
- **Crisis leave-one-out**: Does removing a single crisis period
  disproportionately change a gate's Performance Degradation Ratio?
- **Regime completeness**: Does the regime decomposition explain most of
  the total variance?
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_ACCEPTABLE_RANK_CHANGE: int = 1
"""Maximum rank change that is still considered stable."""

_PDR_CHANGE_THRESHOLD: float = 0.50
"""Relative PDR change above which a crisis is deemed influential (50%)."""

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class BoundarySensitivityResult(BaseModel):
    """Result of boundary-perturbation sensitivity analysis."""

    is_stable: bool
    max_rank_change: int
    gates_with_rank_change: list[str] = Field(default_factory=list)


class CrisisLeaveOneOutResult(BaseModel):
    """Result of crisis leave-one-out robustness analysis."""

    is_robust: bool
    sensitive_to_crisis: list[str] = Field(default_factory=list)
    pdr_change_by_crisis: dict[str, dict[str, float]] = Field(default_factory=dict)


class RegimeCompletenessResult(BaseModel):
    """Result of regime completeness check."""

    residual_ratio: float = Field(description="Within-regime variance / total variance")
    is_complete: bool = Field(description="True if residual_ratio < 0.5")


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def check_boundary_sensitivity(
    *,
    baseline_rankings: dict[str, int],
    perturbed_rankings: list[dict[str, int]],
) -> BoundarySensitivityResult:
    """Check whether small boundary perturbations cause large rank changes.

    Parameters
    ----------
    baseline_rankings:
        Maps gate name to its rank under baseline boundaries.
    perturbed_rankings:
        List of gate-name-to-rank dicts, one per perturbation scenario.

    Returns
    -------
    BoundarySensitivityResult
        ``is_stable`` is True when the maximum rank change across all
        perturbations and gates does not exceed ``_MAX_ACCEPTABLE_RANK_CHANGE``.
    """
    max_rank_change = 0
    gates_with_large_change: set[str] = set()

    for perturbed in perturbed_rankings:
        for gate, baseline_rank in baseline_rankings.items():
            perturbed_rank = perturbed.get(gate, baseline_rank)
            change = abs(perturbed_rank - baseline_rank)
            if change > max_rank_change:
                max_rank_change = change
            if change > _MAX_ACCEPTABLE_RANK_CHANGE:
                gates_with_large_change.add(gate)

    return BoundarySensitivityResult(
        is_stable=max_rank_change <= _MAX_ACCEPTABLE_RANK_CHANGE,
        max_rank_change=max_rank_change,
        gates_with_rank_change=sorted(gates_with_large_change),
    )


def crisis_leave_one_out(
    *,
    full_pdr_rankings: dict[str, float],
    leave_out_pdr_rankings: dict[str, dict[str, float]],
) -> CrisisLeaveOneOutResult:
    """Check whether any single crisis disproportionately drives gate PDR.

    For each crisis, compute the relative change in PDR for every gate:
    ``|loo_pdr - full_pdr| / |full_pdr|``.  If any gate exceeds
    ``_PDR_CHANGE_THRESHOLD``, the crisis is marked as sensitive.

    Parameters
    ----------
    full_pdr_rankings:
        Maps gate name to its PDR computed from the full time series.
    leave_out_pdr_rankings:
        Maps crisis name to a dict of gate-name -> PDR when that crisis
        is excluded.

    Returns
    -------
    CrisisLeaveOneOutResult
        ``is_robust`` is True when no crisis is sensitive.
    """
    sensitive_crises: list[str] = []
    pdr_change_by_crisis: dict[str, dict[str, float]] = {}

    for crisis_name, loo_pdr in leave_out_pdr_rankings.items():
        crisis_changes: dict[str, float] = {}
        crisis_is_sensitive = False

        for gate, full_pdr in full_pdr_rankings.items():
            loo_value = loo_pdr.get(gate, full_pdr)
            abs_full = abs(full_pdr)

            if abs_full == 0.0:
                # When full PDR is zero, any non-zero LOO is infinite relative change
                relative_change = float("inf") if loo_value != 0.0 else 0.0
            else:
                relative_change = abs(loo_value - full_pdr) / abs_full

            crisis_changes[gate] = relative_change

            if relative_change > _PDR_CHANGE_THRESHOLD:
                crisis_is_sensitive = True

        pdr_change_by_crisis[crisis_name] = crisis_changes

        if crisis_is_sensitive:
            sensitive_crises.append(crisis_name)

    return CrisisLeaveOneOutResult(
        is_robust=len(sensitive_crises) == 0,
        sensitive_to_crisis=sorted(sensitive_crises),
        pdr_change_by_crisis=pdr_change_by_crisis,
    )


def check_regime_completeness(
    *,
    total_variance: float,
    within_regime_variance: float,
) -> RegimeCompletenessResult:
    """Check whether regime decomposition explains enough total variance.

    Parameters
    ----------
    total_variance:
        Variance of the full (unconditional) return series.
    within_regime_variance:
        Sum of within-regime variances (residual after regime decomposition).

    Returns
    -------
    RegimeCompletenessResult
        ``is_complete`` is True when ``residual_ratio < 0.5``.
    """
    if total_variance == 0.0:
        residual_ratio = 0.0
    else:
        residual_ratio = within_regime_variance / total_variance

    return RegimeCompletenessResult(
        residual_ratio=residual_ratio,
        is_complete=residual_ratio < 0.5,
    )
