# Tier C: New Subsystems Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Implement 6 new engine subsystems: inflection detection, Kelly position sizing, moat classification, drawdown re-screening, NLP filing analysis, and TAM expansion velocity.

**Architecture:** All pure-engine work follows the score modifier pattern from Tier B. API-layer work (C5, C1) adds new ARQ workers and DB tables. C1 introduces Claude API integration for filing analysis.

**Tech Stack:** Python 3.13, Pydantic, SQLAlchemy 2.0 + asyncpg, ARQ, Alembic, pytest + aiosqlite

**Spec:** `docs/superpowers/specs/2026-03-18-tier-c-new-subsystems-design.md`

---

## Parallelism Note

Tasks 1-8 (C4), 9-12 (C6), 13-15 (C3p1), 16-19 (C5) have **no cross-dependencies** and can be implemented in parallel by separate agents. C1 (Tasks 20-25) and C2 (Tasks 26-30) are sequential.

---

## C4: Inflection Detection (Score Modifier)

### Task 1: OpEx Deleverage Signal

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/inflection_detection.py`
- Test: `engine/tests/scoring/quantitative/test_inflection_detection.py`

**Context:** Detects OpEx/Revenue ratio declining for 2+ consecutive periods. Uses `FinancialHistory.periods` where each period has `current_income.revenue`, `current_income.cost_of_revenue`, optional `current_income.sga_expense`. Returns 0-4 points.

- [ ] **Step 1: Write failing test.** Create test file with `_make_period` helper. Write `TestOpExDeleverage` with: declining ratio scores positive, flat scores zero, single period scores zero, capped at four.
- [ ] **Step 2: Run test** `uv run pytest engine/tests/scoring/quantitative/test_inflection_detection.py::TestOpExDeleverage -v` Expected: FAIL ModuleNotFoundError
- [ ] **Step 3: Implement** `opex_deleverage_score(history)`. Helper `_opex_ratio(period)` = (cost_of_revenue + sga_expense) / revenue. Count consecutive declining ratios, score = min(total_magnitude / 0.01, 4.0). Return 0 if fewer than 2 consecutive declines.
- [ ] **Step 4: Run tests.** Expected: All PASS
- [ ] **Step 5: Commit** `feat(engine): add opex_deleverage_score inflection signal`

### Task 2: FCF Crossover Signal

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/inflection_detection.py`
- Modify: `engine/tests/scoring/quantitative/test_inflection_detection.py`

**Context:** Detects FCF turning positive after negative streak. Estimate FCF = net_income + depreciation. Score = min(prior_negative_streak_length, 3.0). Requires last 2 periods positive and at least 1 prior negative.

- [ ] **Step 1: Write failing tests.** crossover detected (score=3.0 for 3 prior negatives), always profitable (0), still negative (0), single period (0).
- [ ] **Step 2: Run test.** Expected: FAIL ImportError
- [ ] **Step 3: Implement** `fcf_crossover_score(history)`. Helper `_estimate_fcf(period)` = net_income + depreciation.
- [ ] **Step 4: Run tests.** Expected: All PASS
- [ ] **Step 5: Commit** `feat(engine): add fcf_crossover_score inflection signal`

### Task 3: Margin Expansion Signal

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/inflection_detection.py`
- Modify: `engine/tests/scoring/quantitative/test_inflection_detection.py`

**Context:** Detects gross margin expanding toward ATH. Uses `period.current_income.gross_margin`. Requires 2+ consecutive expansions and proximity to ATH (within 200bps). Score = proximity * consistency * 3.0, capped at 3.0.

- [ ] **Step 1: Write failing tests.** expanding toward ATH, flat margins (0), declining (0), insufficient data (0).
- [ ] **Step 2-4: Implement, test, commit** `feat(engine): add margin_expansion_score inflection signal`

### Task 4: Inflection Composite + Metadata

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/inflection_detection.py`
- Modify: `engine/tests/scoring/quantitative/test_inflection_detection.py`

**Context:** `inflection_score(history) -> FactorScore`. Combines opex + fcf + margin into 0-10 scale. Metadata: `opex_deleverage_detected`, `fcf_crossover_detected`, `margin_expansion_magnitude`, `periods_since_inflection`.

- [ ] **Step 1: Write failing tests.** combined score > 0, stable company scores 0.
- [ ] **Step 2-4: Implement, test, commit** `feat(engine): add inflection_score composite with metadata`

### Task 5: Inflection Modifier in score_modifiers.py

**Files:**
- Modify: `engine/src/margin_engine/scoring/score_modifiers.py`
- Modify: `engine/tests/scoring/test_score_modifiers.py`

**Context:** Maps inflection_score (0-10) to multiplier [1.0, 1.10]. Linear: 1.0 + (clamped/10.0) * 0.10. Never penalizes.

- [ ] **Step 1: Write failing tests.** score 0 -> 1.0, score 10 -> 1.10, score 5 -> 1.05.
- [ ] **Step 2: Implement** `inflection_modifier(inflection_score_value: float) -> float`
- [ ] **Step 3: Run tests, commit** `feat(engine): add inflection_modifier to score_modifiers`

### Task 6: Update apply_all_modifiers for 4th Param

**Files:**
- Modify: `engine/src/margin_engine/scoring/score_modifiers.py` (line 257: `apply_all_modifiers`)
- Modify: `engine/tests/scoring/test_score_modifiers.py`

**Context:** Currently: `(composite_score, anti_consensus, liquidity, insider)`. Add `inflection: float = 1.0`. Multiply into combined product. Clamp stays [0.75, 1.25]. Default preserves backward compat.

- [ ] **Step 1: Write tests** for 4-modifier combined + backward compat (3 args).
- [ ] **Step 2: Update function signature** and multiply inflection into combined product. Add "inflection" key to breakdown dict.
- [ ] **Step 3: Run ALL score_modifiers tests** `uv run pytest engine/tests/scoring/test_score_modifiers.py -v`
- [ ] **Step 4: Commit** `feat(engine): add inflection param to apply_all_modifiers`

### Task 7: Wire into v3 and v4 Pipelines

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_pipeline.py` (lines 20-24 imports, line 195 call)
- Modify: `engine/src/margin_engine/scoring/v4_pipeline.py` (lines 24-28 imports, line 321 call)

**Context:** Both import `anti_consensus_modifier, apply_all_modifiers, insider_signal_modifier, liquidity_modifier` from score_modifiers. Add `inflection_modifier`. Both call `apply_all_modifiers(composite_score, ac_mod, liq_mod, ins_mod)`. Before that call, add: `from margin_engine.scoring.quantitative.inflection_detection import inflection_score`, then `infl_result = inflection_score(history)`, `infl_mod = inflection_modifier(infl_result.raw_value)`, pass as 5th arg.

- [ ] **Step 1: Update v3_pipeline.py** imports and apply_all_modifiers call
- [ ] **Step 2: Update v4_pipeline.py** same pattern
- [ ] **Step 3: Run pipeline tests** `uv run pytest engine/tests/scoring/ -v`
- [ ] **Step 4: Commit** `feat(engine): wire inflection modifier into v3 and v4 pipelines`

### Task 8: Full Engine Test Suite

- [ ] **Step 1:** `uv run pytest engine/tests/ -v` Expected: All 2778+ PASS

---

## C6: Kelly Criterion Position Sizing

### Task 9: Extend Backtesting Models

**Files:**
- Modify: `engine/src/margin_engine/backtesting/models.py` (line 78: HoldingRecord, line 115: PerformanceMetrics)
- Create: `engine/tests/backtesting/test_kelly_models.py`

**Context:** HoldingRecord (line 78) has: ticker, weight, entry_price, composite_score. Add optional: `conviction_tier: str | None = None`, `exit_price: float | None = None`, `position_return: float | None = None`. New models: `PositionOutcome(ticker, conviction_tier, entry_price, exit_price, return_pct)` with `is_winner` property. `TierStats(tier, win_rate, avg_winner_return, avg_loser_return, n_positions)`. Extend PerformanceMetrics: `tier_stats: list[TierStats] | None = None`.

- [ ] **Step 1: Write failing tests** for new fields (optional defaults) and new models.
- [ ] **Step 2: Add fields and models** to models.py
- [ ] **Step 3: Run backtesting tests** `uv run pytest engine/tests/backtesting/ -v`
- [ ] **Step 4: Commit** `feat(engine): extend backtesting models for Kelly tracking`

### Task 10: Kelly Position Size Formula

**Files:**
- Create: `engine/src/margin_engine/scoring/kelly_position_sizing.py`
- Create: `engine/tests/scoring/test_kelly_position_sizing.py`

**Context:** `kelly_position_size(win_probability, expected_gain, expected_loss, kelly_fraction=0.25, max_position_pct=15.0)`. Full Kelly: f* = (p*b - q) / b where b = gain/loss. Fractional = fraction * max(0, f*) * 100. Capped. `KellyConstraints` model with max_single=15, max_top_3=50, max_sector=30, min_positions=5.

- [ ] **Step 1: Write failing tests.** Positive edge (p=0.6, b=2.0 -> 10%), negative edge (p*b < q -> 0), low win high payoff (p=0.45, b=3.0 -> positive), capped at 15%, custom fraction.
- [ ] **Step 2: Implement** kelly_position_size + KellyConstraints
- [ ] **Step 3: Run tests, commit** `feat(engine): add Kelly criterion position sizing formula`

### Task 11: Per-Position Outcome Tracking

**Files:**
- Modify: `engine/src/margin_engine/backtesting/metrics.py`
- Modify: `engine/tests/backtesting/test_metrics.py`

**Context:** Add `PerformanceCalculator.compute_tier_stats(outcomes: list[PositionOutcome]) -> list[TierStats]` as staticmethod. Groups by conviction_tier. Computes win_rate, avg_winner_return, avg_loser_return per tier. Import PositionOutcome and TierStats from models.

- [ ] **Step 1: Write failing tests.** 5 outcomes across 2 tiers -> correct stats per tier. Empty list -> empty.
- [ ] **Step 2: Implement** compute_tier_stats (use collections.defaultdict to group)
- [ ] **Step 3: Run tests, commit** `feat(engine): add compute_tier_stats for Kelly inputs`

### Task 12: Integrate Kelly into v3_position_sizing

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_position_sizing.py`
- Create: `engine/tests/scoring/test_kelly_integration.py`

**Context:** Add `kelly_position_size_or_fallback(tier, opportunity_type, tier_stats)`. Uses Kelly when tier_stats has n_positions >= 10, else falls back to `_SIZING` dict.

- [ ] **Step 1: Write failing tests.** With stats -> Kelly result, without stats -> fixed table value.
- [ ] **Step 2: Implement** kelly_position_size_or_fallback
- [ ] **Step 3: Run tests, commit** `feat(engine): integrate Kelly sizing with fallback`

---

## C3 Phase 1: Moat Source Classification

### Task 13: Switching Costs Proxy

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/moat_durability.py`
- Modify: `engine/tests/scoring/quantitative/test_moat_durability.py`

**Context:** New `_detect_switching_costs(history) -> float` (0.0-0.8 confidence). Proxy: avg SGA/Revenue > 20% across 3+ periods AND min period-over-period revenue retention > 95%. Scored separately from `_SIGNATURE_WEIGHTS` (does NOT get added to the weights dict).

- [ ] **Step 1: Write failing tests.** high SGA + stable revenue -> 0.8, low SGA -> 0.0
- [ ] **Step 2: Implement** _detect_switching_costs
- [ ] **Step 3: Run moat tests, commit** `feat(engine): add switching costs moat proxy`

### Task 14: Regulatory + Brand Moat Proxies

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/moat_durability.py`
- Modify: `engine/tests/scoring/quantitative/test_moat_durability.py`

**Context:** `_detect_regulatory_moat(sector: GICSSector) -> float`: Utilities->1.0, Financials/Healthcare->0.7, others->0.0. `_detect_brand_moat(history, sector, sector_median_gm) -> float`: sustained GM > sector_median + 15pp for 80%+ of 5+ periods -> 0.7.

- [ ] **Step 1: Write tests** for both detectors
- [ ] **Step 2: Implement** both functions
- [ ] **Step 3: Run tests, commit** `feat(engine): add regulatory and brand moat proxies`

### Task 15: Wire Metadata into moat_durability_score

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/moat_durability.py` (line 111)
- Modify: `engine/tests/scoring/quantitative/test_moat_durability.py`

**Context:** Add optional params `sector: GICSSector | None = None`, `sector_median_gm: float = 0.30` to `moat_durability_score()`. Compute proxy confidences, pick highest as primary_moat. Add to FactorScore.metadata: primary_moat, moat_confidence, secondary_moats, moat_sources_detected. Numeric score from _SIGNATURE_WEIGHTS UNCHANGED.

- [ ] **Step 1: Write failing test** (Utilities -> metadata primary_moat="regulatory")
- [ ] **Step 2: Update** moat_durability_score
- [ ] **Step 3: Run ALL moat tests** (regression: existing tests pass since sector defaults to None)
- [ ] **Step 4: Commit** `feat(engine): add moat classification metadata`

---

## C5: Drawdown Re-Screening

### Task 16: DrawdownRescreen ORM Model + Migration

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: migration

**Context:** Table `drawdown_rescreens`: id, ticker (String 10 indexed), drawdown_pct (Float), high_price (Float), current_price (Float), trigger_date (Date), prior_conviction (String 20 nullable), new_conviction (nullable), outcome (nullable), created_at (DateTime tz=True). Use idempotent migration.

- [ ] **Step 1: Add ORM model** to models.py
- [ ] **Step 2: Generate migration** `uv run alembic revision --autogenerate -m "add drawdown_rescreens table"`
- [ ] **Step 3: Apply** `uv run alembic upgrade head`
- [ ] **Step 4: Commit** `feat(api): add drawdown_rescreens table`

### Task 17: DrawdownScreener Service

**Files:**
- Create: `api/src/margin_api/services/drawdown_screener.py`
- Create: `api/tests/services/test_drawdown_screener.py`

**Context:** `DrawdownScreener` with `find_candidates(session, min_drawdown_pct=-0.20)` and `trigger_rescreening(session, candidates, arq_pool)`. Queries PitDailyPrice for 52-week high vs current. Filters: only scored universe (ScoreResponse.is_published), debounce (skip within MARGIN_DRAWDOWN_DEBOUNCE_DAYS=7), sorted by deepest drawdown, capped at MARGIN_DRAWDOWN_MAX_PER_RUN=10.

- [ ] **Step 1: Write failing tests** (mock DB data)
- [ ] **Step 2: Implement** DrawdownScreener
- [ ] **Step 3: Run tests, commit** `feat(api): add DrawdownScreener service`

### Task 18: Cron Job + rescore_ticker Worker

**Files:**
- Modify: `api/src/margin_api/workers.py`

**Context:** `rescore_ticker(ctx, ticker, trigger_reason)` per-ticker worker. Creates JobRun, calls per-ticker scoring (extract from run_scoring_v3/v4 or stub with TODO). `screen_drawdown_candidates(ctx)` daily cron 23:30 UTC. Uses DrawdownScreener, circuit breaker (>15 -> governance alert). Register both.

- [ ] **Step 1: Add rescore_ticker** following JobRun pattern at line 582
- [ ] **Step 2: Add screen_drawdown_candidates** cron
- [ ] **Step 3: Register** in WorkerSettings functions/cron lists
- [ ] **Step 4: Commit** `feat(api): add drawdown cron and rescore_ticker worker`

### Task 19: Full API Test Suite

- [ ] **Step 1:** `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`

---

## C1: NLP Pipeline

### Task 20: Filing Text + Sentiment Cache Tables

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: migration

**Context:** `filing_texts`: ticker, cik, filing_type, filing_date, period_end, business_text (Text), risk_factors_text (Text), mda_text (Text), raw_html_hash (String 64), created_at. Unique(ticker, filing_type, period_end). `filing_sentiment_cache`: filing_text_id (FK), ticker, analysis_version, prompt_hash, sentiment_value (Float), moat_signals/risk_flags/management_quality/competitive_position/segment_revenue (all JSONVariant), model_used, created_at. Unique(filing_text_id, analysis_version).

- [ ] **Step 1: Add both ORM models**
- [ ] **Step 2: Generate + apply migration**
- [ ] **Step 3: Commit** `feat(api): add filing text and sentiment cache tables`

### Task 21: Filing Text Extractor

**Files:**
- Create: `api/src/margin_api/services/edgar/text_extractor.py`
- Create: `api/tests/services/edgar/test_text_extractor.py`

**Context:** `FilingTextExtractor.extract_sections(filing_html, filing_type) -> ExtractedSections`. Section mapping: 10-K Items 1/1A/7, 10-Q Part II Item 1A / Part I Item 2. Regex section boundary detection. Returns dataclass with business, risk_factors, mda, html_hash. Cap sections at 50K chars.

- [ ] **Step 1: Write tests** with minimal HTML fixtures
- [ ] **Step 2: Implement** FilingTextExtractor
- [ ] **Step 3: Run tests, commit** `feat(api): add FilingTextExtractor`

### Task 22: NLP Analyzer Service

**Files:**
- Create: `api/src/margin_api/services/nlp_analyzer.py`
- Create: `api/tests/services/test_nlp_analyzer.py`

**Context:** `NLPAnalyzer.analyze(session, filing_text_id, ticker, mda_text, risk_text)`. Checks MARGIN_NLP_ENABLED. Uses Anthropic SDK (AsyncAnthropic). Structured prompt for JSON output. Caches in filing_sentiment_cache. Config: MARGIN_NLP_MODEL (haiku), MARGIN_NLP_TEMPERATURE (0), MARGIN_NLP_MAX_FILINGS_PER_DAY (50), MARGIN_NLP_RATE_LIMIT (10/min).

- [ ] **Step 1: Write tests** with mocked API client
- [ ] **Step 2: Implement** NLPAnalyzer
- [ ] **Step 3: Run tests, commit** `feat(api): add NLP filing analysis service`

### Task 23: Wire into EDGAR Pipeline

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Modify: `api/src/margin_api/services/edgar/daily_update.py`

**Context:** New `analyze_filing_text` worker. After XBRL parsing in daily_update.py, add text extraction and (if NLP enabled) enqueue analysis.

- [ ] **Step 1: Add** analyze_filing_text worker
- [ ] **Step 2: Wire** text extraction into daily_update.py
- [ ] **Step 3: Run tests, commit** `feat(api): wire NLP analysis into EDGAR pipeline`

### Task 24: Wire NLP into Anti-Consensus Modifier

**Files:**
- Modify: `engine/src/margin_engine/scoring/score_modifiers.py` (line 192)
- Modify: `engine/tests/scoring/test_score_modifiers.py`

**Context:** `anti_consensus_modifier` currently: 4 params, weights 40/30/30. Add optional `nlp_sentiment: float | None = None`. When present: 30/25/25/20 weights with NLP signal (normalize from -5..+5 to -1..+1). When None: original 40/30/30.

- [ ] **Step 1: Write failing tests** (with NLP vs without differ, None backward compat)
- [ ] **Step 2: Update** anti_consensus_modifier
- [ ] **Step 3: Run tests, commit** `feat(engine): add NLP sentiment to anti_consensus_modifier`

### Task 25: C1 Full Verification

- [ ] **Step 1:** `uv run pytest engine/tests/ -v`
- [ ] **Step 2:** `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`

---

## C2: TAM Expansion Velocity

### Task 26: Industry Growth Rates Config

**Files:**
- Create: `engine/src/margin_engine/config/industry_growth_rates.py`
- Create: `engine/tests/config/test_industry_growth_rates.py`

**Context:** `IndustryGrowthRate(rate, last_updated)` Pydantic model. Dict of ~20 sub-industries. `get_industry_growth_rate(industry)` returns rate or default 0.05.

- [ ] **Step 1: Write failing tests** (known industry, unknown fallback, all positive)
- [ ] **Step 2: Implement** config module
- [ ] **Step 3: Run tests, commit** `feat(engine): add industry growth rates config`

### Task 27: TAM Expansion Factor

**Files:**
- Create: `engine/src/margin_engine/scoring/quantitative/tam_expansion.py`
- Create: `engine/tests/scoring/quantitative/test_tam_expansion.py`

**Context:** `tam_expansion_velocity(segment_revenues, industry_growth_rate) -> FactorScore | None`. Velocity = company_cagr / max(industry_rate, 0.01). Score = min(velocity/2.0, 1.0) * 10. None if < 2 data points.

- [ ] **Step 1: Write failing tests** (gaining share, losing share, insufficient data, zero industry)
- [ ] **Step 2: Implement** tam_expansion_velocity
- [ ] **Step 3: Run tests, commit** `feat(engine): add TAM expansion velocity factor`

### Task 28: TAM Modifier + Pipeline Wiring

**Files:**
- Modify: `engine/src/margin_engine/scoring/score_modifiers.py`
- Modify: `engine/src/margin_engine/scoring/v3_pipeline.py`
- Modify: `engine/src/margin_engine/scoring/v4_pipeline.py`
- Modify: `engine/tests/scoring/test_score_modifiers.py`

**Context:** `tam_modifier(tam_score_value: float | None) -> float`. Maps 0-10 to [0.95, 1.10], center 5->1.0. None->1.0. Update apply_all_modifiers for 5th param `tam: float = 1.0`. Wire into pipelines.

- [ ] **Step 1: Write tests** for tam_modifier and 5-param apply_all_modifiers
- [ ] **Step 2: Implement** tam_modifier, update apply_all_modifiers
- [ ] **Step 3: Wire** into v3 and v4 pipelines
- [ ] **Step 4: Run tests, commit** `feat(engine): add TAM modifier and wire into pipelines`

### Task 29: SegmentRevenueHistory Table

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: migration

**Context:** Table: ticker (String 10 indexed), filing_date (Date), segment_name (String 200), segment_type (String 20), revenue (Float), source (String 10), created_at. Unique(ticker, filing_date, segment_name).

- [ ] **Step 1: Add ORM model, generate + apply migration**
- [ ] **Step 2: Commit** `feat(api): add segment_revenue_history table`

### Task 30: Final Verification

- [ ] **Step 1:** `uv run pytest engine/tests/ -v` All PASS
- [ ] **Step 2:** `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py` All PASS
- [ ] **Step 3:** `uv run ruff check --fix . && uv run ruff format .`
- [ ] **Step 4: Final commit** `chore: lint fixes for Tier C implementation`
