"""Ensemble Valuation — 4-method convergence test for reliable intrinsic value.

Methods:
1. DCF (passed in from existing dcf_mos.py)
2. Owner Earnings Capitalization (Owner Earnings / WACC)
3. Asset-Based Floor (Net Cash + Tangible Book * sector liquidation multiple)
4. EV/EBIT Peer Comparison (sector median EV/EBIT * company EBIT)

Convergence: >= 3 of 4 methods must agree within 30% of their median.
Ensemble IV = median of converging methods.
"""

from __future__ import annotations

import statistics

from pydantic import BaseModel

from margin_engine.models.financial import GICSSector

_ASSET_LIGHT_SECTORS = frozenset({
    GICSSector.TECHNOLOGY,
    GICSSector.COMMUNICATION_SERVICES,
    GICSSector.HEALTHCARE,
})


class EnsembleResult(BaseModel):
    """Result of ensemble valuation convergence test."""

    converged: bool
    converging_count: int
    ensemble_iv: float
    methods: dict[str, float]
    convergence_threshold: float = 0.30


def compute_ensemble_valuation(
    dcf_iv: float,
    owner_earnings_iv: float,
    asset_floor_iv: float,
    peer_comparison_iv: float,
    convergence_pct: float = 0.30,
    min_converging: int = 3,
    sector: GICSSector | None = None,
) -> EnsembleResult:
    """Compute ensemble intrinsic value from 4 independent methods.

    Args:
        dcf_iv: Intrinsic value from DCF model.
        owner_earnings_iv: Owner Earnings / WACC.
        asset_floor_iv: Net Cash + Tangible Book * liquidation multiple.
        peer_comparison_iv: Sector median EV/EBIT * company EBIT.
        convergence_pct: Max deviation from median to count as converging.
        min_converging: Minimum methods that must converge.

    Returns:
        EnsembleResult with convergence status and ensemble IV.
    """
    methods = {
        "dcf": dcf_iv,
        "owner_earnings": owner_earnings_iv,
        "asset_floor": asset_floor_iv,
        "peer_comparison": peer_comparison_iv,
    }

    # Filter out non-positive values
    valid = {k: v for k, v in methods.items() if v > 0}

    if len(valid) < min_converging:
        return EnsembleResult(
            converged=False,
            converging_count=len(valid),
            ensemble_iv=0.0,
            methods=methods,
        )

    # Iteratively find the largest converging cluster.
    # Start with all valid values, compute median, check convergence.
    # If not enough converge, remove the furthest outlier and retry.
    remaining = sorted(valid.values())
    best_converging: list[float] = []

    while len(remaining) >= 2:
        median_iv = statistics.median(remaining)

        if median_iv <= 0:
            break

        converging = [
            v for v in remaining if abs(v - median_iv) / median_iv <= convergence_pct
        ]

        if len(converging) >= len(best_converging):
            best_converging = converging

        if len(converging) >= min_converging:
            ensemble_iv = statistics.median(converging)
            return EnsembleResult(
                converged=True,
                converging_count=len(converging),
                ensemble_iv=ensemble_iv,
                methods=methods,
            )

        # Remove the value furthest from the median
        furthest = max(remaining, key=lambda v: abs(v - median_iv))
        remaining.remove(furthest)

    # Asset-light fallback: converge on DCF + peer_comparison only.
    # Asset-light businesses (Technology, Communication Services, Healthcare)
    # have near-zero asset floor valuations, making 3-of-4 convergence impossible.
    if sector in _ASSET_LIGHT_SECTORS:
        core_methods = {"dcf": dcf_iv, "peer_comparison": peer_comparison_iv}
        core_valid = {k: v for k, v in core_methods.items() if v > 0}
        if len(core_valid) == 2:
            vals = list(core_valid.values())
            median_iv = statistics.median(vals)
            if median_iv > 0:
                within = [
                    v for v in vals if abs(v - median_iv) / median_iv <= convergence_pct
                ]
                if len(within) >= 2:
                    return EnsembleResult(
                        converged=True,
                        converging_count=2,
                        ensemble_iv=median_iv,
                        methods=methods,
                    )

    converging_count = len(best_converging) if best_converging else 0
    return EnsembleResult(
        converged=False,
        converging_count=converging_count,
        ensemble_iv=0.0,
        methods=methods,
    )
