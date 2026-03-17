"""Human-readable factor fingerprint.

Buckets pillar percentiles to nearest 5 and produces a compact string
like "Q90+V85+M80+G75" for display and historical matching.
"""

from __future__ import annotations

_PILLAR_ABBREV: dict[str, str] = {
    "quality": "Q",
    "value": "V",
    "momentum": "M",
    "growth": "G",
    "catalyst": "Cat",
    "capital_allocation": "CA",
}

_PILLAR_ORDER = ["quality", "value", "momentum", "growth", "catalyst", "capital_allocation"]


def _bucket(pctl: float) -> int:
    """Round percentile to nearest 5."""
    return int(round(pctl / 5) * 5)


def build_signature(pillars: dict[str, float]) -> str:
    """Build a compact signature string from pillar percentiles."""
    parts: list[str] = []
    for name in _PILLAR_ORDER:
        if name in pillars:
            abbrev = _PILLAR_ABBREV.get(name, name[0].upper())
            parts.append(f"{abbrev}{_bucket(pillars[name])}")
    return "+".join(parts)
