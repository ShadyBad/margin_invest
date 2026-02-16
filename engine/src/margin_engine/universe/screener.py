"""Universe screener — discover US equities via yfinance."""
from __future__ import annotations

from datetime import UTC, datetime


def filter_universe(
    tickers: list[dict],
    *,
    excluded_sectors: list[str] | None = None,
    min_market_cap: int = 0,
    min_avg_volume: int = 0,
) -> list[str]:
    """Filter raw ticker data by sector, market cap, and volume thresholds."""
    excluded = set(excluded_sectors or [])
    result: list[str] = []
    for t in tickers:
        if t.get("sector", "") in excluded:
            continue
        if t.get("market_cap", 0) < min_market_cap:
            continue
        if t.get("avg_volume_dollar", 0) < min_avg_volume:
            continue
        result.append(t["ticker"])
    return sorted(result)


def generate_universe_yaml(
    *,
    tickers: list[str],
    excluded_sectors: list[str],
    min_market_cap: int,
    min_avg_volume: int,
) -> str:
    """Generate a universe.yaml string from filtered tickers."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(UTC).strftime("%Y.%m.%d")

    lines = [
        f'version: "{today}"',
        'description: "US equities, excluding financials and REITs"',
        'source: "yfinance_screener"',
        f'generated_at: "{now}"',
        "",
        "exclusions:",
        "  sectors:",
    ]
    for sector in excluded_sectors:
        lines.append(f'    - "{sector}"')
    lines.append(f"  min_market_cap: {min_market_cap}")
    lines.append(f"  min_avg_volume: {min_avg_volume}")
    lines.append("")
    lines.append("tickers:")
    for ticker in sorted(tickers):
        lines.append(f"  - {ticker}")
    lines.append("")
    return "\n".join(lines)
