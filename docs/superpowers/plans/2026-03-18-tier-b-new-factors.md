# Tier B: New Factors & Data — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan. Steps use checkbox syntax for tracking.

**Goal:** Add 3 post-composite score modifiers (anti-consensus, liquidity, insider signal) and remove Financials/Real Estate sector exclusion with adaptive scoring.

**Architecture:** All new signals are post-composite multipliers (0.75-1.25 combined range) applied after the v3/v4 cascade. B2 (sector exclusion removal) is structural — it changes the universe, filters, and cascade profitability computation. B2 must be implemented first; B1, B3, B4 are independent and parallelizable.

**Tech:** Python 3.13+, Pydantic, pytest, Finnhub SDK, EDGAR XML parsing, PostgreSQL, Alembic, ARQ

**Spec:** `docs/superpowers/specs/2026-03-18-tier-b-new-factors-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `engine/src/margin_engine/scoring/score_modifiers.py` | All 3 modifier functions + `apply_all_modifiers()` + `compute_fundamental_trajectory()` |
| `engine/src/margin_engine/scoring/sector_adapters.py` | `SectorAdapter` — sector-aware profitability metric selection |
| `engine/tests/scoring/test_score_modifiers.py` | Tests for all modifier functions |
| `engine/tests/scoring/test_sector_adapters.py` | Tests for sector adapter + percentile ranking |
| `api/src/margin_api/services/edgar/form4_parser.py` | SEC Form 4 XML parsing |
| `api/src/margin_api/services/insider_service.py` | `is_first_purchase()` DB query |
| `api/tests/services/test_form4_parser.py` | Form 4 parser tests |
| `api/tests/services/test_insider_service.py` | First-purchase query tests |

### Modified Files

| File | Change Summary |
|------|---------------|
| `engine/src/margin_engine/models/financial.py` | Remove `is_excluded_v1`, `is_excluded`; extend `InsiderTransaction` |
| `engine/src/margin_engine/config/filter_config.py` | Lower market cap default, add exempt sectors, remove `excluded_sectors` from `LiquidityConfig` |
| `engine/src/margin_engine/scoring/filters/liquidity.py` | Remove `_EXCLUDED_SECTORS`, remove exclusion check blocks |
| `engine/src/margin_engine/scoring/v3_cascade.py` | Use `SectorAdapter` for Financials/RE ROIC computation |
| `engine/src/margin_engine/config/v3_scoring_config.py` | Add `SectorPercentileConfig` |
| `engine/src/margin_engine/scoring/v3_pipeline.py` | Add fields to `TickerV3Data`, wire modifiers |
| `engine/src/margin_engine/scoring/v4_pipeline.py` | Add fields to `TickerV4Data`, wire modifiers |
| `engine/src/margin_engine/ingestion/providers/finnhub_provider.py` | Add `fetch_short_interest()`, `fetch_analyst_recommendations()` |
| `engine/src/margin_engine/scoring/quantitative/insider_cluster.py` | Add drawdown, magnitude, first-buy params |
| `api/src/margin_api/cli.py` | Remove `excluded_sectors` from universe builder |
| `api/src/margin_api/db/models.py` | New tables: `sentiment_signals`, `insider_transaction_history` |
| `api/src/margin_api/workers.py` | New ARQ jobs |

---

## Phase 1: B2 — Sector Exclusion Removal (must be first)

### Task 1: Remove sector exclusion from filter config and models

**Files:** Modify `filter_config.py:40-46,61-64,87-92,95-121,134-159`, `financial.py:30-32,222-224`. Test `test_filter_config.py`, `test_models.py`.

- [ ] Write failing test: `LiquidityConfig` should not have `excluded_sectors` field
- [ ] Run test — expected FAIL
- [ ] Update `MarketCapMinimum`: default 300M to 100M, add `financials=500M`, `real_estate=1B`
- [ ] Remove `excluded_sectors` from `LiquidityConfig`
- [ ] Add `exempt_sectors` to `AltmanConfig`: `["Utilities", "Financials", "Real Estate"]`
- [ ] Add `exempt_sectors` to `FcfDistressConfig`: `["Financials", "Real Estate"]`
- [ ] Add `exempt_sectors` to `InterestCoverageConfig`: `["Financials"]`
- [ ] Add `exempt_sectors` to `CurrentRatioConfig`: `["Financials"]`
- [ ] Remove `is_excluded_v1` from `GICSSector`, `is_excluded` from `AssetProfile`
- [ ] Fix tests: remove `is_excluded` assertions in `test_models.py:311,322,333`, `test_golden_fixture.py:51`
- [ ] Run tests and commit

### Task 2: Remove sector exclusion from liquidity filter

**Files:** Modify `liquidity.py:40-58,127-142,239-248`. Test `test_liquidity.py`.

- [ ] Write failing test: `GICSSector.FINANCIALS` with $500B market cap passes `liquidity_check()`
- [ ] Run test — expected FAIL
- [ ] Remove `_EXCLUDED_SECTORS` frozenset (lines 53-58)
- [ ] Remove sector exclusion block in `liquidity_check()` (lines 127-142)
- [ ] Remove sector exclusion block in `liquidity_check_v2()` (lines 239-248)
- [ ] Fix existing tests that assert Financials/RE exclusion
- [ ] Run tests and commit

### Task 3: Add sector adapters with percentile normalization

**Files:** Create `sector_adapters.py`, `test_sector_adapters.py`. Modify `v3_scoring_config.py`.

- [ ] Write failing tests: ROE for Financials, FFO proxy for RE, ROIC for Tech. Percentile ranking tests.
- [ ] Run tests — expected FAIL
- [ ] Implement `SectorAdapter` class with `profitability_metric()`, `metric_name()`, `needs_percentile_gates()`
- [ ] Implement `sector_percentile_rank()` function
- [ ] Add `SectorPercentileConfig` to `v3_scoring_config.py`
- [ ] Run tests and commit

### Task 4: Wire sector adapters into v3_cascade.py

**Files:** Modify `v3_cascade.py:88-103,204-244`. Test `test_v3_cascade.py`.

- [ ] Write failing test: Financials ticker with high ROE produces valid cascade result
- [ ] Add `universe_profitability_metrics` and `percentile_config` to `TrackAInputs`/`TrackBInputs`
- [ ] Replace inline ROIC in Gate 2 with `SectorAdapter`. Financials/RE: percentile gate. Others: absolute.
- [ ] Same for Track B `_current_roic()` and `_is_roic_improving()`
- [ ] Run tests and commit

### Task 5: Remove sector exclusion from universe builder

**Files:** Modify `cli.py:1765`.

- [ ] Change `excluded_sectors` list to empty
- [ ] Update description string and log messages
- [ ] Commit

### Task 6: Wire filter exemptions for downstream filters

**Files:** Modify `fcf_distress.py`, `beneish.py`, `interest_coverage.py`, `current_ratio.py`.

- [ ] Write failing tests: each filter exempts Financials/RE per config
- [ ] Add `exempt_sectors` to `BeneishConfig`
- [ ] Add sector exemption check to each filter function
- [ ] Run tests and commit

---

## Phase 2: Score Modifiers Framework

### Task 7: Create score_modifiers.py with apply_all_modifiers

**Files:** Create `score_modifiers.py`, `test_score_modifiers.py`.

- [ ] Write failing tests: neutral=no change; combined clamped [0.75, 1.25]; breakdown keys
- [ ] Implement `apply_all_modifiers()` returning `(modified_score, breakdown_dict)`
- [ ] Run tests and commit

---

## Phase 3: B3 — Liquidity Modifier

### Task 8: Implement liquidity_modifier

**Files:** Modify `score_modifiers.py`. Test `test_score_modifiers.py`.

- [ ] Write failing tests: mega-cap=1.0, small-cap penalized, micro-cap=0.85, never boosts, range [0.85, 1.0]
- [ ] Implement: log-scaled cap tier + turnover adequacy + stability, mapped to 0.85-1.00
- [ ] Run tests and commit

---

## Phase 4: B1 — Anti-Consensus Modifier

### Task 9: Extend FinnhubProvider

**Files:** Modify `finnhub_provider.py`, `types.py`. Test `test_finnhub_provider.py`.

- [ ] Write failing tests for `fetch_short_interest()` and `fetch_analyst_recommendations()`
- [ ] Add `SHORT_INTEREST` and `ANALYST` to `DataCategory` enum
- [ ] Implement both methods following existing pattern
- [ ] Run tests and commit

### Task 10: Implement anti_consensus_modifier and compute_fundamental_trajectory

**Files:** Modify `score_modifiers.py`. Test `test_score_modifiers.py`.

- [ ] Write failing tests: strong signal >1.05, bearish <1.0, neutral=1.0, range [0.90, 1.15]. Trajectory tests.
- [ ] Implement `compute_fundamental_trajectory(history)`: ROIC+GM trends, return 0-1
- [ ] Implement `anti_consensus_modifier()`: 3 weighted components, return 0.90-1.15
- [ ] Run tests and commit

### Task 11: Add sentiment_signals DB table and ingestion job

**Files:** Modify `db/models.py`, `workers.py`. Create Alembic migration.

- [ ] Add `SentimentSignal` ORM model
- [ ] Generate migration
- [ ] Add `ingest_sentiment_signals` worker stub at 23:45 UTC
- [ ] Commit

---

## Phase 5: B4 — Insider Signal Upgrade

### Task 12: Extend InsiderTransaction model and insider_cluster_score

**Files:** Modify `financial.py:188-197`, `insider_cluster.py`. Test `test_insider_cluster.py`.

- [ ] Write failing tests: drawdown 1.5x, magnitude opt-in, first-buy 10x, backward compat
- [ ] Add `insider_cik` and `is_first_purchase` to `InsiderTransaction`
- [ ] Add `price_drawdown_pct` and `apply_magnitude` params to `insider_cluster_score()`
- [ ] Implement `_magnitude_boost()` helper
- [ ] Run tests and commit

### Task 13: Implement insider_signal_modifier

**Files:** Modify `score_modifiers.py`. Test `test_score_modifiers.py`.

- [ ] Write failing tests: no cluster=1.0, cluster=1.05, drawdown/magnitude/first-buy bonuses, max 1.15
- [ ] Implement additive bonuses from 1.05 base, capped at 1.15
- [ ] Run tests and commit

### Task 14: Add EDGAR Form 4 parser and insider_transaction_history table

**Files:** Create `form4_parser.py`, `test_form4_parser.py`. Modify `db/models.py`. Create migration.

- [ ] Write failing test with Form 4 XML fixture
- [ ] Implement `Form4Parser.parse()` for purchase transactions
- [ ] Add `InsiderTransactionHistory` ORM model with BigInteger shares
- [ ] Generate migration
- [ ] Run tests and commit

### Task 15: Add insider_service.py and Form 4 worker jobs

**Files:** Create `insider_service.py`, `test_insider_service.py`. Modify `workers.py`.

- [ ] Write failing tests for `is_first_purchase()`
- [ ] Implement DB query against `insider_transaction_history`
- [ ] Add Form 4 worker stubs (backfill + daily at 23:30 UTC)
- [ ] Run tests and commit

---

## Phase 6: Pipeline Wiring

### Task 16: Wire modifiers into v3_pipeline.py and v4_pipeline.py

**Files:** Modify `v3_pipeline.py:37-54`, `v4_pipeline.py:44-70`. Test `test_v3_pipeline.py`.

- [ ] Add modifier fields to `TickerV3Data` and `TickerV4Data` (all with neutral defaults)
- [ ] After cascade, compute 3 modifiers and call `apply_all_modifiers()`. Store on result metadata.
- [ ] Write test: non-neutral inputs produce modified score
- [ ] Run pipeline tests and commit

### Task 17: Run full test suite and fix regressions

- [ ] Run engine tests: expect ~2778+ PASS
- [ ] Run API tests (ignoring xbrl_parser): expect ~1699+ PASS
- [ ] Fix regressions from removed exclusion properties, changed market cap default, new fields
- [ ] Run lint
- [ ] Commit if fixes needed
