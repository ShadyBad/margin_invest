# SEC EDGAR Provider Design

**Date:** 2026-02-22
**Status:** Approved

## Overview

Integrate SEC EDGAR as a data provider for three categories:
- **Fundamentals (XBRL)** — fallback after yfinance and FMP (priority 2)
- **Insider (Form 4)** — primary, above Finnhub (priority 10)
- **Institutional (13F)** — primary, above Finnhub (priority 10)

SEC EDGAR is a free government API. No API key required — only a User-Agent header with company name and contact email.

## Architecture

### Per-Category Priority (Registry Enhancement)

The existing `ProviderInfo` has a single `priority` field. SEC EDGAR needs different priorities per category. Solution: add an optional `category_priorities: dict[DataCategory, int] | None` field to `ProviderInfo`.

The registry's `get_fallback_chain` uses `category_priorities.get(category)` when present, falling back to the base `priority`. Fully backward-compatible — existing providers unchanged.

### EDGARProvider

Single provider class with per-category priorities:

```python
ProviderInfo(
    name="edgar",
    supported_categories=[FUNDAMENTALS, INSIDER, INSTITUTIONAL],
    requests_per_minute=600,  # 10 req/sec
    requires_api_key=False,
    priority=10,  # default for insider/institutional
    category_priorities={
        DataCategory.FUNDAMENTALS: 2,
        DataCategory.INSIDER: 10,
        DataCategory.INSTITUTIONAL: 10,
    },
)
```

### Resulting Fallback Chains

```
Fundamentals:  yfinance (10) -> FMP (5) -> EDGAR XBRL (2)
Price:         Polygon (20) -> yfinance (10)
Insider:       EDGAR Form 4 (10) -> Finnhub (5)
Institutional: EDGAR 13F (10) -> Finnhub (5)
Macro:         FRED (no fallback)
News:          Finnhub (5) -> FMP (5)
Earnings:      Finnhub (5)
```

## CIK Mapping

SEC EDGAR uses CIK numbers, not tickers. The provider lazy-loads the SEC's `company_tickers.json` on first fetch and caches the ticker-to-CIK mapping in memory. CIK numbers are zero-padded to 10 digits for API URLs.

Source: `https://www.sec.gov/files/company_tickers.json`

## Fetch Methods

### fetch_fundamentals — XBRL Company Facts

- **Endpoint:** `https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json`
- **Approach:** Single API call returns all XBRL facts. Extract latest 10-K annual values.
- **XBRL tag mapping:**
  - Income: `Revenue`/`Revenues`, `CostOfRevenue`, `GrossProfit`, `OperatingIncomeLoss`, `NetIncomeLoss`, `EarningsPerShareBasic`, `EarningsPerShareDiluted`
  - Balance: `Assets`, `AssetsCurrent`, `Liabilities`, `LiabilitiesCurrent`, `StockholdersEquity`, `CashAndCashEquivalentsAtCarryingValue`, `LongTermDebt`
  - Cash flow: `NetCashProvidedByUsedInOperatingActivities`, `NetCashProvidedByUsedInInvestingActivities`, `NetCashProvidedByUsedInFinancingActivities`, `PaymentsToAcquirePropertyPlantAndEquipment`
- **Returns:** `{"income_statement": {...}, "balance_sheet": {...}, "cash_flow": {...}}`

### fetch_insider_transactions — Form 4

- **Step 1:** Fetch `https://data.sec.gov/submissions/CIK{padded_cik}.json` for filing history
- **Step 2:** Filter for `form == "4"`, take most recent 10 filings
- **Step 3:** For each filing, fetch XML document and parse with `xml.etree.ElementTree`
- **XML path:** Accession number from submissions → construct filing URL
- **Extract:** owner name, officer title, is_director, is_officer, transaction date, transaction code (P/S/A), shares, price, acquired/disposed
- **Returns:** `{"transactions": [...]}`

### fetch_institutional_holdings — 13F

- **Curated fund list:** ~10 top funds with hardcoded CIKs (Berkshire Hathaway, Baupost, Appaloosa, Greenlight, Pershing Square, Scion, etc.)
- **For each fund:** Fetch latest 13F-HR filing from submissions → parse `infotable.xml`
- **Matching:** Case-insensitive issuer name match against target company name
- **Returns:** `{"holdings": [{fund_name, fund_cik, shares, value_thousands, report_date, filing_date}]}`
- **Performance note:** ~20+ API calls per ticker query. Rate limiter manages throughput. Finnhub fallback available if EDGAR is slow/fails.

## Dependencies

- `httpx` — already used by FMP provider, no new package
- `xml.etree.ElementTree` — Python stdlib, no new package

## Constructor

```python
EDGARProvider(user_agent: str, rate_limiter: RateLimiter | None = None)
```

User-Agent is required by SEC. Format: `"CompanyName email@example.com"`. No API key.

## Testing

- Mock all httpx calls (no real SEC traffic)
- CIK mapping: load, lookup, zero-padding, missing ticker
- XBRL parsing: income/balance/cash flow extraction, missing tags
- Form 4 XML parsing: transactions, multiple owners, edge cases
- 13F XML parsing: holdings matching, no matches
- Error handling: network errors, missing CIK, empty filings
- Registry integration: per-category priority sorting, fallback chains
