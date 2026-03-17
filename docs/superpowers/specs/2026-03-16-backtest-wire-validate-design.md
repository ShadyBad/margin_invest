# Backtest Wire & Validate — Design Spec

**Date:** 2026-03-16
**Sub-project:** 1 of 3 (Wire & Validate, Shadow Portfolio + On-Demand, Full Frontend)
**Scope:** Replace synthetic backtest placeholder with real execution against production PIT data

## Context

The backtesting engine is fully built: ReplayOrchestrator, DatabasePITProvider, walk-forward partitioning, regime classification, failure audit, cost models, and API response builders all exist. A real worker (api/workers.py:2897 precompute_default_backtest) already runs the orchestrator against PIT data weekly on Sunday 3AM UTC with a 4-hour timeout. However, it currently:

- Starts from 2009 (before EDGAR data is consistent)
- Disables the entire liquidity filter (disabled_filters={"liquidity"})
- Passes no benchmark prices (SPY), causing synthetic linear benchmark
- Has no validation gates or error capture
- The async run_async() method is missing gross_return computation (present in sync run())

An admin trigger endpoint already exists at POST /admin/backtest/precompute (admin.py:657).

This sub-project fixes these gaps, changes the start date to 2011, re-enables liquidity with relaxed thresholds, adds real SPY benchmark data, adds validation gates, and adds an introspection endpoint.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Start date | 2011-01-01 (changed from 2009) | EDGAR data only semi-consistent before then |
| Scoring mode | score_universe_v3 (real) | Already wired, whole point is validation |
| Execution | Existing ARQ worker + existing admin trigger | Already built, just needs fixes |
| Validation criteria | Beat SPY after adjusting for volatility | Positive excess CAGR plus Sharpe exceeds benchmark |
| Issue handling | Hybrid: 3 fix-and-rerun cycles max | Then ship with honest disclosures |
| Liquidity filter | Re-enable with relaxed thresholds | Disabled entirely was too aggressive; relaxed values better |

## Design

### 1. Fix Worker (api/workers.py)

Modify existing precompute_default_backtest() at workers.py:2897:

1. Change start_date from 2009 to 2011
2. Remove disabled_filters={"liquidity"} — re-enable liquidity filter
3. Use backtest_filter_config() (pass as filter_config to orchestrator) instead of relying on disabled_filters
4. Load real SPY benchmark prices before constructing orchestrator (see Section 3)
5. Pass benchmark_prices to ReplayOrchestrator constructor
6. Add error capture: wrap run in try/except, store traceback in BacktestRun.error_message on failure
7. Log validation summary after successful run (see Section 5)

The sync stub precompute_default_backtest() in backtest.py:385 and run_real_backtest() in backtest.py:448 remain available as shared helpers. The worker should delegate to run_real_backtest() (with updated signature) to avoid duplication.

### 2. Backtest Filter Config Changes

backtest_filter_config() in engine/config/filter_config.py adds relaxed dollar volume tiers and keeps existing market cap / years-of-history relaxations:

| Threshold | Production | Backtest |
|-----------|-----------|----------|
| Market cap floor | 300M | 100M (already relaxed) |
| Years of history | 5 | 1 (already relaxed) |
| Dollar volume mega | 50M | 25M (new) |
| Dollar volume large | 20M | 10M (new) |
| Dollar volume mid | 5M | 2.5M (new) |
| Dollar volume small | 2M | 1M (new) |

All financial health filters remain at production defaults.

### 3. Benchmark Data (SPY Prices)

SPY is an ETF and is NOT in pit_daily_prices (which comes from EDGAR SEC filings). Primary path is yf.download.

New method on DatabasePITProvider: get_price_series(ticker, start_date, end_date) returning dict of date to float. Queries pit_daily_prices with date range filter. Used for any ticker that IS in PIT data.

For SPY specifically: fetch via yf.download("SPY", start="2011-01-01") and insert into pit_daily_prices (same schema, just SPY rows). This is a one-time seed operation run at the start of precompute_default_backtest if SPY prices are missing. No new table needed.

The worker then loads SPY prices via get_price_series() and passes them as benchmark_prices to the orchestrator.

### 4. Fix run_async() gross_return Gap

The sync run() method (replay_orchestrator.py:260-284) computes pre_cost_value and gross_return, but run_async() does not. This causes cost sensitivity analysis to produce zeros.

Add the same pre_cost_value capture and gross_return computation to run_async(). This is a 3-line fix in engine/backtesting/replay_orchestrator.py.

### 5. Admin Endpoints

POST /admin/backtest/precompute (already exists at admin.py:657)
- No changes needed. Already enqueues precompute_default_backtest.

GET /admin/backtest/latest (new)
- Auth: existing admin authentication
- Queries most recent BacktestRun ordered by created_at desc
- Returns:
  - Config used
  - Metrics (CAGR, excess CAGR, Sharpe, max drawdown, num months, avg turnover)
  - Validation summary (6 gates from Section 6, each with pass/fail)
  - Duration (started_at to completed_at)
  - Status and error_message if failed

### 6. Validation Gates

After each run, these gates are evaluated and logged (not enforced automatically):

| Metric | Gate | Rationale |
|--------|------|-----------|
| CAGR | positive | Model does not lose money over 14 years |
| Excess CAGR vs SPY | positive | Beats the benchmark |
| Sharpe ratio | exceeds benchmark Sharpe | Outperformance per unit of volatility |
| Max drawdown | below 60 percent | Not catastrophically worse than SPY GFC |
| Num months | above 100 | Enough data points (roughly 180 expected) |
| Avg turnover | below 80 percent | Not churning every month |

Validation results stored in BacktestRun.summary_stats alongside the full ReplayResult. Also logged as a structured summary at INFO level.

### 7. BacktestRun Model Changes

Add error_message column (Text, nullable) to BacktestRun model. Requires Alembic migration.

completed_at already exists. No other model changes needed.

### 8. Logging and Observability

- Run start: config summary, PIT data date range
- Run end: validation summary table (6 gates), duration, total rebalances, portfolio final value
- Errors: per-ticker scoring failures already logged by orchestrator as warnings
- Progress logging during the run is not added (would require modifying orchestrator callback interface, deferred to future work)

### 9. Timeout and Error Handling

- ARQ worker timeout: already 4 hours (14400s) at workers.py:3778
- On failure: BacktestRun.status set to "failed", error_message captures traceback
- No automatic retries
- API serves synthetic fallback (or last successful real run) via get_best_available_result()

### 10. Fix-and-Rerun Process

1. Trigger run via existing POST /admin/backtest/precompute
2. Check results via new GET /admin/backtest/latest
3. If issues found, fix and retrigger. Cap at 3 cycles.
4. After 3, ship with honest disclosures noting remaining gaps.

### 11. Serialization Size

Full ReplayResult with 180 monthly snapshots (each with up to 50 holdings) plus audit_log could be several MB of JSONB. This is acceptable for a single "default" backtest row. The existing worker already serializes the full result at workers.py:3004. No truncation needed for sub-project 1. If size becomes an issue with many on-demand runs (sub-project 2), we will address then.

## Files Touched

| File | Change |
|------|--------|
| engine/config/filter_config.py | Add relaxed dollar volume tiers to backtest_filter_config() |
| engine/backtesting/replay_orchestrator.py | Add gross_return computation to run_async() (3-line fix) |
| api/services/pit_provider.py | Add get_price_series() method |
| api/services/backtest.py | Update run_real_backtest() to accept benchmark_prices, add validation gate logic |
| api/workers.py | Fix start date, re-enable liquidity filter, load SPY prices, add error capture, log validation |
| api/routes/admin.py | Add GET /admin/backtest/latest endpoint |
| api/db/models.py | Add error_message column to BacktestRun |
| api/alembic/ | Migration for BacktestRun.error_message column |

## Files NOT Touched

Frontend, existing public API routes, other engine backtesting modules (except replay_orchestrator.py for the gross_return fix). They already work.

## What This Does NOT Include

- Shadow portfolio service (sub-project 2)
- On-demand knob runs via ARQ (sub-project 2)
- Full frontend backtest page (sub-project 3)
- Threshold calibration based on results (future work, informed by validation output)
- Progress callback during replay (deferred — would require orchestrator interface change)
