# Backtest Wire & Validate — Design Spec

**Date:** 2026-03-16
**Sub-project:** 1 of 3 (Wire & Validate, Shadow Portfolio + On-Demand, Full Frontend)
**Scope:** Replace synthetic backtest placeholder with real execution against production PIT data

## Context

The backtesting engine is fully built: ReplayOrchestrator, DatabasePITProvider, walk-forward partitioning, regime classification, failure audit, cost models, and API response builders all exist. However, precompute_default_backtest() still returns hardcoded synthetic numbers. No real backtest has ever been run against the production PIT data (217K snapshots, 12.8M prices, 5,327 tickers).

This sub-project wires the real run, executes it, and validates that the scoring system produces meaningful results.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Start date | 2011-01-01 | EDGAR data only semi-consistent before then |
| Scoring mode | score_universe_v3 (real) | Whole point is validating the actual pipeline |
| Execution | ARQ worker + admin trigger | Production-ready cron plus manual trigger for iteration |
| Validation criteria | Beat SPY after adjusting for volatility | Positive excess CAGR plus Sharpe exceeds benchmark |
| Issue handling | Hybrid: 3 fix-and-rerun cycles max | Then ship with honest disclosures |
| Filter config | Relaxed dollar volumes (half of production) | Historical markets had lower liquidity |

## Design

### 1. Wire Real Backtest Execution

api/services/backtest.py - precompute_default_backtest() becomes async:

1. Opens a DB session
2. Creates BacktestRun(name="default", status="running")
3. Loads SPY price series via new get_price_series() method
4. Builds ReplayConfig(start_date=date(2011, 1, 1), end_date=date.today())
5. Builds backtest_filter_config() (with relaxed dollar volumes)
6. Instantiates ReplayOrchestrator with DatabasePITProvider, real SPY prices, and use_real_scoring=True
7. Calls orchestrator.run_async()
8. Serializes ReplayResult into BacktestRun(status="complete", summary_stats=result)
9. Logs validation summary

Falls back gracefully: if the run fails, API continues serving the synthetic fallback via get_best_available_result().

### 2. Backtest Filter Config Changes

backtest_filter_config() in engine/config/filter_config.py gets relaxed dollar volume tiers to account for lower historical liquidity:

| Tier | Production | Backtest |
|------|-----------|----------|
| Mega | 50M | 25M |
| Large | 20M | 10M |
| Mid | 5M | 2.5M |
| Small | 2M | 1M |

All financial health filters (Beneish, Altman, FCF, interest coverage, current ratio, mediocrity gate) remain at production defaults. Market cap and years-of-history relaxations already exist.

### 3. Benchmark Data (SPY Prices)

The orchestrator needs real SPY prices. Currently falls back to synthetic linear growth when benchmark_prices is empty.

New method on DatabasePITProvider: get_price_series(ticker, start_date, end_date) returning dict of date to float. Single SQL query against pit_daily_prices filtering by ticker and date range.

Called before orchestrator construction to load SPY prices for the full backtest window. If SPY is not in PIT data, fall back to a one-time yf.download fetch stored in a backtest_benchmark_prices table.

### 4. Admin Endpoints

POST /admin/backtest/trigger
- Auth: existing admin authentication
- Enqueues precompute_default_backtest via ARQ
- Returns job ID and enqueued status

GET /admin/backtest/latest
- Auth: existing admin authentication
- Returns the most recent BacktestRun with:
  - Config used
  - Metrics (CAGR, excess CAGR, Sharpe, max drawdown, num months)
  - Validation summary (6 gates, each with pass/fail)
  - Duration, timestamps
  - Error message if failed

### 5. Validation Gates

After each run, these gates are evaluated and logged (not enforced automatically):

| Metric | Gate | Rationale |
|--------|------|-----------|
| CAGR | positive | Model does not lose money over 14 years |
| Excess CAGR vs SPY | positive | Beats the benchmark |
| Sharpe ratio | exceeds benchmark Sharpe | Outperformance per unit of volatility |
| Max drawdown | below 60 percent | Not catastrophically worse than SPY GFC |
| Num months | above 100 | Enough data points (roughly 180 expected) |
| Avg turnover | below 80 percent | Not churning every month |

Results stored in BacktestRun.summary_stats alongside the full ReplayResult.

### 6. Logging and Observability

- Run start: config summary, PIT data date range, universe size
- Progress: every 20 rebalances — current date, portfolio value, elapsed time, ETA
- Run end: full validation summary table, duration, total rebalances
- Errors: per-ticker scoring failures logged as warnings (not fatal). If more than 50 percent fail at any rebalance, log error but continue.

### 7. Timeout and Error Handling

- ARQ worker timeout: 4 hours (separate from normal worker timeout)
- On failure: BacktestRun.status set to failed, error_message captures traceback
- No automatic retries — investigate manually, fix, trigger rerun
- API serves synthetic fallback (or last successful real run) during failures

### 8. Fix-and-Rerun Process

1. First run completes — check metrics via GET /admin/backtest/latest
2. If issues found — fix data/filter/scoring, trigger rerun via POST /admin/backtest/trigger
3. Cap at 3 cycles. After 3, ship with honest disclosures noting remaining gaps.

## Files Touched

| File | Change |
|------|--------|
| engine/config/filter_config.py | Relax dollar volume tiers in backtest_filter_config() |
| api/services/pit_provider.py | Add get_price_series() method |
| api/services/backtest.py | Replace synthetic precompute_default_backtest() with real async run |
| api/workers.py | Wire async precompute, 4hr timeout |
| api/routes/admin.py | Add POST trigger and GET latest endpoints |
| api/db/models.py | Ensure BacktestRun has error_message, completed_at if missing |

## Files NOT Touched

Engine backtesting modules, frontend, existing public API routes. They already work — this sub-project feeds them real data.

## What This Does NOT Include

- Shadow portfolio service (sub-project 2)
- On-demand knob runs via ARQ (sub-project 2)
- Full frontend backtest page (sub-project 3)
- Threshold calibration based on results (future work, informed by validation output)
