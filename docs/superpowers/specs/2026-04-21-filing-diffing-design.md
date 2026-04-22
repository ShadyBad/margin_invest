# Risk Factor Diffing Pipeline — Design Spec

**Date:** 2026-04-21
**Status:** Approved
**Author:** Brandon + Claude

## Mission

For every ticker in the universe, pull the current and prior 10-K filings, extract Item 1A (Risk Factors) from both, compute semantic diffs using Voyage AI embeddings, and classify material changes with Claude Haiku 4.5 — producing a severity scored risk delta signal.

This is the first signal in the proprietary filing analysis stack. It ships as a **standalone overlay** (not integrated into composite scoring) until the evaluation harness validates predictive value.

## Architecture Overview

The pipeline extends the existing EDGAR infrastructure. It consumes `FilingText` rows that the existing extraction pipeline already produces — no new EDGAR fetching or HTML parsing.

```
[Existing] daily_pit_update / edgar backfill
    -> FilingText rows (risk_factors_text already extracted)

[New] risk_diff_pipeline (ARQ job, weekly Sunday 04:00 UTC)
    |-- For each ticker, load current + prior 10-K FilingText rows
    |-- Chunk risk_factors_text into individual paragraphs
    |-- Embed all paragraphs via Voyage AI (voyage-finance-2, 1024 dims)
    |-- Cosine similarity matching to pair old <-> new paragraphs
    |-- Classify: NEW, REMOVED, EXPANDED, SOFTENED
    |-- Send material changes to Claude Haiku 4.5 (prompt caching)
    |       -> structured JSON per output schema
    |-- Store result in risk_factor_analyses table
    |-- Log LLM call to llm_call_log table
    '-- Expose via GET /analytics/risk_factors/{ticker}
```

## Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Storage | PostgreSQL (no Supabase) | Consistent with existing stack; ~3GB for 6,000 filings is well within PG comfort zone |
| Embedding provider | Voyage AI (voyage-finance-2) | Purpose built for financial text; 13x cheaper than OpenAI embeddings |
| Analysis model | Claude Haiku 4.5 + prompt caching | Single model, ~$0.014/filing, well under $0.15 target. Assessment harness is safety net |
| Observability | PostgreSQL llm_call_log table | No Langfuse dependency; same auditability, queryable with SQL |
| Composite integration | Standalone overlay (v1) | Signal must prove predictive value via assessment harness before affecting rankings |
| Existing code | Extend, don't duplicate | Improve existing text_extractor.py; consume existing FilingText rows |

## Paragraph Chunking

Risk Factors sections follow a consistent structure: bold/italic heading followed by explanatory paragraphs.

**Chunking rules:**
1. Split on double newline boundaries (paragraph breaks)
2. Merge short fragments (under 100 chars) into the preceding chunk (continuation paragraphs)
3. Drop boilerplate preamble ("In addition to the other information..." intro)
4. Each chunk gets a normalized fingerprint (lowercased, whitespace collapsed SHA-256) for deduplication

## Embedding and Matching

- Embed all chunks from both years in a single Voyage AI batch call (voyage-finance-2, 1024 dimensions)
- Build cosine similarity matrix: each old chunk vs each new chunk
- Matching thresholds:
  - Above 0.95: unchanged, skip entirely
  - Between 0.85 and 0.95 (or greater than 20% length change): candidate for EXPANDED or SOFTENED, sent to Claude
  - Below 0.85 (new chunk, no match in prior): change_type is NEW
  - Below 0.85 (old chunk, no match in current): change_type is REMOVED
- Threshold of 0.85 is configurable via MARGIN_RISK_DIFF_SIMILARITY_THRESHOLD env var
- Voyage API calls batched at 128 chunks per request

## Claude Analysis

### Prompt Structure

**System prompt (~1,500 tokens, cached across all filings in a batch run):**
- Role definition: SEC filing specialist
- Output schema specification
- Severity calibration guide:
  - 1 to 3: Routine language updates, regulatory boilerplate changes
  - 4 to 6: Meaningful new disclosures (new market exposure, litigation, customer concentration)
  - 7 to 8: Material with potential financial impact (covenant violations, going concern language, regulatory investigations)
  - 9 to 10: Existential (fraud disclosure, imminent insolvency, SEC investigation)
- 3 few shot examples anchoring the severity scale

**User prompt (variable, ~2 to 8K tokens):**
- Only the material change candidates (pre filtered by diff engine)
- Each candidate includes old paragraph, new paragraph, and change type from embedding match

**Prompt caching:**
System prompt is the `system` parameter in the Anthropic API call. Identical across all filings in a batch, so 2,999 of 3,000 calls hit the cache. Cached prefix costs $0.10/MTok vs $1.00/MTok uncached.

**Prompt versioning:**
Version string (e.g., risk_diff_v1) stored on every risk_factor_analyses row and every llm_call_log row. Assessment harness compares results across versions.

### Output Schema

```json
{
  "ticker": "string",
  "filing_accession": "string",
  "comparison_prior_accession": "string",
  "material_changes": [
    {
      "change_type": "new | removed | expanded | softened",
      "topic": "string",
      "severity": "1 to 10 integer",
      "summary_50_words": "string",
      "verbatim_new_text": "string",
      "verbatim_old_text": "string or null"
    }
  ],
  "overall_risk_delta_score": "negative 10.0 to positive 10.0 float",
  "model_confidence": "0.0 to 1.0 float",
  "analysis_tokens_used": "integer",
  "analysis_cost_usd": "float"
}
```

### Cost Estimate

| Component | Per Filing | Full Universe (3,000) |
|---|---|---|
| Cached system prompt | $0.00015 | $0.45 |
| User prompt (change candidates) | $0.004 | $12.00 |
| Output tokens | $0.01 | $30.00 |
| Voyage embeddings | $0.005 | $15.00 |
| **Total** | **~$0.019** | **~$57** |

## Database Schema

### risk_factor_analyses

Primary output table.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL | PK |
| ticker | VARCHAR(10) | NOT NULL, indexed |
| filing_text_id | INTEGER | FK to filing_texts.id (current 10-K) |
| prior_filing_text_id | INTEGER | FK to filing_texts.id (prior 10-K) |
| filing_accession | VARCHAR(25) | |
| prior_filing_accession | VARCHAR(25) | |
| material_changes | JSONB | Array of change objects |
| overall_risk_delta_score | FLOAT | negative 10.0 to positive 10.0 |
| model_confidence | FLOAT | 0.0 to 1.0 |
| analysis_tokens_used | INTEGER | |
| analysis_cost_usd | FLOAT | |
| prompt_version | VARCHAR(20) | |
| embedding_model | VARCHAR(50) | voyage-finance-2 |
| analysis_model | VARCHAR(50) | claude-haiku-4-5-20251001 |
| created_at | TIMESTAMPTZ | default now() |

Unique constraint: (ticker, filing_text_id, prompt_version)

material_changes is JSONB (not normalized rows) because a single filing typically has 3 to 15 changes, the frontend reads the whole set at once, and it avoids a join heavy schema.

### risk_factor_embeddings

Cached chunk embeddings to avoid re-embedding unchanged filings.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL | PK |
| filing_text_id | INTEGER | FK to filing_texts.id |
| chunk_index | INTEGER | Position in section |
| chunk_text_hash | VARCHAR(64) | SHA-256 of normalized text |
| embedding | VECTOR(1024) | pgvector, voyage-finance-2 output |
| embedding_model | VARCHAR(50) | |
| created_at | TIMESTAMPTZ | |

Unique constraint: (filing_text_id, chunk_index)

Requires CREATE EXTENSION IF NOT EXISTS vector (pgvector). Available on Railway PostgreSQL. Alembic migration enables extension idempotently. Fallback if pgvector unavailable: store as JSONB float array, compute cosine similarity in Python.

### llm_call_log

Shared observability table for all LLM calls (this pipeline and existing NLP analyzer).

| Column | Type | Notes |
|---|---|---|
| id | SERIAL | PK |
| service | VARCHAR(50) | risk_diffing, nlp_analyzer, etc. |
| ticker | VARCHAR(10) | nullable |
| model | VARCHAR(50) | |
| prompt_version | VARCHAR(20) | |
| input_hash | VARCHAR(64) | SHA-256 of full prompt |
| input_tokens | INTEGER | |
| output_tokens | INTEGER | |
| cost_usd | FLOAT | |
| latency_ms | INTEGER | |
| response_json | JSONB | nullable, for debugging |
| error | TEXT | nullable |
| created_at | TIMESTAMPTZ | default now() |

Index: (service, prompt_version, created_at)

## Extractor Improvements

Targeted fixes to existing services/edgar/text_extractor.py for the 95% S&P 500 accuracy target:

1. **Table of contents false matches**: Skip Item 1A matches in the first 10% of the document, or require minimum gap between ToC and real section header
2. **Variant formatting**: Add patterns for "ITEM 1A.", "Item 1A --", "Item 1A:", mixed casing
3. **Missing Item 1B boundary**: Already handled — extractor falls back to Item 2 (properties) as end boundary
4. **Inline styled headers**: Already handled — HTML is stripped before regex matching

These are amendments to _10K_SECTION_PATTERNS and _find_section_boundaries, not a rewrite.

## Pipeline Orchestration

```
diff_risk_factors_batch(tickers: list[str])
    |
    |-- Query FilingText for each ticker: current + prior 10-K
    |   (ordered by period_end DESC, LIMIT 2, filing_type is 10-K)
    |
    |-- Skip tickers with fewer than 2 10-K filings
    |
    |-- For each eligible ticker:
    |   |-- chunk_risk_factors(text) -> list[RiskChunk]
    |   |-- Check embedding cache -> embed only uncached chunks
    |   |-- compute_similarity_matrix(old_embeddings, new_embeddings)
    |   |-- classify_changes(matrix, threshold of 0.85)
    |   |   -> list of (change_type, old_chunk, new_chunk)
    |   |-- If no material candidates -> store result with empty changes, delta of 0.0
    |   |-- If material candidates exist -> call Claude for analysis
    |   |-- Store RiskFactorAnalysis row
    |   '-- Log to llm_call_log
    |
    '-- Return summary: {processed, skipped, errors, total_cost}
```

### ARQ Integration

- diff_risk_factors(ctx, tickers) processes a batch
- orchestrate_risk_diffing(ctx) loads universe, chunks into batches of 50, enqueues jobs
- Cron: weekly Sunday 04:00 UTC (after precompute_default_backtest at 03:00)
- Feature gated: MARGIN_RISK_DIFF_ENABLED environment variable

### Processing Time Estimate

- ~2,000 tickers with 2+ 10-K filings
- Embedding: ~160K embeddings, 1,250 Voyage API calls at ~200ms each, roughly 4 minutes
- Claude analysis: ~2,000 calls at ~1.5s each, concurrency of 4, roughly 12 minutes
- **Total: under 30 minutes** (well within 6 hour target)

## Assessment Harness

### Golden Set Format (evals/risk_factor_diffing/golden_set.jsonl)

Each line is a self contained test case with these fields:

- **case_id**: unique identifier (e.g., "svb-2022-10k")
- **ticker**: stock symbol
- **description**: what happened and why this case matters
- **current_filing**: accession number, period_end, and full risk_factors_text
- **prior_filing**: same structure for the previous year
- **expected_changes**: array of expected detections, each with:
  - change_type (expanded, new, removed, softened)
  - topic_keyword (substring to match against system output topic)
  - min_severity (minimum acceptable severity score)
  - must_detect (true if this counts toward recall)
- **outcome**: the real world event, stock_impact_pct, and months_after_filing

The risk_factors_text is embedded directly in the JSONL so the harness is fully self contained with no network dependencies.

### Runner

The runner loads the golden set, runs the full diff pipeline on each case, and computes:

- **precision**: detected_true / total_system_flagged
- **recall**: detected_true / total_must_detect
- **severity_correlation**: Spearman rank correlation (system severity vs stock_impact_pct)
- **mean_severity_error**: average absolute difference (system_severity minus min_severity)

Regression gate:
- FAIL if precision dropped more than 5% vs prior prompt version
- FAIL if recall dropped more than 5%
- WARN if severity_correlation dropped more than 0.05

Results stored in evals/risk_factor_diffing/runs/ (JSON, gitignored). The runner automatically loads the prior version for regression comparison.

### Seeded Cases

5 initial cases with real SEC filing text: Wirecard, Luckin Coffee, SVB, Enron, WorldCom. 20 additional slots templated for manual labeling.

### Acceptance Criteria Gate

The harness must achieve at least 70% precision and 60% recall on the golden set BEFORE this signal is considered for composite score integration.

## API Surface

### GET /analytics/risk_factors/{ticker}

Returns the most recent analysis for the given ticker. Response includes: ticker, current_period, prior_period, overall_risk_delta_score, model_confidence, material_changes array (each with change_type, topic, severity, summary_50_words), prompt_version, and analyzed_at timestamp.

Verbatim text fields (verbatim_new_text, verbatim_old_text) excluded by default to keep payloads small. Available via include_verbatim query parameter.

Uses existing JWT middleware. No auth changes.

## Frontend

Single card component on the asset detail page (not a new page or route).

**Component:** web/src/components/risk_factors/RiskDeltaCard.tsx

Shows:
- Risk Delta Score as a negative 10 to positive 10 gauge (green for improving, red for deteriorating)
- Material changes list: collapsible rows with change_type badge, topic, severity pill (1-3 green, 4-6 yellow, 7-8 orange, 9-10 red), 50 word summary
- Empty states: "No material changes detected" and "Insufficient data" (fewer than 2 10-K filings)

Supporting components: SeverityPill.tsx, ChangeRow.tsx

## Module Structure

### New Files (api/src/margin_api/)

```
services/risk_diffing/
    __init__.py
    chunker.py          -- paragraph chunking + normalization
    embedder.py         -- Voyage AI client, batch embedding, cache check
    diff_engine.py      -- similarity matrix, change classification
    risk_analyzer.py    -- Claude prompt construction, caching, structured output
    pipeline.py         -- end to end orchestration (batch + single ticker)
    config.py           -- thresholds, model names, prompt version, all tunables
```

### Modified Files

- services/edgar/text_extractor.py — ToC false match fix, additional header patterns
- db/models.py — add RiskFactorAnalysis, RiskFactorEmbedding, LLMCallLog models
- workers.py — register diff_risk_factors, orchestrate_risk_diffing, add weekly cron
- routers/analytics.py — add GET /analytics/risk_factors/{ticker}

### Evals (project root)

```
evals/risk_factor_diffing/
    golden_set.jsonl
    runner.py
    conftest.py
    runs/               -- gitignored
```

### Frontend

```
web/src/components/risk_factors/
    RiskDeltaCard.tsx
    RiskDeltaCard.test.tsx
    SeverityPill.tsx
    ChangeRow.tsx
web/src/lib/api/risk_factors.ts
```

### New Dependencies

- voyageai — Voyage AI Python SDK
- pgvector — SQLAlchemy pgvector integration

### Environment Variables

All new env vars follow the existing MARGIN_ prefix convention:

- MARGIN_RISK_DIFF_ENABLED — feature gate (default false, same pattern as NLP_ENABLED)
- MARGIN_VOYAGE_CREDENTIAL — Voyage AI access credential (set in Railway, never in code)
- MARGIN_RISK_DIFF_SIMILARITY_THRESHOLD — cosine threshold (default 0.85)
- MARGIN_RISK_DIFF_PROMPT_VERSION — active prompt version (default risk_diff_v1)
- MARGIN_RISK_DIFF_MAX_CONCURRENCY — parallel Claude calls per batch (default 4)
- MARGIN_RISK_DIFF_BATCH_SIZE — tickers per ARQ job (default 50)

## Non Goals (v1)

- 10-Q diffing (quarterly filings are less reliable)
- Other 10-K sections (MD&A diffing is a separate future signal)
- Real time alerts on new filings (daily batch is sufficient)
- Composite score integration (standalone overlay until assessment validates)
- Multi year trend analysis (two consecutive 10-Ks only)
