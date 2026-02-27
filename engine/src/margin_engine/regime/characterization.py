"""Gate characterization module.

Given regime-tagged data for each gate (returns with gate enabled vs disabled,
elimination rates per regime), compute per-gate regime profiles including
Performance Degradation Ratio (PDR), Variance Inflation Factor (VIF), and
elimination rate ratios.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from margin_engine.regime.models import RegimeState

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

GateDataDict = dict[str, dict[str, dict[str, list]]]
"""Maps gate_name -> {"with": {...}, "without": {...}}."""

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_DEFAULT_RF_MONTHLY: float = 0.04 / 12


def _sharpe(returns: np.ndarray, rf_monthly: float = _DEFAULT_RF_MONTHLY) -> float:
    """Annualized Sharpe ratio from monthly returns.

    Returns 0.0 when fewer than 2 observations or zero standard deviation.
    """
    if len(returns) < 2:
        return 0.0
    excess = returns - rf_monthly
    std = float(np.std(excess, ddof=1))
    if std == 0.0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(12))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class GateRegimeStats(BaseModel):
    """Per-regime statistics for a single gate."""

    model_config = ConfigDict(frozen=True)

    regime_key: str
    n_months: int
    sharpe_with_gate: float
    sharpe_without_gate: float
    unconditional_sharpe_with_gate: float
    elimination_rate: float
    unconditional_elimination_rate: float
    variance_with_gate: float
    unconditional_variance: float

    @property
    def pdr(self) -> float:
        """Performance Degradation Ratio.

        ``sharpe_with_gate / unconditional_sharpe_with_gate - 1.0``

        Returns 0.0 when unconditional Sharpe is 0 (division guard).
        """
        if self.unconditional_sharpe_with_gate == 0.0:
            return 0.0
        return self.sharpe_with_gate / self.unconditional_sharpe_with_gate - 1.0

    @property
    def vif(self) -> float:
        """Variance Inflation Factor.

        ``variance_with_gate / unconditional_variance``

        Returns 1.0 when unconditional variance is 0 (division guard).
        """
        if self.unconditional_variance == 0.0:
            return 1.0
        return self.variance_with_gate / self.unconditional_variance

    @property
    def elimination_rate_ratio(self) -> float:
        """Elimination rate ratio.

        ``elimination_rate / unconditional_elimination_rate``

        Returns 1.0 when unconditional elimination rate is 0 (division guard).
        """
        if self.unconditional_elimination_rate == 0.0:
            return 1.0
        return self.elimination_rate / self.unconditional_elimination_rate


class GateRegimeProfile(BaseModel):
    """Regime profile for a single gate across all observed regimes."""

    gate_name: str
    regime_stats: list[GateRegimeStats] = Field(default_factory=list)
    most_degraded_regime: str | None = None
    max_pdr: float = 0.0
    max_vif: float = 0.0


class RegimeCharacterizationReport(BaseModel):
    """Collection of gate regime profiles."""

    profiles: dict[str, GateRegimeProfile] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def compute_gate_profiles(
    *,
    gate_data: GateDataDict,
) -> RegimeCharacterizationReport:
    """Compute per-gate regime profiles from gate data.

    Parameters
    ----------
    gate_data:
        Maps gate_name to::

            {
                "with": {
                    "regimes": list[RegimeState],
                    "returns": list[float],
                    "benchmark": list[float],
                    "elimination_rates": list[float],
                },
                "without": {
                    "returns": list[float],
                    "benchmark": list[float],
                },
            }

    Returns
    -------
    RegimeCharacterizationReport with one :class:`GateRegimeProfile` per gate.
    """
    if not gate_data:
        return RegimeCharacterizationReport()

    profiles: dict[str, GateRegimeProfile] = {}

    for gate_name, data in gate_data.items():
        with_data = data["with"]
        without_data = data["without"]

        regimes: list[RegimeState] = with_data["regimes"]
        returns_with = np.array(with_data["returns"], dtype=np.float64)
        returns_without = np.array(without_data["returns"], dtype=np.float64)
        elim_rates = np.array(with_data["elimination_rates"], dtype=np.float64)

        # Step 1: Unconditional metrics (full time series)
        unconditional_sharpe_with = _sharpe(returns_with)
        unconditional_sharpe_without = _sharpe(returns_without)
        unconditional_variance = float(np.var(returns_with, ddof=1)) if len(returns_with) >= 2 else 0.0
        unconditional_elim_rate = float(np.mean(elim_rates)) if len(elim_rates) > 0 else 0.0

        # Step 2: Bucket indices by regime_key
        buckets: dict[str, list[int]] = defaultdict(list)
        for i, regime in enumerate(regimes):
            buckets[regime.regime_key].append(i)

        # Step 3: Per-regime metrics
        regime_stats_list: list[GateRegimeStats] = []
        for regime_key, indices in buckets.items():
            idx = np.array(indices)
            rets_with = returns_with[idx]
            rets_without = returns_without[idx]
            elim = elim_rates[idx]

            n_months = len(indices)
            sharpe_with = _sharpe(rets_with)
            sharpe_without = _sharpe(rets_without)
            variance_with = float(np.var(rets_with, ddof=1)) if n_months >= 2 else 0.0
            elim_rate = float(np.mean(elim)) if n_months > 0 else 0.0

            stats = GateRegimeStats(
                regime_key=regime_key,
                n_months=n_months,
                sharpe_with_gate=sharpe_with,
                sharpe_without_gate=sharpe_without,
                unconditional_sharpe_with_gate=unconditional_sharpe_with,
                elimination_rate=elim_rate,
                unconditional_elimination_rate=unconditional_elim_rate,
                variance_with_gate=variance_with,
                unconditional_variance=unconditional_variance,
            )
            regime_stats_list.append(stats)

        # Step 5: Find most degraded regime (most negative PDR) and max VIF
        most_degraded_regime: str | None = None
        min_pdr = 0.0
        max_vif = 0.0

        for stats in regime_stats_list:
            pdr = stats.pdr
            vif = stats.vif
            if pdr < min_pdr:
                min_pdr = pdr
                most_degraded_regime = stats.regime_key
            if vif > max_vif:
                max_vif = vif

        profiles[gate_name] = GateRegimeProfile(
            gate_name=gate_name,
            regime_stats=regime_stats_list,
            most_degraded_regime=most_degraded_regime,
            max_pdr=min_pdr,
            max_vif=max_vif,
        )

    return RegimeCharacterizationReport(profiles=profiles)
