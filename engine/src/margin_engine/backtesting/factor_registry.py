"""Factor availability registry for historical backtesting.

Declares which scoring factors have reliable data at which dates.
The replay orchestrator uses this to determine which factors to include
when scoring at each historical rebalance point.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class FactorAvailability(BaseModel):
    """A single factor's data availability window."""

    name: str
    available_from: date
    category: str  # "quality", "value", "momentum", "growth", "ml"
    notes: str = ""


class FactorRegistry:
    """Registry of factor data availability dates.

    Provides lookup methods for determining which factors can be
    computed at any given historical date.
    """

    def __init__(self, entries: list[FactorAvailability]) -> None:
        self._entries = sorted(entries, key=lambda e: e.available_from)

    @classmethod
    def default(cls) -> FactorRegistry:
        """Build the default registry with known factor availability dates."""
        return cls(_DEFAULT_ENTRIES[:])

    def available_factors(self, as_of: date) -> list[FactorAvailability]:
        """Return factors with reliable data at the given date."""
        return [e for e in self._entries if e.available_from <= as_of]

    def missing_factors(self, as_of: date) -> list[FactorAvailability]:
        """Return factors NOT yet available at the given date."""
        return [e for e in self._entries if e.available_from > as_of]

    def coverage_ratio(self, as_of: date) -> float:
        """Fraction of total factors available at the given date (0.0 to 1.0)."""
        if not self._entries:
            return 0.0
        available = len(self.available_factors(as_of))
        return available / len(self._entries)

    def all_factors(self) -> list[FactorAvailability]:
        """Return all registered factors regardless of date."""
        return list(self._entries)


# Default entries based on data source availability research.
# Dates represent the earliest reliable data for each factor.
_DEFAULT_ENTRIES = [
    # Quality factors — available from SEC EDGAR XBRL (~2005-2008)
    FactorAvailability(
        name="gross_profitability", available_from=date(2005, 1, 1), category="quality"
    ),
    FactorAvailability(name="f_score", available_from=date(2005, 1, 1), category="quality"),
    FactorAvailability(
        name="accrual_ratio", available_from=date(2005, 1, 1), category="quality"
    ),
    FactorAvailability(name="roic_wacc", available_from=date(2006, 1, 1), category="quality"),
    FactorAvailability(name="roic_trend", available_from=date(2006, 1, 1), category="quality"),
    FactorAvailability(
        name="roic_stability",
        available_from=date(2008, 1, 1),
        category="quality",
        notes="Needs 3yr history",
    ),
    FactorAvailability(
        name="fcf_conversion", available_from=date(2005, 1, 1), category="quality"
    ),
    FactorAvailability(
        name="capital_allocation", available_from=date(2006, 1, 1), category="quality"
    ),
    # Value factors
    FactorAvailability(name="ev_fcf", available_from=date(2005, 1, 1), category="value"),
    FactorAvailability(
        name="ev_gross_profit", available_from=date(2005, 1, 1), category="value"
    ),
    FactorAvailability(
        name="acquirers_multiple", available_from=date(2005, 1, 1), category="value"
    ),
    FactorAvailability(name="reverse_dcf", available_from=date(2006, 1, 1), category="value"),
    FactorAvailability(name="owner_earnings", available_from=date(2006, 1, 1), category="value"),
    FactorAvailability(name="peg_ratio", available_from=date(2006, 1, 1), category="value"),
    # Momentum factors
    FactorAvailability(
        name="price_momentum", available_from=date(2005, 1, 1), category="momentum"
    ),
    FactorAvailability(
        name="multi_horizon_momentum", available_from=date(2005, 1, 1), category="momentum"
    ),
    FactorAvailability(
        name="earnings_revision",
        available_from=date(2010, 1, 1),
        category="momentum",
        notes="Analyst estimates data spotty before 2010",
    ),
    FactorAvailability(name="sue", available_from=date(2008, 1, 1), category="momentum"),
    # Growth factors
    FactorAvailability(
        name="revenue_cagr",
        available_from=date(2008, 1, 1),
        category="growth",
        notes="Needs 3yr history",
    ),
    FactorAvailability(
        name="operating_leverage", available_from=date(2008, 1, 1), category="growth"
    ),
    FactorAvailability(name="rule_of_40", available_from=date(2008, 1, 1), category="growth"),
    # Specialized factors
    FactorAvailability(
        name="insider_activity",
        available_from=date(2010, 1, 1),
        category="quality",
        notes="SEC Form 4 data spotty before 2010",
    ),
    FactorAvailability(
        name="institutional_accumulation",
        available_from=date(2010, 1, 1),
        category="quality",
        notes="13F data",
    ),
    FactorAvailability(
        name="moat_durability",
        available_from=date(2010, 1, 1),
        category="quality",
        notes="Needs 5yr history",
    ),
    # ML factors — only available from when the ML pipeline started
    FactorAvailability(
        name="ml_cluster_score",
        available_from=date(2026, 1, 1),
        category="ml",
        notes="Requires trained cluster model",
    ),
    FactorAvailability(
        name="ml_vae_anomaly",
        available_from=date(2026, 1, 1),
        category="ml",
        notes="Requires trained VAE model",
    ),
]
