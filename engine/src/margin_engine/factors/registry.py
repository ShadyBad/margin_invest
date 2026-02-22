"""Factor registry for ML feature extraction."""

from __future__ import annotations

from pydantic import BaseModel


class FactorMeta(BaseModel):
    """Metadata for a single factor."""

    name: str
    pillar: str  # "quality", "value", "momentum", "growth", "capital_allocation", "catalyst"
    higher_is_better: bool = True
    compute_fn: str = ""  # dotted path to compute function (informational only)
    tags: list[str] = []


class FactorRegistry:
    """Registry of all available factors."""

    def __init__(self) -> None:
        self._factors: dict[str, FactorMeta] = {}

    def register(self, meta: FactorMeta) -> None:
        """Register a factor in the registry."""
        self._factors[meta.name] = meta

    def get(self, name: str) -> FactorMeta | None:
        """Get factor metadata by name."""
        return self._factors.get(name)

    def list_by_pillar(self, pillar: str) -> list[FactorMeta]:
        """List all factors belonging to a pillar."""
        return [f for f in self._factors.values() if f.pillar == pillar]

    def all_factors(self) -> list[FactorMeta]:
        """Return all registered factors."""
        return list(self._factors.values())

    def to_feature_names(self) -> list[str]:
        """Return sorted list of all factor names (for feature matrix columns)."""
        return sorted(self._factors.keys())

    def __len__(self) -> int:
        return len(self._factors)


def default_registry() -> FactorRegistry:
    """Create a FactorRegistry pre-populated with all known factors.

    Factors are grouped by pillar with appropriate higher_is_better settings.
    """
    registry = FactorRegistry()

    # Quality factors
    quality_factors = [
        FactorMeta(name="gross_profitability", pillar="quality"),
        FactorMeta(name="roic_wacc", pillar="quality"),
        FactorMeta(name="roic_trend", pillar="quality"),
        FactorMeta(name="roic_stability", pillar="quality"),
        FactorMeta(name="f_score", pillar="quality"),
        FactorMeta(name="accrual_ratio", pillar="quality", higher_is_better=False),
        FactorMeta(name="fcf_conversion", pillar="quality"),
        FactorMeta(name="operating_leverage", pillar="quality"),
        FactorMeta(name="owner_earnings", pillar="quality"),
        FactorMeta(name="moat_durability", pillar="quality"),
        FactorMeta(name="capital_allocation", pillar="quality"),
        FactorMeta(name="competitive_dynamics", pillar="quality"),
        FactorMeta(name="reinvestment_engine", pillar="quality"),
    ]

    # Value factors
    value_factors = [
        FactorMeta(name="reverse_dcf", pillar="value"),
        FactorMeta(name="ensemble_valuation", pillar="value"),
        FactorMeta(name="ev_fcf", pillar="value"),
        FactorMeta(name="ev_gross_profit", pillar="value"),
        FactorMeta(name="peg_ratio", pillar="value"),
        FactorMeta(name="dcf_mos", pillar="value"),
        FactorMeta(name="asset_floor", pillar="value"),
        FactorMeta(name="acquirers_multiple", pillar="value", higher_is_better=False),
        FactorMeta(name="scenario_iv", pillar="value"),
        FactorMeta(name="wacc_sector", pillar="value", higher_is_better=False),
    ]

    # Momentum factors
    momentum_factors = [
        FactorMeta(name="price_momentum", pillar="momentum"),
        FactorMeta(name="multi_horizon_momentum", pillar="momentum"),
        FactorMeta(name="sue", pillar="momentum"),
        FactorMeta(name="earnings_revision", pillar="momentum"),
        FactorMeta(name="contrarian_signal", pillar="momentum"),
        FactorMeta(name="sentiment_score", pillar="momentum"),
        FactorMeta(name="insider_cluster", pillar="momentum"),
        FactorMeta(name="institutional_accumulation", pillar="momentum"),
        FactorMeta(name="shareholder_yield", pillar="momentum"),
    ]

    # Growth factors
    growth_factors = [
        FactorMeta(name="revenue_cagr", pillar="growth"),
        FactorMeta(name="incremental_roic", pillar="growth"),
        FactorMeta(name="rule_of_40", pillar="growth"),
        FactorMeta(name="runway_score", pillar="growth"),
    ]

    # Catalyst factors
    catalyst_factors = [
        FactorMeta(name="asymmetry", pillar="catalyst"),
        FactorMeta(name="price_targets", pillar="catalyst"),
    ]

    all_factors = (
        quality_factors + value_factors + momentum_factors + growth_factors + catalyst_factors
    )
    for factor in all_factors:
        registry.register(factor)

    return registry
