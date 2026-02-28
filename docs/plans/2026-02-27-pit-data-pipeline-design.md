# PIT Data Pipeline Design

Replace synthetic backtesting data with real point-in-time (PIT) historical data sourced from SEC EDGAR XBRL filings and yfinance daily prices.

## Decisions

- **Data sources**: SEC EDGAR (XBRL filings for PIT fundamentals) + yfinance (daily prices)
- **History depth**: Full XBRL era (2009–2026), ~68 quarters
- **Universe**: All SEC filers with sufficient liquidity (market cap threshold)
- **Delisting**: Track universe membership via filing activity; 2+ consecutive quarters of no filing = delisted; exit at last known price
- **Architecture**: Monolithic backfill into PostgreSQL + `DatabasePITProvider` implementing the existing `PointInTimeProvider` protocol
- **Async strategy**: Add `AsyncPointInTimeProvider` protocol to engine; `DatabasePITProvider` implements it natively

## Current State

The backtesting engine architecture is complete and tested:
- `ReplayOrchestrator` replays the scoring pipeline against historical data
- `PointInTimeProvider` protocol defines the data access interface
- `InMemoryPITProvider` exists for tests
- API endpoints exist (`/backtest/teaser`, `/backtest/default`, `/backtest/replay`, `/backtest/shadow-portfolio`)
- DB tables exist (`backtest_runs`, `backtest_results`, `shadow_portfolio_snapshots`)

Everything user-facing returns synthetic data:
- `get_default_replay_result()` returns hardcoded metrics (10.4% CAGR, 0.85 Sharpe) with constant monthly returns
- Equity curve is perfectly smooth (no realistic volatility or drawdowns)
- Audit logs, factor timelines, failure audits all return empty arrays
- Shadow portfolio endpoint returns zeroed-out response

## Schema

### New Tables

#### `pit_financial_snapshots`

One row per SEC filing, as-originally-reported. Amendments stored as separate rows.

| Column | Type | Notes |
|--------|------|-------|
| id | BigInteger, PK | |
| cik | String, indexed | SEC Central Index Key |
| ticker | String, indexed | Mapped from CIK at filing time |
| filing_date | Date, indexed | When SEC received the filing |
| period_end | Date | Fiscal period end date |
| form_type | String | 10-K, 10-Q, 10-K/A, 10-Q/A |
| accession_number | String, unique | SEC filing ID, dedup key |
| income_statement | JSONB | Revenue, net income, EBIT, etc. |
| balance_sheet | JSONB | Assets, liabilities, equity, debt |
| cash_flow | JSONB | Operating CF, capex, dividends |
| shares_outstanding | BigInteger, nullable | |
| fiscal_year | Integer | |
| fiscal_quarter | Integer, nullable | Null for annual filings |
| ingested_at | DateTime | |

Unique constraint: `(accession_number)`.

#### `pit_daily_prices`

Daily OHLCV prices for all universe tickers.

| Column | Type | Notes |
|--------|------|-------|
| ticker | String, PK | |
| date | Date, PK | Trading day |
| open | Float | |
| high | Float | |
| low | Float | |
| close | Float | |
| adj_close | Float | Split/dividend adjusted |
| volume | BigInteger | |
| source | String | "yfinance" |

Composite PK: `(ticker, date)`.

#### `pit_universe_membership`

Quarterly snapshot of which companies were active filers.

| Column | Type | Notes |
|--------|------|-------|
| id | BigInteger, PK | |
| ticker | String, indexed | |
| cik | String | |
| quarter_date | Date | e.g., 2020-03-31 |
| is_active | Boolean | Filed this quarter? |
| market_cap | Float, nullable | For liquidity filtering |
| last_filing_date | Date, nullable | Most recent filing seen |
| delist_detected_at | Date, nullable | When filings stopped |
| last_known_price | Float, nullable | Exit price for delisted |

Unique constraint: `(ticker, quarter_date)`.

### Modified Tables

**`backtest_runs`**: Add `pit_data_version` (String) for reproducibility hash.

## EDGAR XBRL Ingestion Pipeline

### Architecture

```
edgar-backfill CLI command
├── Phase 1: Index Build
│   ├── Download company.idx for each quarter (2009 Q1 → 2026 Q1)
│   ├── Filter for form types: 10-K, 10-Q, 10-K/A, 10-Q/A
│   ├── Map CIK → ticker using SEC company-tickers JSON
│   └── Produce list of (accession_number, cik, form_type, filing_date) to fetch
│
├── Phase 2: XBRL Fetch + Parse
│   ├── For each accession not already in pit_financial_snapshots:
│   │   ├── Download filing from EDGAR archives
│   │   ├── Find XBRL instance document (*.xml or inline XHTML)
│   │   ├── Parse using lxml + ElementTree (standardized US-GAAP tags)
│   │   ├── Extract ~30 financial fields with fallback tag chains
│   │   └── Insert into pit_financial_snapshots
│   ├── Rate limit: 5 req/sec (SEC allows 10, we stay conservative)
│   ├── User-Agent: "MarginInvest admin@margininvest.com"
│   └── Checkpoint: commit every 100 filings, resume from last accession
│
├── Phase 3: Universe Assembly
│   ├── For each quarter: scan which CIKs filed a 10-Q or 10-K
│   ├── 2+ consecutive quarters without filing → mark delist_detected_at
│   ├── Fetch last known price from pit_daily_prices for delisted tickers
│   └── Populate pit_universe_membership
│
└── Phase 4: Validation
    ├── Golden-value check against known filings (AAPL, MSFT, JPM, JNJ, XOM)
    ├── Count check: 3000-6000 filers per quarter expected
    └── Flag filings with missing critical fields
```

### XBRL Tag Mapping

| Engine Field | Primary US-GAAP Tag | Fallbacks |
|---|---|---|
| revenue | `Revenues` | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet` |
| net_income | `NetIncomeLoss` | `ProfitLoss`, `NetIncomeLossAvailableToCommonStockholdersBasic` |
| total_assets | `Assets` | — |
| total_liabilities | `Liabilities` | `LiabilitiesAndStockholdersEquity` minus `StockholdersEquity` |
| operating_cash_flow | `NetCashProvidedByOperatingActivities` | `CashFlowsFromOperatingActivities` |
| capex | `PaymentsToAcquirePropertyPlantAndEquipment` | `PurchaseOfPropertyPlantAndEquipment` |
| shares_outstanding | `CommonStockSharesOutstanding` | `WeightedAverageNumberOfSharesOutstandingBasic` |
| long_term_debt | `LongTermDebt` | `LongTermDebtNoncurrent` |
| current_assets | `AssetsCurrent` | — |
| current_liabilities | `LiabilitiesCurrent` | — |
| interest_expense | `InterestExpense` | `InterestExpenseDebt` |
| dividends_paid | `PaymentsOfDividends` | `PaymentsOfDividendsCommonStock` |
| share_repurchases | `PaymentsForRepurchaseOfCommonStock` | — |
| gross_profit | `GrossProfit` | Revenue minus `CostOfGoodsAndServicesSold` |
| ebit | `OperatingIncomeLoss` | Revenue minus COGS minus SGA |
| total_equity | `StockholdersEquity` | `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |

### Price Backfill

Separate CLI command using yfinance bulk download:

```
price-backfill CLI command
├── Collect all unique tickers from pit_financial_snapshots
├── Batch download in groups of 500 via yf.download()
├── Insert into pit_daily_prices with ON CONFLICT DO NOTHING
├── Estimated: ~4000 tickers × ~4000 trading days = ~16M rows
└── Runtime: 1-3 hours
```

## DatabasePITProvider

Implements `AsyncPointInTimeProvider` protocol. Lives in `api/src/margin_api/services/pit_provider.py`.

### Query Patterns

**`get_snapshot(ticker, as_of_date)`**: Most recent filing where `filing_date <= as_of_date`. Joins with prior period for YoY comparison. Fetches price from `pit_daily_prices`.

```sql
SELECT * FROM pit_financial_snapshots
WHERE ticker = :ticker AND filing_date <= :as_of_date
ORDER BY filing_date DESC LIMIT 2
```

**`get_universe(as_of_date)`**: Active filers in the nearest quarter, filtered by market cap.

```sql
SELECT * FROM pit_universe_membership
WHERE quarter_date = (
    SELECT MAX(quarter_date) FROM pit_universe_membership
    WHERE quarter_date <= :as_of_date
)
AND is_active = TRUE
AND market_cap >= :min_market_cap
```

**`get_price(ticker, as_of_date)`**: Exact date match, fallback to most recent prior trading day.

```sql
SELECT close FROM pit_daily_prices
WHERE ticker = :ticker AND date <= :as_of_date
ORDER BY date DESC LIMIT 1
```

**`get_delisting(ticker)`**: Check for delisting marker.

```sql
SELECT delist_detected_at, last_known_price FROM pit_universe_membership
WHERE ticker = :ticker AND delist_detected_at IS NOT NULL
ORDER BY quarter_date DESC LIMIT 1
```

### Lookahead Bias Prevention

Three guards:

1. **Filing date filter**: All financial queries use `filing_date <= as_of_date`. A Q4 2019 report filed on 2020-02-15 is invisible on 2020-01-31.
2. **Price date filter**: Prices use `date <= as_of_date` with `ORDER BY date DESC LIMIT 1`. No future prices.
3. **Factor availability registry**: Engine's existing `FactorRegistry` prevents using factors that didn't exist at a given date.

## Engine Changes

### AsyncPointInTimeProvider Protocol

Add to `engine/src/margin_engine/backtesting/pit_provider.py`:

```python
class AsyncPointInTimeProvider(Protocol):
    """Async variant for database-backed providers."""
    async def get_snapshot(self, ticker: str, as_of_date: date) -> PITSnapshot | None: ...
    async def get_universe(self, as_of_date: date) -> list[PITSnapshot]: ...
    async def get_price(self, ticker: str, as_of_date: date) -> float | None: ...
    async def get_delisting(self, ticker: str) -> DelistingEvent | None: ...
```

### ReplayOrchestrator Async Path

Add `async def run_async(self)` alongside existing sync `run()`. Same logic, awaits provider calls. The sync path remains for tests using `InMemoryPITProvider`.

## API Wiring

### Replace Synthetic Data

Remove `get_default_replay_result()`. Replace with:

1. **`precompute_default_backtest`** ARQ worker (weekly schedule):
   - Instantiates `DatabasePITProvider` + `ReplayOrchestrator`
   - Runs full 2009–present backtest with default config
   - Stores result in `backtest_runs` table
   - API reads cached result

2. **`GET /backtest/default`** reads from `backtest_runs` (most recent completed run).

3. **`POST /backtest/replay`** instantiates orchestrator with user config, runs real backtest, caches by config hash.

4. **`GET /backtest/shadow-portfolio`** wired to daily `snapshot_shadow_portfolio` worker that records current scored portfolio as an immutable append-only snapshot.

### Response Enrichment

Currently empty fields will be populated:
- `audit_log`: Per-rebalance records (universe size, eliminations, top holdings, factor coverage)
- `factor_timeline`: Factor weight evolution over time
- `failure_audit`: Worst-performing periods with root cause attribution
- `regime_segments`: Real regime classification from market data

## Testing Strategy

### Layer 1: Data Integrity

- Golden-value tests for 5 reference companies (AAPL, MSFT, JPM, JNJ, XOM) — verify parsed XBRL against SEC filing PDFs
- Cross-reference against yfinance for non-restated periods
- Completeness: 3000+ filers per quarter
- NaN audit on all JSONB fields

### Layer 2: PIT Correctness

- **Filing lag test**: Known filing with specific date → verify prior quarter returned for dates before filing
- **Delisting test**: Known delisted company excluded from post-delisting universe, exit price correct
- **Price alignment test**: Correct close returned for specific trading day; weekends return prior Friday
- **Universe monotonicity**: Universe size generally grows 2009→2026, dips during recessions

### Layer 3: Engine Integration

- Synthetic vs. real comparison: Same config, both providers → both produce valid ReplayResult
- Determinism: Identical config → identical results
- Known-history: COVID crash (2020 Q1) correctly classified as crisis regime
- Factor coverage audit per rebalance date

### Layer 4: Anti-Regression Sentinels

- **No-future-data**: Poison filing with `filing_date = 2099-01-01` never appears in pre-2099 results
- **Survivorship**: Delisted company appears in pre-delisting universe, absent from post-delisting
- **Price gap**: Missing price data returns nearest prior price, never null or future price

### Validation Checkpoints

| Checkpoint | Gate Criteria |
|---|---|
| After EDGAR index build | >60 quarters indexed, >3000 CIKs per quarter |
| After XBRL parsing | Golden-value tests pass for 5 reference companies |
| After price backfill | >95% coverage for universe tickers across date range |
| After universe assembly | Monotonic growth trend, delisting detection working |
| After provider wiring | PIT correctness tests pass (filing lag, no lookahead) |
| After API wiring | Default backtest returns non-synthetic results with realistic volatility |
| Before production | Full regression suite green, determinism confirmed |

## Migration Roadmap

### Phase 1: Schema & Infrastructure
- Alembic migration for 3 new tables + `backtest_runs` column
- Add `lxml` dependency
- Estimated: 1 task

### Phase 2: EDGAR Backfill CLI
- CLI command `edgar-backfill`
- XBRL parser with tag mapping + fallbacks
- Rate limiting, checkpointing, resumability
- Runtime: 8-24 hours one-time
- Estimated: 3-4 tasks (index builder, XBRL parser, CLI wiring, validation)

### Phase 3: Price Backfill CLI
- CLI command `price-backfill`
- yfinance bulk download in batches
- Runtime: 1-3 hours one-time
- Estimated: 1 task

### Phase 4: Universe Assembly
- Scan filings quarterly, detect delistings
- Populate `pit_universe_membership`
- Estimated: 1 task

### Phase 5: DatabasePITProvider
- `AsyncPointInTimeProvider` protocol in engine
- `DatabasePITProvider` implementation in API
- Async `run_async()` on ReplayOrchestrator
- PIT correctness + golden-value tests
- Estimated: 2-3 tasks

### Phase 6: API Wiring
- Remove `get_default_replay_result()`
- Wire all 4 backtest endpoints to real provider
- `precompute_default_backtest` worker (weekly)
- `snapshot_shadow_portfolio` worker (daily)
- Populate audit log, factor timeline, failure audit
- Estimated: 2-3 tasks

### Phase 7: Incremental Updates
- Daily EDGAR check for new filings
- Daily price append after market close
- Quarterly universe membership refresh
- Estimated: 1-2 tasks

## Common Failure Modes

| Failure | Symptom | Mitigation |
|---|---|---|
| XBRL tag variation | Missing revenue for some filers | Fallback tag chain (5+ alternatives per concept) |
| CIK→ticker mapping gaps | Filings without ticker association | SEC company-tickers JSON + manual mapping file |
| yfinance adjusted price drift | Prices don't match other sources | Use adj_close for returns, close for display |
| EDGAR rate limiting | 429 responses | Exponential backoff, stay at 5 req/sec |
| Memory pressure during backfill | OOM on large batches | Stream results, commit every 100 filings |
| Restatement contamination | Later amendment overwrites original | Amendments (10-K/A) stored as separate rows |
| Timezone mismatch | Prices off by one day | All dates stored as UTC, market close = 16:00 ET |
| Sparse early data | Few filers in 2009-2010 | Accept lower coverage, log warnings |
