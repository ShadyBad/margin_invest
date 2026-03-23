# Pipeline Wiring Gaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Wire three existing stubs into the scoring pipeline.

**Architecture:** Each phase replaces a stub with a call to existing, tested infrastructure. No new tables, no new external APIs.

**Spec:** `docs/superpowers/specs/2026-03-22-pipeline-wiring-gaps-design.md` (full design details)

## Task 1: rescore_ticker - Write Failing Test

**Files:** Create `api/tests/workers/test_rescore_ticker.py`

- [ ] Write 3 tests: (1) calls scoring pipeline via mocked run_scoring_v4, (2) updates DrawdownRescreen.outcome on success, (3) handles failure gracefully with error status
- [ ] Run tests, verify they fail because stub returns placeholder

## Task 2: rescore_ticker - Implement

**Files:** Modify `api/src/margin_api/workers.py:4438-4515`

- [ ] Replace stub body with real scoring call: `run_scoring_v4(tickers=[ticker])`
- [ ] Query latest unprocessed DrawdownRescreen for the ticker (outcome IS NULL, ORDER BY created_at DESC)
- [ ] On success: set outcome="rescored", fetch new V4Score conviction, set new_conviction
- [ ] On failure: catch exception, set outcome="failed", log, return error dict
- [ ] Run tests (3 PASS), run full API suite for regressions, commit

## Task 3: NLP - Expose Analysis Version

**Files:** Modify `api/src/margin_api/services/nlp_analyzer.py:34`

- [ ] Add `NLP_ANALYSIS_VERSION = _ANALYSIS_VERSION` below line 34
- [ ] Run NLP tests, commit

## Task 4: NLP - Remove sentiment_score Stub Flag

**Files:** Modify `engine/src/margin_engine/scoring/quantitative/sentiment_score.py:72`

- [ ] Change `stub=True` to `stub=False` at line 72
- [ ] Run existing sentiment_score tests, commit

## Task 5: NLP - Add sentiment_value to TickerDataBase

**Files:** Modify `engine/src/margin_engine/scoring/ticker_data.py`

- [ ] Add `sentiment_value: float | None = None` field
- [ ] Run engine scoring tests for regressions, commit

## Task 6: NLP - Wire Sentiment into scoring

**Files:** Modify `scoring.py:225,319`, `cli.py`. Create `engine/tests/scoring/test_sentiment_wiring.py`, `api/tests/services/test_sentiment_loading.py`

- [ ] Write engine tests: (1) real value produces non-stub FactorScore, (2) contrarian bonus increases raw_value, (3) score=0.0 maps to midrange
- [ ] Run engine tests (should pass already - testing existing function)
- [ ] Add `sentiment_value: float | None = None` param to `compute_raw_factor_scores()`
- [ ] Replace line 319 stub: conditionally append sentiment sub-score only when value provided
- [ ] Write API tests: (1) cache query returns latest entry, (2) returns None for unknown ticker
- [ ] In cli.py: batch query FilingSentimentCache filtered by NLP_ANALYSIS_VERSION, build sentiment dict, pass to compute_raw_factor_scores
- [ ] Run full test suites, commit

## Task 7: NLP - Post-Ranking Contrarian Signal

**Files:** Modify scoring pipeline post-ranking section. Update `test_sentiment_wiring.py`.

- [ ] Add 2 contrarian tests: bonus applied with negative sentiment, no bonus with positive
- [ ] After rank_and_compute_composites: iterate composites, if sentiment < 0 AND quality.average_percentile >= 70, recompute sentiment_score with has_contrarian_signal=True, replace in momentum sub_scores
- [ ] Run tests, commit

## Task 8: TAM - Add SECTOR_GROWTH_RATES Config

**Files:** Modify `engine/src/margin_engine/config/industry_growth_rates.py`. Create `engine/tests/config/test_sector_growth_rates.py`.

- [ ] Write 4 tests: all 11 GICSSector values present, rates in [-0.05, 0.30], known sector lookup, unknown returns 0.05 default
- [ ] Add SECTOR_GROWTH_RATES dict keyed by GICSSector string values (e.g. "Information Technology": 0.12)
- [ ] Add `get_sector_growth_rate(sector: str) -> float` helper
- [ ] Run tests (4 PASS), commit

## Task 9: TAM - Add revenue_history to TickerDataBase

**Files:** Modify `engine/src/margin_engine/scoring/ticker_data.py`

- [ ] Add `revenue_history: list[dict] | None = None` and `sector: str | None = None`
- [ ] Run engine tests for regressions, commit

## Task 10: TAM - Wire into v3/v4 Pipelines

**Files:** Modify `v3_pipeline.py:203`, `v4_pipeline.py:329`, `cli.py`. Create `engine/tests/scoring/test_tam_wiring.py`.

- [ ] Write 3 tests: modifier differs from 1.0 with revenue data, equals 1.0 without, single data point falls back
- [ ] Replace `tam_modifier(None)` in v3_pipeline.py:203 and v4_pipeline.py:329: check revenue_history >= 2 points + sector exists, call tam_expansion_velocity with get_sector_growth_rate, pass result to tam_modifier. Fallback to tam_modifier(None).
- [ ] In cli.py: query pit_financial_snapshots income_statement JSONB, extract "revenue" per fiscal_year, deduplicate, build revenue_by_ticker dict. Pass to TickerDataBase along with Asset.sector.
- [ ] Run full test suites, commit

## Task 11: Final Verification

- [ ] Run complete engine test suite: `uv run pytest engine/tests/ -v -q` (3345+ tests)
- [ ] Run complete API test suite: `uv run pytest api/tests/ --ignore=api/tests/services/test_xbrl_parser.py -q` (2776+ tests)
- [ ] Lint: `uv run ruff check --fix . && uv run ruff format .`
- [ ] Final commit if lint produced changes
