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

### Percentile Ranking with a Single Ticker

`run_scoring_v4` performs universe-level percentile ranking. With a single ticker, every percentile would be degenerate (50.0 or 0/100). To handle this:

- Call `run_scoring_v4(tickers=[ticker])` to get the factor raw values and conviction gates.
- **Accept degenerate percentile ranks.** The re-score is a rapid triage — the purpose is to run the ticker through the full filter/gate pipeline (liquidity, mediocrity, conviction gates) after a drawdown event, not to produce a publication-ready composite rank. The next full `full_score_v4` run (daily 21:30 UTC chain) will recompute proper universe-level percentiles for this ticker alongside all others.
- Store the `new_conviction` on the `DrawdownRescreen` record so the operator can see if the drawdown changed the ticker's gate outcome.

### Schema Change: DrawdownRescreen

The `DrawdownRescreen` model (models.py:1346) has no `rescored_at` column. Use the existing `outcome` column (String(20), nullable) to record completion status:
- On success: `outcome = "rescored"`
- On failure: `outcome = "failed"`
- Also set `new_conviction` to the V4Score's conviction value on success.

No Alembic migration needed — `outcome` and `new_conviction` columns already exist.

### Changes
Replace the stub body with:
1. Call `run_scoring_v4(tickers=[ticker])` — this computes raw factor scores, composites, and percentiles, then runs the v4 pipeline with ML/Track C.
2. Look up the DrawdownRescreen record to update: query `WHERE ticker = :ticker AND outcome IS NULL ORDER BY created_at DESC LIMIT 1`. This handles the case where multiple drawdown events may be enqueued for the same ticker — we update only the most recent unprocessed one.
3. Set `outcome = "rescored"` and `new_conviction` from the resulting V4Score's conviction value.
4. No staging/approval gate — drawdown re-scores are time-sensitive. Scores are written as unpublished V4Score rows (consistent with daily pipeline before `stage_scores`).

### Error Handling
- Wrap in try/except. On failure: log exception, set `outcome = "failed"`, return `{"status": "error", "error": str(exc)}`.

### Tests
- Unit test: mock `run_scoring_v4`, verify called with `tickers=[ticker]`.
- Unit test: verify `DrawdownRescreen.outcome` is set to `"rescored"` on success, `"failed"` on failure.
- Unit test: verify `new_conviction` is populated from V4Score result.

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

**Integration point:** `compute_raw_factor_scores()` in `api/src/margin_api/services/scoring.py` (line ~225). This function builds the momentum sub-scores list. Line 319 currently has `sentiment_score(score=0.0)` as a hardcoded neutral stub.

**API changes (scoring.py):**
1. Add an optional `sentiment_value: float | None = None` parameter to `compute_raw_factor_scores()`.
2. Replace line 319 (`sentiment_score(score=0.0)`) with:
   - If `sentiment_value is not None`: call `sentiment_score(score=sentiment_value, has_contrarian_signal=False)`. The contrarian signal is computed post-hoc (see below).
   - If `sentiment_value is None`: skip the sentiment sub-score entirely (don't append the neutral stub).
3. Remove `stub=True` from `sentiment_score()` return value in `engine/scoring/quantitative/sentiment_score.py`. Since the function is now only called with real sentiment values (None case skips entirely), the stub flag is no longer needed.
4. **Historical scorer** (`historical_scorer.py`): also has a `sentiment_score(score=0.0)` stub. Leave it unchanged for now — backtesting uses historical data and should not retroactively inject NLP sentiment that didn't exist at the time. This is explicitly out of scope.

**API changes (cli.py — data loading):**
1. In `run_scoring_v3()` / `run_scoring_v4()`, before calling `compute_raw_factor_scores()`: batch-query `FilingSentimentCache` for all tickers being scored.
   - Query: latest row per ticker's asset, where `analysis_version == NLP_ANALYSIS_VERSION`.
   - Import `NLP_ANALYSIS_VERSION` — expose `_ANALYSIS_VERSION` from `margin_api.services.nlp_analyzer` as a public constant `NLP_ANALYSIS_VERSION = "v1"`.
2. Pass each ticker's `sentiment_value` through to `compute_raw_factor_scores()`.

**Contrarian signal (post-ranking):**
The contrarian signal requires `quality_percentile`, which is only available after `rank_and_compute_composites()` runs. Handle this as a post-ranking fixup:
1. After percentile ranking, for each CompositeScore: if `quality.average_percentile >= 70` and the ticker's `sentiment_value < 0`, recompute `sentiment_score(value, has_contrarian_signal=True)` and replace the sentiment sub-score in momentum's sub_scores list.
2. This is a targeted fixup on the already-computed CompositeScore — no pipeline restructuring needed.

**What does NOT change:**
- NLP analyzer, text extractor, worker/cron integration (already complete).
- Dashboard rendering — already extracts sentiment from `momentum.sub_scores[name="sentiment"]` via the V4Score migration done earlier this session.

**Null handling:** When no cache entry exists, `sentiment_value` stays None, sentiment sub-score is skipped entirely. Momentum percentile is computed from the remaining sub-scores only. Sentiment appears gradually as filings are analyzed.

### Tests
- Engine: momentum includes sentiment sub-score when `sentiment_value` provided.
- Engine: momentum unchanged when `sentiment_value` is None (no stub score appended).
- Engine: contrarian signal fixup fires when quality ≥ 70 and sentiment < 0.
- API: scoring pipeline batch-loads sentiment from FilingSentimentCache.

## Phase 3: TAM Data Wiring

### Current State
- `tam_expansion_velocity(segment_revenues, industry_growth_rate)` returns a FactorScore (0-10). Fully tested.
- `tam_modifier(score)` maps that score to a multiplier (0.95-1.10). Fully tested.
- `v3_pipeline.py:203` and `v4_pipeline.py:329` call `tam_modifier(None)` → always returns 1.0.

### Changes

**Engine changes:**
1. Add `revenue_history: list[dict] | None = None` to `TickerDataBase` — list of `{"revenue": float, "year": int}`.
2. Add `SECTOR_GROWTH_RATES: dict[str, float]` config in `engine/config/` keyed by `GICSSector` string values (e.g., `"Information Technology": 0.12`, `"Health Care": 0.08`). All 11 GICS sectors must have an entry. Values are approximate annual industry growth rates sourced from public market data.
3. In v3/v4 pipeline, replace `tam_modifier(None)` with:
   - If `revenue_history` has ≥ 2 points and sector is in `SECTOR_GROWTH_RATES`:
     - Call `tam_expansion_velocity(revenue_history, industry_growth_rate)`.
     - If result is not None: pass `result.raw_value` to `tam_modifier(score)`.
     - If result is None (insufficient data points after filtering): `tam_modifier(None)`.
   - Else: `tam_modifier(None)` (unchanged fallback).

**API changes (cli.py — data loading):**
1. In `run_scoring_v3()` / `run_scoring_v4()`: query existing financial data to build `revenue_history` from the last 3-5 years of annual revenue. Source: `pit_financial_snapshots.income_statement` JSONB (key: `"revenue"`). Aggregate quarterly rows to annual by `fiscal_year`. Handle cases where `income_statement` is None or `"revenue"` key is missing (skip that quarter).
2. Look up `Asset.sector` to get the GICS sector string, pass to pipeline for `SECTOR_GROWTH_RATES` lookup.

### Data Source
Total company revenue (already ingested) is used as a proxy for segment revenue. This captures the core signal — is this company outgrowing its industry? — without requiring XBRL segment parsing.

### Limitations (Documented, Not Fixed)
- Total revenue is a proxy: multi-segment companies get a blended rate.
- Sector-level growth rates are coarse vs. industry-level.
- Both are strictly better than the current no-op (1.0x multiplier for all).

### Tests
- Engine: pipeline uses TAM modifier when revenue history available.
- Engine: pipeline falls back to `tam_modifier(None)` when no revenue data.
- Engine: `SECTOR_GROWTH_RATES` has entries for all 11 GICS sectors (exhaustiveness test).
- Engine: TAM score computation handles edge cases (single data point, zero industry rate).

## Execution Order

1. **Phase 1 (rescore_ticker):** ~15 lines of real logic. No dependencies. No migration.
2. **Phase 2a (flip NLP flag):** Env var change on Railway. No code.
3. **Phase 2b (NLP scoring wiring):** API changes in scoring.py + cli.py, engine change in sentiment_score.py. Independent of Phase 1.
4. **Phase 3 (TAM wiring):** Engine config + pipeline changes, API data loading. Independent of Phases 1-2.

Phases can be implemented and shipped independently. Phase 2a should ship as early as possible to let the sentiment cache populate.

## Out of Scope
- XBRL segment revenue parsing (future enhancement for TAM precision).
- NLP moat enrichment Phase 2 (depends on NLP data flowing first).
- Simulator Kelly sizing wiring (separate subsystem, separate spec).
- v3 cascade conditional gate activation (separate engine work).
- Legacy Score table cleanup (separate migration).
