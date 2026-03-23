# Pipeline Wiring Gaps — Design Spec

**Date:** 2026-03-22
**Status:** Approved
**Scope:** Wire three existing stubs into the scoring pipeline: rescore_ticker, NLP→scoring integration, TAM data wiring.

## Context

The scoring pipeline has three subsystems that are fully built but not connected:

1. **rescore_ticker** — stub that logs intent but doesn't score. Called by DrawdownScreener on price drawdowns ≥20%.
2. **NLP pipeline** — Claude Haiku analysis of SEC filings, feature-gated off. Results cached in `FilingSentimentCache` but never read by scoring.
3. **TAM modifier** — `tam_expansion_velocity()` and `tam_modifier()` both implemented and tested. Pipeline always passes `tam_modifier(None)` → 1.0 (no effect).

All three follow the same pattern: infrastructure exists, wiring is missing. They ship as three sequential phases with no cross-dependencies.

## Phase 1: rescore_ticker

### Current State
- `rescore_ticker(ctx, ticker, trigger_reason)` in `workers.py` is a logging-only stub returning `{"status": "placeholder"}`.
- `DrawdownScreener.trigger_rescreening()` enqueues `rescore_ticker` jobs via ARQ when a ticker drops ≥20% from its 52-week high.
- The CLI functions `run_scoring_v3(tickers=...)` and `run_scoring_v4(tickers=...)` already accept an optional ticker list parameter.

### Changes
Replace the stub body with:
1. Call `run_scoring_v4(tickers=[ticker])` — this internally runs v3 first, then extends with ML/Track C.
2. Update the `DrawdownRescreen` record: set `rescored_at = datetime.now(UTC)` on success.
3. No staging/approval gate — drawdown re-scores are time-sensitive. Scores are written as unpublished V4Score rows (consistent with daily pipeline before `stage_scores`).

### Error Handling
- Wrap in try/except. On failure: log exception, return `{"status": "error", "error": str(exc)}`.
- Do NOT mark DrawdownRescreen.rescored_at on failure (allows retry on next cron cycle).

### Tests
- Unit test: mock `run_scoring_v4`, verify called with `tickers=[ticker]`.
- Unit test: verify `DrawdownRescreen.rescored_at` is set on success, not set on failure.

## Phase 2: NLP → Scoring Integration

### Step 2a: Enable Feature Flag (No Code Change)
Set `MARGIN_NLP_ENABLED=true` on Railway. The existing infrastructure handles everything:
- `daily_pit_update` cron (23:00 UTC) enqueues `analyze_filing_text` jobs for new filings.
- `nlp_analyzer.py` calls Claude Haiku (temperature=0, deterministic).
- Results cached in `FilingSentimentCache` (keyed by filing_text_id + analysis_version).
- Cost: ~$12/quarter at ~50 filings/day.
- Rate-limited via `MARGIN_NLP_MAX_FILINGS_PER_DAY` (default 50).

This step ships first so the cache populates while the scoring integration is built.

### Step 2b: Wire Sentiment into Scoring Pipeline

**Engine changes:**
1. Add `sentiment_value: float | None = None` to `TickerDataBase` in `ticker_data.py`.
2. In momentum factor computation, when `sentiment_value is not None`:
   - Call existing `sentiment_score(value, has_contrarian_signal)`.
   - Contrarian signal: `has_contrarian_signal = True` when `quality_percentile >= 70` and `sentiment_value < 0`.
   - Append returned `FactorScore` to momentum's `sub_scores`.
3. Remove `stub=True` from `sentiment_score()` return value.

**API changes:**
1. In `load_ticker_v3_data()` / `load_ticker_v4_data()` (cli.py): query `FilingSentimentCache` for each ticker's latest `sentiment_value`. Populate `TickerDataBase.sentiment_value`.
2. Query: latest `FilingSentimentCache` row per ticker where `analysis_version` matches current version.

**What does NOT change:**
- NLP analyzer, text extractor, worker/cron integration (already complete).
- Dashboard rendering — already extracts sentiment from `momentum.sub_scores[name="sentiment"]` via the V4Score migration done earlier this session.

**Null handling:** When no cache entry exists, `sentiment_value` stays None, sentiment sub-score is skipped. Momentum percentile is unchanged. Sentiment appears gradually as filings are analyzed.

### Tests
- Engine: momentum includes sentiment sub-score when `sentiment_value` provided.
- Engine: momentum unchanged when `sentiment_value` is None.
- Engine: contrarian signal fires when quality ≥ 70 and sentiment < 0.
- API: scoring pipeline loads sentiment from FilingSentimentCache.

## Phase 3: TAM Data Wiring

### Current State
- `tam_expansion_velocity(segment_revenues, industry_growth_rate)` returns a FactorScore (0-10). Fully tested.
- `tam_modifier(score)` maps that score to a multiplier (0.95-1.10). Fully tested.
- `v3_pipeline.py:203` and `v4_pipeline.py:329` call `tam_modifier(None)` → always returns 1.0.

### Changes

**Engine changes:**
1. Add `revenue_history: list[dict] | None = None` to `TickerDataBase` — list of `{"revenue": float, "year": int}`.
2. Add `SECTOR_GROWTH_RATES: dict[str, float]` config mapping GICS sector names to annual growth rates (e.g., `"TECHNOLOGY": 0.12`). ~11 sectors.
3. In v3/v4 pipeline, replace `tam_modifier(None)` with:
   - If `revenue_history` has ≥ 2 points and sector has a growth rate:
     - Call `tam_expansion_velocity(revenue_history, industry_growth_rate)`.
     - Pass resulting `raw_value` to `tam_modifier(score)`.
   - Else: `tam_modifier(None)` (unchanged fallback).

**API changes:**
1. In `load_ticker_v3_data()`: query existing financial data to build `revenue_history` from the last 3-5 years of annual revenue. Source: yfinance data already stored in `score_detail` JSONB or `pit_financial_snapshots`.
2. Look up `Asset.sector` to get the GICS sector, map to growth rate via `SECTOR_GROWTH_RATES`.

### Data Source
Total company revenue (already ingested) is used as a proxy for segment revenue. This captures the core signal — is this company outgrowing its industry? — without requiring XBRL segment parsing.

### Limitations (Documented, Not Fixed)
- Total revenue is a proxy: multi-segment companies get a blended rate.
- Sector-level growth rates are coarse vs. industry-level.
- Both are strictly better than the current no-op (1.0x multiplier for all).

### Tests
- Engine: pipeline uses TAM modifier when revenue history available.
- Engine: pipeline falls back to `tam_modifier(None)` when no revenue data.
- Engine: `SECTOR_GROWTH_RATES` has entries for all 11 GICS sectors.

## Execution Order

1. **Phase 1 (rescore_ticker):** ~10 lines of real logic. No dependencies.
2. **Phase 2a (flip NLP flag):** Env var change on Railway. No code.
3. **Phase 2b (NLP scoring wiring):** Engine + API changes. Independent of Phase 1.
4. **Phase 3 (TAM wiring):** Engine + API changes. Independent of Phases 1-2.

Phases can be implemented and shipped independently. Phase 2a should ship as early as possible to let the sentiment cache populate.

## Out of Scope
- XBRL segment revenue parsing (future enhancement for TAM precision).
- NLP moat enrichment Phase 2 (depends on NLP data flowing first).
- Simulator Kelly sizing wiring (separate subsystem, separate spec).
- v3 cascade conditional gate activation (separate engine work).
- Legacy Score table cleanup (separate migration).
