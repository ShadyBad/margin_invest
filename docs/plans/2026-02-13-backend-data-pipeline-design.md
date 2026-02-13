# Backend Data Pipeline Design

Wire real scoring data through the backend so the API serves actual computed scores from financial data.

## Architecture

```
yfinance ──> financial_data (DB) ──> ARQ Worker ──> scores (DB) ──> API ──> Frontend
   ^                                     |
   |                                     v
seed CLI                          engine scoring pipeline
```

## Components

### 1. Database Schema & Migrations (Alembic)

Initialize Alembic for the `margin-api` package. Generate initial migration from existing ORM models (assets, scores, users, auth tables).

**New ORM model**: `FinancialData`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| asset_id | FK -> assets.id | Indexed |
| period_end | Date | End of fiscal period |
| filing_date | String | ISO date |
| income_statement | JSONB | Raw provider data |
| balance_sheet | JSONB | Raw provider data |
| cash_flow | JSONB | Raw provider data |
| price_history | JSONB | Array of price bars |
| earnings_data | JSONB | Quarterly EPS data |
| source | String | Provider name (e.g., "yfinance") |
| fetched_at | DateTime | When data was retrieved |

- Unique constraint: `(asset_id, period_end)`
- Add `score_detail` JSONB column to existing `scores` table for full factor breakdowns

### 2. Data Seeding CLI

Command: `uv run python -m margin_api.cli seed`

- Hardcoded list of ~50 S&P 500 tickers (top by market cap, across sectors)
- For each ticker: fetch fundamentals, price history, earnings via `YFinanceProvider`
- Upsert `Asset` row (ticker, name, sector, sub_industry, market_cap)
- Store raw data in `financial_data` table
- Respect rate limits via engine's `RateLimiterRegistry` (60 req/min for yfinance)
- Progress reporting to stdout
- After seeding completes, enqueue all tickers for scoring

### 3. Background Scoring Worker (ARQ)

Task: `score_ticker(ticker: str)`

1. Load `financial_data` + `asset` from DB for the given ticker
2. Parse JSONB into engine's `FinancialPeriod` + `AssetProfile` Pydantic models
3. Run elimination filters (Beneish, Altman, FCF, interest coverage, current ratio, liquidity)
4. If filters pass: compute quality, value, momentum factor scores
5. Classify growth stage
6. Compute composite score via `compute_composite_score()`
7. Write `Score` row to DB (composite_percentile, conviction_level, signal, factor percentiles)
8. Store full `CompositeScore` as JSONB in `score_detail` column

Worker config:
- ARQ with Redis backend (already in docker-compose)
- Concurrency: 5 workers (yfinance rate limit is per-process)
- Retry: 3 attempts with exponential backoff

### 4. API Route Refactoring

Replace in-memory `_score_store` dict with async SQLAlchemy queries.

**GET /scores/{ticker}**:
- Join `scores` + `assets` on `asset_id`
- Filter by ticker, order by `scored_at DESC`, limit 1
- Parse `score_detail` JSONB for factor breakdowns
- Return `ScoreResponse`

**GET /scores**:
- Paginated query with optional `min_percentile` and `conviction` filters
- Join with `assets` for ticker/name
- Return `ScoreListResponse`

**GET /dashboard**:
- Query scores with conviction in (exceptional, high) for picks
- Query scores with conviction = watchlist for watchlist items
- Join with `assets` for name
- Return `DashboardResponse` with real data

**Removed**: `_score_store` dict, `POST /scores/{ticker}`, `DELETE /scores/{ticker}` (scores are computed, not user-submitted)

### 5. Data Conversion Layer

Add `margin_api.services.scoring` module:
- `financial_data_to_period(row: FinancialData) -> FinancialPeriod`: Parse JSONB to engine models
- `financial_data_to_profile(asset: Asset, row: FinancialData) -> AssetProfile`: Build asset profile
- `run_scoring_pipeline(ticker: str, session: AsyncSession) -> CompositeScore`: Orchestrate full pipeline

### 6. Frontend Impact

None. API response schemas are unchanged. The frontend already consumes the correct endpoints.

## S&P 500 Ticker List (~50)

Cross-sector representation:
- Tech: AAPL, MSFT, NVDA, GOOGL, META, AMZN, AVGO, ORCL, CRM, AMD
- Healthcare: UNH, JNJ, LLY, ABBV, MRK
- Financials: JPM, V, MA, BAC, GS
- Consumer: PG, KO, PEP, COST, WMT, HD
- Energy: XOM, CVX
- Industrials: CAT, GE, HON, UNP, RTX
- Communication: NFLX, DIS, CMCSA
- Utilities: NEE, SO, DUK
- Materials: LIN, APD, SHW
- Real Estate: PLD, AMT
- Consumer Disc: TSLA, NKE, SBUX, MCD, TJX

## Dependencies

New packages for `margin-api`:
- `arq` — async Redis job queue
- `alembic` — database migrations
- `asyncpg` — already installed

## Success Criteria

1. `uv run python -m margin_api.cli seed` populates 50 tickers with financial data
2. ARQ worker scores all 50 tickers within 5 minutes
3. `GET /api/v1/scores/AAPL` returns real composite score with factor breakdowns
4. `GET /api/v1/dashboard` returns picks and watchlist based on real scores
5. All existing API tests updated and passing
6. New integration tests for the scoring pipeline
