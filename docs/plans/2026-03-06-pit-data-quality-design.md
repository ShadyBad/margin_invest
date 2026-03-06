# PIT Data Quality Improvement Design

Improve backtest quality by enriching PIT data with real GICS sectors, volume/market-cap metrics, and corrected delisting detection. Two phases: data enrichment first, then quality tuning.

## Current State

The PIT backtest pipeline is functional (25.68% total return, 183 monthly snapshots, 5,327 tickers) but has significant data quality issues:

- All tickers hardcoded as `sector=GICSSector.TECHNOLOGY` — breaks sector-neutral scoring
- `avg_daily_volume=0` and `years_of_history=0` — liquidity filter fully disabled
- `detect_delistings()` uses 2-quarter threshold — marks 5,312/5,327 tickers as delisted (annual filers miss 2 quarters by definition); mitigated by bypassing `is_active` filter
- `market_cap` always NULL in `pit_universe_memberships`
- `fill_last_known_prices()` does 5,312 sequential N+1 queries
- First ~12 months of backtest select 0 stocks (unknown which filters are too aggressive)
- Accidentally committed screenshot artifacts in repo

## Phase 1: Data Enrichment

### Schema Changes

#### New table: `sic_sector_map`

Static lookup mapping SIC codes to GICS sectors. ~400 rows, seeded via Alembic migration.

| Column | Type | Notes |
|--------|------|-------|
| sic_code | Integer, PK | 4-digit SIC code |
| gics_sector | String | GICSSector enum value |
| sic_description | String, nullable | For reference |

SIC codes follow hierarchical ranges that map to GICS sectors:
- 1000-1499 (Mining) -> MATERIALS
- 2000-3999 (Manufacturing) -> split across INDUSTRIALS, CONSUMER_DISCRETIONARY, CONSUMER_STAPLES, HEALTHCARE, TECHNOLOGY
- 4000-4999 (Transportation/Utilities) -> INDUSTRIALS or UTILITIES
- 5000-5999 (Wholesale/Retail) -> CONSUMER_DISCRETIONARY or CONSUMER_STAPLES
- 6000-6799 (Finance/Insurance/Real Estate) -> FINANCIALS or REAL_ESTATE
- 7000-8999 (Services) -> COMMUNICATION_SERVICES, HEALTHCARE, TECHNOLOGY

Unmapped codes fall back to INDUSTRIALS.

#### Column additions

- `pit_financial_snapshots.sic_code` (Integer, nullable) — SIC code at filing time
- `pit_universe_memberships.sic_code` (Integer, nullable) — SIC code per quarter
- `pit_universe_memberships.avg_daily_volume` (Float, nullable) — trailing 60-day avg of close x volume

### SIC Data Source

Switch from SEC's `company_tickers.json` to `company_tickers_exchange.json`. Same structure but includes SIC codes. Extend `load_cik_ticker_map()` to return `dict[int, tuple[str, int]]` (CIK -> (ticker, sic_code)) instead of `dict[int, str]`.

### Universe Assembly Changes

**SIC codes:** Store `sic_code` on both `pit_financial_snapshots` and `pit_universe_memberships` rows during assembly.

**Market cap:** Compute `shares_outstanding x close_price` at each quarter date. `shares_outstanding` from most recent filing, `close_price` from `pit_daily_prices`. Store on existing `market_cap` column (currently always NULL).

**Avg daily dollar volume:** For each ticker at each quarter, compute trailing 60-trading-day average of `close x volume` from `pit_daily_prices`. Batch query using window functions, not N+1.

**Delisting threshold:** Change `detect_delistings()` from 2 to 8 consecutive quarters. Handles annual filers (naturally miss ~3 quarters) and companies with filing delays.

**`fill_last_known_prices()` batch fix:** Replace per-ticker loop with single batch query:
```sql
SELECT ticker, close FROM (
    SELECT ticker, close,
           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
    FROM pit_daily_prices
    WHERE ticker IN (:delisted_tickers) AND date < :delist_date
) sub WHERE rn = 1
```

### PIT Provider Changes

**`_build_profile()`:**
- Look up GICS sector from SIC code via `sic_sector_map` (query or in-memory cache)
- Populate `avg_daily_volume` from membership/price data
- Compute `years_of_history` from ticker's earliest filing date vs `as_of_date`

**`get_universe()`:** Re-enable `is_active` filter now that delisting data is trustworthy (8-quarter threshold).

**`get_prices()` batch method:** Add `get_prices(tickers: list[str], as_of_date: date) -> dict[str, float]` to `DatabasePITProvider` and `AsyncPointInTimeProvider` protocol. Used by `ReplayOrchestrator._compute_returns()` to replace per-ticker N+1 price lookups.

### Re-run

After all Phase 1 changes: re-run universe assembly once (idempotent via ON CONFLICT), then trigger `precompute_default_backtest`.

## Phase 2: Quality Tuning

### Filter Failure Diagnostics

Add `filter_failure_breakdown: dict[str, int]` field to `AuditEntry` in the replay orchestrator. Per rebalance date, track which filters caused elimination:

```python
filter_failures: dict[str, int] = defaultdict(int)
for snapshot in universe:
    result = run_elimination_filters(...)
    if not result.passed:
        for f in result.failed_filters:
            filter_failures[f.name] += 1
```

Logged at INFO level and stored in audit entries for data-driven threshold decisions.

### Re-enable Liquidity Filter

Remove `disabled_filters={"liquidity"}` from the precompute worker. With real `avg_daily_volume`, `market_cap`, and `years_of_history` populated in Phase 1, the filter will work correctly.

### Final Backtest Re-run

Trigger `precompute_default_backtest` to get updated metrics with real sectors, real volume filtering, correct delisting handling, and filter diagnostics.

### Screenshot Cleanup

`git rm` the accidentally committed screenshot/artifact files.

## Not In Scope

- Changing filter thresholds (Phase 2 diagnostics inform future decisions)
- GICS sub-industry mapping (sector level sufficient for now)
- Real company names in AssetProfile (still uses ticker as name)
- Optimizing universe assembly runtime (currently acceptable)
