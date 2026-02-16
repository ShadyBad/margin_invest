"""Universe configuration loading and validation."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ExclusionRules:
    sectors: list[str] = field(default_factory=list)
    min_market_cap: int = 0
    min_avg_volume: int = 0


@dataclass(frozen=True)
class UniverseConfig:
    version: str
    tickers: list[str]
    ticker_count: int
    config_hash: str
    description: str = ""
    source: str = ""
    generated_at: str = ""
    exclusions: ExclusionRules = field(default_factory=ExclusionRules)


def load_universe_config(path: Path) -> UniverseConfig:
    """Load and validate a universe YAML config file."""
    raw = path.read_text()
    data = yaml.safe_load(raw)

    if not data or "version" not in data:
        raise ValueError("Universe config must include 'version' field")

    tickers_raw = data.get("tickers", [])
    if not tickers_raw:
        raise ValueError("Universe config must include non-empty 'tickers' list")

    # Deduplicate, preserve order, uppercase
    seen: set[str] = set()
    tickers: list[str] = []
    for t in tickers_raw:
        upper = str(t).upper().strip()
        if upper not in seen:
            seen.add(upper)
            tickers.append(upper)

    config_hash = hashlib.sha256(raw.encode()).hexdigest()

    exclusions_data = data.get("exclusions", {})
    exclusions = ExclusionRules(
        sectors=exclusions_data.get("sectors", []),
        min_market_cap=exclusions_data.get("min_market_cap", 0),
        min_avg_volume=exclusions_data.get("min_avg_volume", 0),
    )

    return UniverseConfig(
        version=str(data["version"]),
        tickers=tickers,
        ticker_count=len(tickers),
        config_hash=config_hash,
        description=data.get("description", ""),
        source=data.get("source", ""),
        generated_at=data.get("generated_at", ""),
        exclusions=exclusions,
    )
