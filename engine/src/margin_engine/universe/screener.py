"""Universe screener — discover US equities via yfinance."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

_PAGE_SIZE = 250

# Major US exchanges — excludes OTC/Pink Sheets where foreign stocks trade
# NMS = NASDAQ Global Select, NGM = NASDAQ Global Market, NCM = NASDAQ Capital Market
# NYQ = NYSE, ASE = NYSE American (formerly AMEX), PCX = NYSE Arca
US_EXCHANGES = ["NMS", "NGM", "NCM", "NYQ", "ASE", "PCX"]

# Yahoo Finance sector names (yfinance uses these, not GICS)
ALL_SECTORS = [
    "Technology",
    "Healthcare",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Energy",
    "Industrials",
    "Basic Materials",
    "Utilities",
    "Communication Services",
    "Financial Services",
    "Real Estate",
]


def screen_us_equities(
    *,
    min_market_cap: int = 0,
    min_avg_volume: int = 0,
    excluded_sectors: list[str] | None = None,
    exchanges: list[str] | None = None,
) -> list[dict]:
    """Screen Yahoo Finance for US equities listed on major exchanges.

    Queries each included sector separately (Yahoo screener has no NOT operator).
    Returns a list of dicts with keys: ticker, name, market_cap, avg_volume, sector.

    Args:
        exchanges: Exchange codes to include (default: US_EXCHANGES).
            Uses ``is-in`` filter to restrict to major US exchanges,
            excluding OTC/Pink Sheets where foreign stocks trade.
    """
    import yfinance as yf
    from yfinance import EquityQuery

    excluded = set(excluded_sectors or [])
    included_sectors = [s for s in ALL_SECTORS if s not in excluded]
    exchange_list = exchanges or US_EXCHANGES

    results: list[dict] = []

    for sector in included_sectors:
        conditions = [
            EquityQuery("eq", ["region", "us"]),
            EquityQuery("is-in", ["exchange", *exchange_list]),
            EquityQuery("eq", ["sector", sector]),
        ]
        if min_market_cap > 0:
            conditions.append(EquityQuery("gt", ["intradaymarketcap", min_market_cap]))
        else:
            # Yahoo requires at least some filter — use $1 as floor
            conditions.append(EquityQuery("gt", ["intradaymarketcap", 1]))
        if min_avg_volume > 0:
            conditions.append(EquityQuery("gt", ["avgdailyvol3m", min_avg_volume]))
        query = EquityQuery("and", conditions)

        # First page to get total
        response = yf.screen(
            query, sortField="intradaymarketcap", sortAsc=False,
            size=_PAGE_SIZE, offset=0,
        )
        sector_total = response.get("total", 0)
        logger.info("  %s: %d tickers", sector, sector_total)

        offset = 0
        while offset < sector_total:
            if offset > 0:
                response = yf.screen(
                    query, sortField="intradaymarketcap", sortAsc=False,
                    size=_PAGE_SIZE, offset=offset,
                )

            quotes = response.get("quotes", [])
            if not quotes:
                break

            for q in quotes:
                symbol = q.get("symbol", "")
                # Skip non-standard tickers (warrants, units, etc.)
                if not symbol or "." in symbol or "-" in symbol or len(symbol) > 5:
                    continue

                results.append({
                    "ticker": symbol,
                    "name": q.get("shortName") or q.get("longName") or symbol,
                    "market_cap": q.get("marketCap", 0),
                    "avg_volume": q.get("averageDailyVolume3Month", 0),
                    "sector": sector,
                })

            offset += _PAGE_SIZE

    logger.info("Total: %d tickers across %d sectors", len(results), len(included_sectors))
    return results


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
    exchanges: list[str] | None = None,
    description: str = "US equities, excluding financials and REITs",
) -> str:
    """Generate a universe.yaml string from filtered tickers."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(UTC).strftime("%Y.%m.%d")
    exchange_list = exchanges or US_EXCHANGES

    lines = [
        f'version: "{today}"',
        f'description: "{description}"',
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
    lines.append("  exchanges:")
    for ex in exchange_list:
        lines.append(f'    - "{ex}"')
    lines.append("")
    lines.append("tickers:")
    for ticker in sorted(tickers):
        lines.append(f"  - {ticker}")
    lines.append("")
    return "\n".join(lines)
