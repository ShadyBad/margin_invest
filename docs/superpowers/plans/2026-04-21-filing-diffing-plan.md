# Filing Diffing Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan. Steps use checkbox syntax for tracking.

**Goal:** Build a semantic diffing pipeline that compares consecutive 10-K Item 1A sections, classifies material changes with Claude Haiku 4.5, and surfaces a delta signal on the asset detail page.

**Architecture:** Extends the existing EDGAR pipeline. Consumes `FilingText` rows from `text_extractor.py`. New `services/risk_diffing/` module handles chunking, Voyage AI embedding, cosine similarity matching, and Claude analysis. Three new PostgreSQL tables. Exposed via API endpoint and a frontend card component.

**Tech Stack:** Python 3.13, SQLAlchemy 2.0, asyncpg, Voyage AI SDK, Anthropic SDK (Haiku 4.5), ARQ workers, FastAPI, Next.js 16, React 19, Vitest

**Spec:** `docs/superpowers/specs/2026-04-21-filing-diffing-design.md`

---

## Overview

14 tasks, each following TDD. The full task breakdown with complete code, exact file paths, test commands, and expected output was presented during the brainstorming session. Below is the structural summary. When executing, refer to the detailed task content from the session.

## File Structure

### New Files (API)

```
services/risk_diffing/
    __init__.py
    config.py           -- env var tunables (thresholds, models, versions)
    chunker.py          -- paragraph splitting, normalization, SHA-256 fingerprinting
    embedder.py         -- Voyage AI batch embedding, cache read/write
    diff_engine.py      -- cosine similarity matrix, change classification
    risk_analyzer.py    -- Claude prompt construction, caching, LLM call logging
    pipeline.py         -- end to end orchestration (single ticker + batch)

schemas/risk_diffing.py -- Pydantic response schemas
routes/risk_diffing.py  -- GET /api/v1/analytics/risk_factors/{ticker}
alembic/versions/       -- migration for 3 new tables
```

### New Files (Tests)

```
tests/services/risk_diffing/
    test_chunker.py       -- 9 tests: splitting, merging, boilerplate, hashing
    test_embedder.py      -- 5 tests: batching, cache hits/misses
    test_diff_engine.py   -- 6 tests: similarity, NEW/REMOVED/MODIFIED/unchanged
    test_risk_analyzer.py -- 7 tests: prompt building, JSON parsing, LLM logging
    test_pipeline.py      -- 3 tests: skip logic, full flow with mocks
tests/routes/
    test_risk_diffing.py  -- 2 tests: 404 and success response
```

### New Files (Evals)

```
evals/risk_factor_diffing/
    golden_set.jsonl    -- 5 seeded cases (SVB, Enron, WorldCom, Wirecard, Luckin)
    runner.py           -- precision, recall, severity correlation, regression gates
    conftest.py
    runs/               -- gitignored, historical assessment results
```

### New Files (Frontend)

```
web/src/lib/api/risk_diffing.ts          -- API client function
web/src/components/risk_delta/
    RiskDeltaCard.tsx                     -- main card component
    SeverityPill.tsx                      -- color coded severity badge (1-3 green, 4-6 yellow, 7-8 orange, 9-10 red)
    ChangeRow.tsx                         -- collapsible material change row
    __tests__/RiskDeltaCard.test.tsx      -- 6 Vitest component tests
```

### Modified Files

| File | Change |
|---|---|
| `api/src/margin_api/db/models.py` | Add RiskFactorAnalysis, RiskFactorEmbedding, LLMCallLog models (after line ~1427) |
| `api/src/margin_api/services/edgar/text_extractor.py` | ToC false match fix in `_find_section_boundaries`, additional Item 1A header patterns |
| `api/src/margin_api/workers.py` | Register `diff_risk_factors`, `orchestrate_risk_diffing`, add Sunday 04:00 UTC cron |
| `api/src/margin_api/app.py` | `include_router(risk_diffing_router)` (line ~177) |
| `web/src/components/asset-detail/asset-detail-view.tsx` | Add `<RiskDeltaCard ticker={ticker} />` after Institutional/Model grid (line ~221) |

---

## Tasks

### Task 1: Config Module
- [ ] Create `services/risk_diffing/__init__.py` and `config.py`
- [ ] Config reads all tunables from env vars with defaults: MARGIN_RISK_DIFF_ENABLED, MARGIN_VOYAGE_CREDENTIAL, similarity threshold (0.85), unchanged threshold (0.95), length change threshold (0.20), prompt version, max concurrency (4), batch size (50)
- [ ] Constants: EMBEDDING_DIMENSIONS=1024, EMBEDDING_BATCH_SIZE=128, MIN_CHUNK_CHARS=100
- [ ] Commit

### Task 2: Database Models and Migration
- [ ] Add RiskFactorAnalysis model: ticker, filing_text_id (FK), prior_filing_text_id (FK), material_changes (JSONB), overall_risk_delta_score, model_confidence, analysis_tokens_used, analysis_cost_usd, prompt_version, embedding_model, analysis_model, created_at. Unique: (ticker, filing_text_id, prompt_version)
- [ ] Add RiskFactorEmbedding model: filing_text_id (FK), chunk_index, chunk_text_hash, embedding (JSONVariant for SQLite compat), embedding_model, created_at. Unique: (filing_text_id, chunk_index)
- [ ] Add LLMCallLog model: service, ticker, model, prompt_version, input_hash, input_tokens, output_tokens, cost_usd, latency_ms, response_json (JSONB), error, created_at. Index: (service, prompt_version, created_at)
- [ ] Generate and apply Alembic migration. Check for multiple heads.
- [ ] Commit

### Task 3: Paragraph Chunker (TDD)
- [ ] Write 9 failing tests: double newline splitting, short fragment merging (<100 chars), boilerplate preamble removal, sequential indices, SHA-256 hashing, whitespace normalization, None/empty input
- [ ] Run tests, verify they fail
- [ ] Implement `chunker.py`: `chunk_risk_factors(text) -> list[RiskChunk]` where RiskChunk is a frozen dataclass with index, text, text_hash
- [ ] Run tests, verify all pass
- [ ] Commit

### Task 4: Voyage AI Embedder (TDD)
- [ ] Install `voyageai` dependency: `uv add voyageai --package margin-api`
- [ ] Write 5 failing tests: returns embeddings for all chunks, batches at 128, empty input, cache miss returns empty dict, store roundtrip
- [ ] Implement `embedder.py`: `embed_chunks(chunks) -> list[list[float]]`, `get_cached_embeddings(session, filing_text_id) -> dict`, `store_embeddings(session, ...)`
- [ ] Run tests, verify all pass
- [ ] Commit

### Task 5: Diff Engine (TDD)
- [ ] Verify numpy is available (likely transitive dep), install if needed
- [ ] Write 6 failing tests: identical vectors sim=1, orthogonal sim=0, matrix dimensions, NEW classification, REMOVED classification, MODIFIED classification, unchanged skipped, empty input
- [ ] Implement `diff_engine.py`: `compute_similarity_matrix(old, new) -> np.ndarray`, `classify_changes(...) -> list[ChangeCandidate]`. Greedy matching sorted by similarity descending.
- [ ] Run tests, verify all pass
- [ ] Commit

### Task 6: Claude Analyzer (TDD)
- [ ] Write 7 failing tests: build_user_prompt includes NEW/REMOVED/MODIFIED, analyze returns structured result, returns None on empty, logs to LLM call log, system prompt contains severity guide and schema
- [ ] Implement `risk_analyzer.py`: SYSTEM_PROMPT with severity calibration (1-3 routine, 4-6 meaningful, 7-8 material, 9-10 existential) and 3 few-shot examples. `build_user_prompt(ticker, candidates)`. `analyze_material_changes(session, ticker, candidates) -> dict`. Uses `cache_control: ephemeral` on system message for prompt caching. Logs every call to LLMCallLog. Cost: Haiku input $1/MTok, cached $0.10/MTok, output $5/MTok.
- [ ] Run tests, verify all pass
- [ ] Commit

### Task 7: Pipeline Orchestrator (TDD)
- [ ] Write 3 failing tests: skips fewer than 2 filings, skips None text, processes successfully with mocks
- [ ] Implement `pipeline.py`: `diff_single_ticker(session, ticker) -> PipelineResult`. Loads 2 most recent 10-K FilingText rows, chunks both, embeds (with cache), classifies changes, analyzes with Claude if material, stores RiskFactorAnalysis row.
- [ ] Run tests, verify all pass
- [ ] Commit

### Task 8: Text Extractor Improvements
- [ ] Replace `_find_section_boundaries` to skip ToC matches (first 10% of document). Use `re.finditer` to find all matches, prefer first past ToC cutoff, fallback to first match.
- [ ] Broaden Item 1A pattern: `r"item\\s*1\\s*a[\\s.:,\\-]+\\s*risk\\s*factors"`
- [ ] Run existing tests to check for regressions
- [ ] Commit

### Task 9: API Endpoint (TDD)
- [ ] Create `schemas/risk_diffing.py`: MaterialChangeResponse, RiskFactorAnalysisResponse (Pydantic)
- [ ] Create `routes/risk_diffing.py`: GET /api/v1/analytics/risk_factors/{ticker} with include_verbatim query param
- [ ] Register router in `app.py`
- [ ] Write 2 route tests: 404 when no analysis, 200 with correct shape
- [ ] Run tests, verify pass
- [ ] Commit

### Task 10: Worker Integration
- [ ] Add `diff_risk_factors(ctx, tickers)` worker function (lazy imports, feature gated)
- [ ] Add `orchestrate_risk_diffing(ctx)` orchestrator (loads universe, batches of 50, enqueues jobs)
- [ ] Register in WorkerSettings.functions list
- [ ] Add weekly cron: Sunday 04:00 UTC, timeout 7200s
- [ ] Smoke test imports
- [ ] Commit

### Task 11: Eval Harness
- [ ] Create `evals/risk_factor_diffing/` directory with .gitignore for runs/
- [ ] Create `golden_set.jsonl` with 5 seeded case templates (SVB, Enron, WorldCom, Wirecard, Luckin). Each has case_id, ticker, description, current/prior filing text (PLACEHOLDER for now), expected_changes with must_detect + min_severity, outcome with event + stock_impact_pct
- [ ] Create `runner.py`: load_golden_set(), evaluate_case(), compute_metrics() (precision, recall, severity correlation via Spearman), save_run(), load_prior_run() for regression comparison. Regression gate: FAIL if precision or recall drops >5%.
- [ ] Commit

### Task 12: Frontend Components
- [ ] Create `web/src/lib/api/risk_diffing.ts` with getRiskFactorAnalysis() using apiFetch
- [ ] Create SeverityPill.tsx: color coded badge (green/yellow/orange/red by severity range)
- [ ] Create ChangeRow.tsx: collapsible row with change_type badge, topic, SeverityPill, expandable summary
- [ ] Create RiskDeltaCard.tsx: loading/empty/data states, delta score gauge, sorted changes list
- [ ] Add `<RiskDeltaCard ticker={{ticker}} />` to asset-detail-view.tsx (outside showScoreView guard)
- [ ] Commit

### Task 13: Frontend Tests
- [ ] Write 6 Vitest tests: loading state, empty state (null data), renders delta score and changes, sorts by severity descending, expands change row on click, shows "no material changes" when empty list
- [ ] Run tests, verify all pass
- [ ] Commit

### Task 14: Integration Smoke Test
- [ ] Run full Python test suite (api/tests/) and verify no regressions
- [ ] Run full frontend test suite (web/) and verify no regressions
- [ ] Run linters (ruff + ESLint)
- [ ] Verify all module imports work
- [ ] Commit any lint fixes

---

## Dependencies Between Tasks

```
Task 1 (config) ─────┐
                      ├─> Task 3 (chunker)
Task 2 (models) ─────┤   Task 4 (embedder)
                      │   Task 5 (diff engine)
                      │   Task 6 (analyzer)
                      │        │
                      └────────┴─> Task 7 (pipeline)
                                       │
Task 8 (extractor) ───────────────────>│
                                       │
                                   Task 9 (API)
                                   Task 10 (worker)
                                   Task 11 (eval)
                                   Task 12 (frontend)
                                   Task 13 (frontend tests)
                                   Task 14 (smoke test)
```

Tasks 1 and 2 must go first. Tasks 3-6 can be parallelized (they depend on 1-2 but not each other). Task 7 depends on 3-6. Tasks 8-13 can proceed after 7. Task 14 is always last.
