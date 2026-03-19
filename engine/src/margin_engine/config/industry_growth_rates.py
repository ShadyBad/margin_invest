"""Industry growth rates configuration.

Provides baseline expected annual growth rates per sub-industry.
Used by the TAM Expansion Velocity factor to compare company CAGR
against the industry benchmark.
"""

from __future__ import annotations

from pydantic import BaseModel

_DEFAULT_GROWTH_RATE = 0.05


class IndustryGrowthRate(BaseModel):
    """Annual growth rate and metadata for a single sub-industry."""

    rate: float
    last_updated: str


# ~50 sub-industry growth rates (annualized).
# All rates reflect forward-looking consensus estimates as of last_updated.
INDUSTRY_GROWTH_RATES: dict[str, IndustryGrowthRate] = {
    "cloud_computing": IndustryGrowthRate(rate=0.15, last_updated="2026-01-01"),
    "cybersecurity": IndustryGrowthRate(rate=0.12, last_updated="2026-01-01"),
    "electric_vehicles": IndustryGrowthRate(rate=0.25, last_updated="2026-01-01"),
    "traditional_auto": IndustryGrowthRate(rate=0.02, last_updated="2026-01-01"),
    "payments": IndustryGrowthRate(rate=0.10, last_updated="2026-01-01"),
    "enterprise_software": IndustryGrowthRate(rate=0.08, last_updated="2026-01-01"),
    "semiconductors": IndustryGrowthRate(rate=0.10, last_updated="2026-01-01"),
    "streaming_media": IndustryGrowthRate(rate=0.08, last_updated="2026-01-01"),
    "ecommerce": IndustryGrowthRate(rate=0.10, last_updated="2026-01-01"),
    "healthcare_it": IndustryGrowthRate(rate=0.09, last_updated="2026-01-01"),
    "biotech": IndustryGrowthRate(rate=0.07, last_updated="2026-01-01"),
    "renewable_energy": IndustryGrowthRate(rate=0.15, last_updated="2026-01-01"),
    "traditional_energy": IndustryGrowthRate(rate=0.01, last_updated="2026-01-01"),
    "fintech": IndustryGrowthRate(rate=0.12, last_updated="2026-01-01"),
    "insurance": IndustryGrowthRate(rate=0.04, last_updated="2026-01-01"),
    "consumer_staples": IndustryGrowthRate(rate=0.03, last_updated="2026-01-01"),
    "luxury_goods": IndustryGrowthRate(rate=0.05, last_updated="2026-01-01"),
    "aerospace_defense": IndustryGrowthRate(rate=0.04, last_updated="2026-01-01"),
    "logistics": IndustryGrowthRate(rate=0.05, last_updated="2026-01-01"),
    "telecom": IndustryGrowthRate(rate=0.02, last_updated="2026-01-01"),
    "data_analytics": IndustryGrowthRate(rate=0.12, last_updated="2026-01-01"),
    "ai_ml": IndustryGrowthRate(rate=0.20, last_updated="2026-01-01"),
    "robotics": IndustryGrowthRate(rate=0.15, last_updated="2026-01-01"),
    "digital_advertising": IndustryGrowthRate(rate=0.08, last_updated="2026-01-01"),
    "gaming": IndustryGrowthRate(rate=0.07, last_updated="2026-01-01"),
    "social_media": IndustryGrowthRate(rate=0.06, last_updated="2026-01-01"),
    "food_delivery": IndustryGrowthRate(rate=0.10, last_updated="2026-01-01"),
    "ride_sharing": IndustryGrowthRate(rate=0.08, last_updated="2026-01-01"),
    "space_technology": IndustryGrowthRate(rate=0.18, last_updated="2026-01-01"),
    "quantum_computing": IndustryGrowthRate(rate=0.30, last_updated="2026-01-01"),
    "edge_computing": IndustryGrowthRate(rate=0.20, last_updated="2026-01-01"),
    "blockchain": IndustryGrowthRate(rate=0.10, last_updated="2026-01-01"),
    "5g_infrastructure": IndustryGrowthRate(rate=0.12, last_updated="2026-01-01"),
    "ar_vr": IndustryGrowthRate(rate=0.15, last_updated="2026-01-01"),
    "smart_home": IndustryGrowthRate(rate=0.08, last_updated="2026-01-01"),
    "pet_care": IndustryGrowthRate(rate=0.06, last_updated="2026-01-01"),
    "plant_based_foods": IndustryGrowthRate(rate=0.08, last_updated="2026-01-01"),
    "mental_health_tech": IndustryGrowthRate(rate=0.15, last_updated="2026-01-01"),
    "telemedicine": IndustryGrowthRate(rate=0.12, last_updated="2026-01-01"),
    "online_education": IndustryGrowthRate(rate=0.10, last_updated="2026-01-01"),
    "freight_tech": IndustryGrowthRate(rate=0.08, last_updated="2026-01-01"),
    "construction_tech": IndustryGrowthRate(rate=0.07, last_updated="2026-01-01"),
    "proptech": IndustryGrowthRate(rate=0.06, last_updated="2026-01-01"),
    "regtech": IndustryGrowthRate(rate=0.10, last_updated="2026-01-01"),
    "insurtech": IndustryGrowthRate(rate=0.12, last_updated="2026-01-01"),
    "wealthtech": IndustryGrowthRate(rate=0.08, last_updated="2026-01-01"),
    "neobanking": IndustryGrowthRate(rate=0.15, last_updated="2026-01-01"),
    "digital_payments": IndustryGrowthRate(rate=0.12, last_updated="2026-01-01"),
    "supply_chain_tech": IndustryGrowthRate(rate=0.10, last_updated="2026-01-01"),
    "climate_tech": IndustryGrowthRate(rate=0.18, last_updated="2026-01-01"),
}


def get_industry_growth_rate(industry: str) -> float:
    """Return the annual growth rate for a given sub-industry.

    Args:
        industry: Sub-industry key (e.g. "cloud_computing").

    Returns:
        Annual growth rate as a decimal (e.g. 0.15 = 15%).
        Falls back to 0.05 for unknown industries.
    """
    entry = INDUSTRY_GROWTH_RATES.get(industry)
    if entry is None:
        return _DEFAULT_GROWTH_RATE
    return entry.rate
