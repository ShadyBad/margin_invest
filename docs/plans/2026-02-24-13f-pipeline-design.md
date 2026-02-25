# 13F Institutional Holdings Pipeline — Design Document

**Date:** 2026-02-24
**Status:** Approved

## Overview

A production-grade pipeline to ingest, store, and analyze SEC EDGAR 13F filings for institutional holdings analysis. Serves two purposes: (1) wire the `institutional_accumulation` scoring factor with real data (replacing the hardcoded 50.0 stub), and (2) provide a standalone Smart Money analytics feature as a premium product differentiator.

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Use case | Scoring + standalone analytics | Both are valuable; the pipeline work is the same |
| Fund universe | Top 200-500 by AUM, curated tier tagged | Broad enough for analytics, curated tier weighted in scoring |
| Historical depth | 10+ years (2013-present) | Full market cycle coverage, backtest validation |
| Analytics surface | Asset detail section + /smart-money page | Scoring integration + premium feature surface |
| Subscription gating | Tiered (free teaser → portfolio detail → institutional full) | Natural upsell hook, matches existing gating pattern |
| CUSIP resolution | OpenFIGI primary + fuzzy name match fallback | Free, high accuracy, local cache grows organically |
| Architecture | Parallel dedicated pipeline (Approach B) | Fund-centric quarterly cadence doesn't fit daily ticker pipeline |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARQ Worker                                │
│                                                                  │
│  Daily Pipeline (existing)          13F Pipeline (new)           │
│  ┌──────────┐                       ┌────────────────┐          │
│  │full_ingest│→score→v3→v4          │full_13f_ingest │          │
│  └──────────┘                       └───────┬────────┘          │
│                                             │                    │
│                                    ┌────────▼─────────┐         │
│                                    │compute_accumulation│        │
│                                    │_signals            │        │
│                                    └──────────────────  ┘        │
│                                                                  │
│  Shared: job_runs tracking, circuit breakers, EDGAR provider     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │   PostgreSQL     │
              │                  │
              │ Existing tables  │    New tables:
              │ ─────────────    │    ─────────────
              │ assets           │    managers
              │ financial_data   │    security_master
              │ scores/v3/v4     │    institutional_holdings
              │ job_runs         │    filing_metadata
              │ ...              │    accumulation_signals
              └──────────────────┘
                       │
              ┌────────▼────────┐
              │   FastAPI        │
              │                  │
              │ Existing routes  │    New routes:
              │ ─────────────    │    ─────────────
              │ /scores          │    /13f/holdings
              │ /backtest        │    /13f/managers
              │ /dashboard       │    /13f/analytics
              └──────────────────┘
                       │
              ┌────────▼────────┐
              │   Next.js        │
              │                  │
              │ Asset detail:    │    New page:
              │  + Institutional │    /smart-money
              │    Holders panel │
              │  + ConvictionEng │
              │    wired         │
              └──────────────────┘
```

**Data flow:**

1. **Quarterly 13F ingest** — Iterate ~300 managers by CIK, fetch latest 13F-HR filing from EDGAR, parse XML infotable, resolve CUSIPs via OpenFIGI cache, upsert holdings rows.
2. **Compute accumulation signals** — After ingest, compute per-asset signals: shares_changed, new_position detection, fund count trends. Write to `accumulation_signals` table.
3. **Daily scoring reads signals** — `full_score_v4` reads latest `accumulation_signals` when computing `institutional_accumulation` percentile (replaces hardcoded 50.0).
4. **API serves both** — Asset detail endpoints include institutional holders. Smart Money page queries cross-fund analytics. Gated by subscription tier.

## Database Schema

### `assets` table — add CUSIP column

```sql
ALTER TABLE assets ADD COLUMN cusip VARCHAR(9);
CREATE INDEX ix_assets_cusip ON assets(cusip);
```

### `security_master` — CUSIP resolution cache

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| cusip | VARCHAR(9), UNIQUE | |
| ticker | VARCHAR(10), nullable | Not all CUSIPs map to tracked assets |
| figi | VARCHAR(12), nullable | From OpenFIGI |
| issuer_name | TEXT | Raw name from 13F filing |
| security_name | TEXT | e.g. "COM", "CL A", "SHS" |
| asset_id | FK → assets.id, nullable | Only set if we track this ticker |
| resolution_method | ENUM | 'openfigi', 'name_match', 'manual', 'unresolved' |
| created_at | TIMESTAMP WITH TZ | |
| updated_at | TIMESTAMP WITH TZ | |

Grows organically — every new CUSIP seen in a filing gets a row. OpenFIGI resolves it, we cache forever. `asset_id` links to our universe when applicable.

### `managers` — institutional fund registry

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| cik | VARCHAR(10), UNIQUE | Immutable SEC identifier |
| name | TEXT | e.g. "BERKSHIRE HATHAWAY INC" |
| short_name | TEXT | e.g. "Berkshire Hathaway" |
| tier | ENUM | 'curated', 'top_aum', 'other' |
| aum_latest | BIGINT, nullable | Latest reported 13F value |
| active | BOOLEAN | Default true |
| first_filing_date | DATE, nullable | |
| last_filing_date | DATE, nullable | |
| metadata | JSONB | Website, strategy description, etc. |
| created_at | TIMESTAMP WITH TZ | |
| updated_at | TIMESTAMP WITH TZ | |

The `tier` field distinguishes the 10 curated super investors from the broader AUM-ranked set. Scoring weights the curated tier more heavily.

### `filing_metadata` — one row per 13F filing

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| manager_id | FK → managers.id | |
| accession_number | VARCHAR(25), UNIQUE | SEC's filing ID |
| filing_type | ENUM | '13F-HR', '13F-HR/A' |
| period_of_report | DATE | Quarter end date |
| filed_date | DATE | |
| total_value | BIGINT | Reported portfolio value in thousands |
| total_holdings | INTEGER | |
| source_url | TEXT | |
| is_amendment | BOOLEAN | |
| supersedes_id | FK → filing_metadata.id, nullable | For amendments |
| ingestion_run_id | FK → job_runs.id, nullable | |
| created_at | TIMESTAMP WITH TZ | |

**Amendment logic:** When a 13F-HR/A arrives, find the original filing for the same `(manager_id, period_of_report)`, set `supersedes_id`, and re-ingest holdings. Queries default to the latest amendment.

### `institutional_holdings` — one row per position per filing

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| filing_id | FK → filing_metadata.id | |
| manager_id | FK → managers.id | Denormalized for query speed |
| security_master_id | FK → security_master.id | |
| cusip | VARCHAR(9) | Denormalized |
| period_of_report | DATE | Denormalized |
| shares_held | BIGINT | |
| value_thousands | BIGINT | Reported market value in $1000s |
| put_call | ENUM | 'PUT', 'CALL', 'NONE' |
| investment_discretion | ENUM | 'SOLE', 'SHARED', 'DEFINED' |
| voting_authority_sole | BIGINT | |
| voting_authority_shared | BIGINT | |
| voting_authority_none | BIGINT | |
| created_at | TIMESTAMP WITH TZ | |

**Indexes:**
- `UNIQUE (filing_id, cusip, put_call)` — deduplicate within a filing
- `INDEX (manager_id, period_of_report)` — fund portfolio over time
- `INDEX (cusip, period_of_report)` — all holders of a security
- `INDEX (security_master_id, period_of_report)` — same, via security master

**Estimated volume:** ~300 managers x ~40 quarters x ~500 holdings = ~6M rows.

### `accumulation_signals` — precomputed per-asset scoring input

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| asset_id | FK → assets.id | |
| period_of_report | DATE | |
| curated_holders | INTEGER | Count of curated-tier funds holding |
| total_holders | INTEGER | Count of all tracked funds holding |
| curated_new_positions | INTEGER | Curated funds that initiated new position |
| total_new_positions | INTEGER | |
| curated_net_shares | BIGINT | Net share change across curated funds |
| total_net_shares | BIGINT | |
| signal_score | FLOAT | Normalized 0-100 composite signal |
| computed_at | TIMESTAMP WITH TZ | |
| created_at | TIMESTAMP WITH TZ | |

**Index:** `UNIQUE (asset_id, period_of_report)`

This is what the scoring pipeline reads. The v4 scorer never touches raw holdings.

## Pipeline & Orchestration

### ARQ Task Chain

```
full_13f_ingest
  ├── Step 1: Refresh manager registry (discover/update fund list)
  ├── Step 2: For each active manager, fetch latest unfetched filings
  ├── Step 3: For each filing, parse XML infotable → resolve CUSIPs → upsert holdings
  └── chains to ↓

compute_accumulation_signals
  ├── Step 1: For each asset in our universe, query holdings across quarters
  ├── Step 2: Compute quarter-over-quarter deltas
  ├── Step 3: Compute normalized signal_score (0-100)
  └── Step 4: Upsert accumulation_signals rows
```

### Scheduling

```python
# Existing daily chain (unchanged)
cron(full_ingest,      hour=21, minute=30)

# 13F pipeline — runs daily, smart about skipping
cron(full_13f_ingest,  hour=22, minute=0)   # 5 PM ET, after daily pipeline
```

Why daily, not quarterly: 13F filings trickle in throughout the 45-day window after quarter-end. Running daily catches new filings as they appear. The pipeline is idempotent — skips managers whose latest filing has already been ingested. On most days it does almost nothing.

### EDGAR Rate Limiting

SEC EDGAR allows 10 requests/sec with a declared User-Agent. For the 13F pipeline:
- Filing index fetch: 1 request per manager per run
- Infotable fetch: 1 request per new filing
- Burst budget: ~300 managers = ~300 requests on a quiet day, ~600 during filing season

### CUSIP Resolution Flow

```
For each holding in parsed XML:
  1. Check security_master cache by CUSIP
     → HIT: use cached ticker/asset_id
     → MISS: continue to step 2

  2. Call OpenFIGI API (batch endpoint, up to 100 CUSIPs per request)
     → RESOLVED: insert security_master row, link asset_id if ticker in universe
     → UNRESOLVED: continue to step 3

  3. Fuzzy name match against assets table (existing EDGARProvider logic)
     → MATCH: insert security_master row with resolution_method='name_match'
     → NO MATCH: insert as 'unresolved', nullable ticker/asset_id
```

### Retry & Error Handling

- **Per-manager circuit breaker** — 3 consecutive failures → skip for 24 hours, log warning
- **Per-filing retry** — Transient HTTP errors (429, 503) → exponential backoff, max 3 retries
- **Poison filing detection** — XML parsing fails 3 times → mark as `parse_error` in `filing_metadata`, move on, alert for manual review
- **Job tracking** — Each run creates a `job_runs` row with `job_type='13f_ingest'`

### Pipeline Idempotency

- **Filing dedup:** `accession_number` is unique. Already-ingested filings are skipped.
- **Holdings dedup:** `UNIQUE (filing_id, cusip, put_call)` prevents double-inserts.
- **Amendment handling:** 13F-HR/A detected → find original for same `(manager_id, period_of_report)` → set `supersedes_id` → re-parse and upsert holdings.

## Historical Backfill

One-time operation, run manually before steady-state cron takes over.

**Phase 1: Seed managers (~5 min)**
Fetch SEC EDGAR's full filer index for 13F-HR filings. Filter to top ~300 by latest reported AUM. Tag the 10 curated super investors. Insert `managers` rows.

**Phase 2: Backfill filings, 2013→present (~4-6 hours)**
Iterate managers oldest-to-newest. For each manager, fetch filing index, parse XML, resolve CUSIPs, insert holdings. Rate-limited to 5 req/sec. Resume-safe via `accession_number` uniqueness.

```bash
uv run python -m margin_api.cli backfill-13f --start-year 2013
```

**Phase 3: Bulk CUSIP resolution (~30 min)**
Collect all unresolved CUSIPs from phase 2. Batch-call OpenFIGI (100 per request). Run fuzzy name matching for remainder. Log unresolved count for manual review.

**Phase 4: Compute historical signals (~10 min)**
Run `compute_accumulation_signals` across all quarters. Populates `accumulation_signals` for the full 10-year history. Enables backtesting of `institutional_accumulation` immediately.

## Scoring Integration

### Signal Score Computation

The `signal_score` on `accumulation_signals` is a composite of four sub-signals, each normalized 0-100 via percentile rank across all assets in the universe for that quarter:

| Sub-signal | Weight | Logic |
|---|---|---|
| Curated holder count | 30% | More curated super-investor funds holding = stronger signal |
| Net curated accumulation | 30% | Net share increases across curated funds |
| New position detection | 25% | Curated fund initiated a new position |
| Broad holder trend | 15% | Quarter-over-quarter change in total tracked fund count |

Curated-tier funds get 2x the weight of top-AUM funds in accumulation and new position sub-signals.

### V4 Scoring Read Path

```python
# In full_score_v4, when computing institutional_accumulation:
latest_signal = db.query(AccumulationSignal)\
    .filter_by(asset_id=asset.id)\
    .order_by(AccumulationSignal.period_of_report.desc())\
    .first()

if latest_signal:
    institutional_percentile = latest_signal.signal_score
else:
    institutional_percentile = None  # excluded from factor, not faked
```

If no 13F signal exists for an asset, the factor is `None` — excluded from the composite, not hardcoded to 50.

### 45-Day Filing Lag

- `accumulation_signals.period_of_report` reflects the quarter the data describes, not when filed
- Scoring uses the latest available quarter, which may be 1-2 quarters old
- No attempt to interpolate between quarters — honest data only
- Frontend displays lag transparently

### ConvictionEngine API Response

```json
{
  "institutional_accumulation": {
    "percentile": 78.5,
    "curated_holders": 3,
    "total_holders": 12,
    "notable_new_positions": ["Berkshire Hathaway", "Lone Pine"],
    "quarter": "2025-Q4",
    "filing_lag_days": 38
  }
}
```

## API Endpoints

### Asset Detail Endpoints

**`GET /api/v1/13f/holdings/{ticker}`** — All tracked funds holding this asset.

Response includes curated holders (fund name, shares held, change, % portfolio, quarters held), other holders, and a summary (total/curated holder counts, net shares changed, signal score).

Gating: Free tier sees summary only. `portfolio`+ sees full holder details.

**`GET /api/v1/13f/holdings/{ticker}/history`** — Position changes over time by quarter.

Gating: `portfolio`+ only.

### Smart Money Page Endpoints (all `institutional`+ only)

**`GET /api/v1/13f/managers`** — Browse tracked funds. Name, tier, AUM, holdings count, top 5 positions, last filing date.

**`GET /api/v1/13f/managers/{manager_id}/portfolio`** — Full fund portfolio with position changes. Includes changes_summary: new positions, exited positions, increased/decreased/unchanged counts.

**`GET /api/v1/13f/analytics/overlap`** — Most-held stocks across all funds. Crowded trades (stocks with many new positions this quarter).

**`GET /api/v1/13f/analytics/new-positions`** — Stocks where multiple tracked funds initiated new positions. Sorted by curated-fund count.

**`GET /api/v1/13f/analytics/clone/{manager_id}`** — Clone portfolio simulation. Strategy options: equal-weight top 10/20, market-cap weighted. Returns allocation + historical performance (return, CAGR, max drawdown, Sharpe).

### Query Optimization

- `compute_accumulation_signals` precomputes overlap/crowded trade summaries alongside per-asset signals. Stored as JSONB in a `quarterly_analytics` table.
- Redis cache with 1-hour TTL for analytics endpoints (data changes at most once per day).
- Total data volume (~6M rows) is well within Postgres comfort zone.

## Frontend

### Asset Detail — Institutional Positioning Panel

Positioned after Scoring Pillars on the existing asset detail page:

- **Header:** "Institutional Positioning — Q4 2025" with filing lag badge
- **Summary bar:** Holder counts, net accumulation
- **Curated holders table:** Fund name, shares held, change delta (green/red), % of fund portfolio, quarters held. Sorted by value.
- **Holder trend sparkline:** Curated + total holder count over 8-10 quarters
- **Expandable full holder list** below curated section

**Free tier teaser:** Summary bar visible but muted. Holder table replaced with blurred placeholder + upgrade CTA. Matches existing backtest teaser pattern.

### ConvictionEngine Wiring

Wire `institutionalAccumulation` prop to score API response. Displays percentile rank, curated holder count, and notable activity inline.

### Smart Money Page (`/smart-money`)

**Tab 1: Fund Tracker** (default)
Searchable/sortable table of all tracked managers. Click row expands to full portfolio with position changes highlighted (green = added, red = reduced, gold star = new, strikethrough = exited).

**Tab 2: Market Signals**
Most crowded positions (top 20 by holder count). New position alerts (multiple funds initiating). Biggest exits.

**Tab 3: Clone Lab**
Manager dropdown + strategy selector (equal-weight top 10/20, market-cap weighted). Portfolio allocation table. Historical equity curve (reuse `EquityCurve` component). Performance stats (reuse `StatsSummary` component). Disclaimer about 45-day delay and simulated results.

### Component Reuse

- `EquityCurve` from backtesting → clone lab
- `StatsSummary` from backtesting → clone lab metrics
- Design tokens (`--color-bullish`, `--color-bearish`, `terminal-card`) → consistent styling
- `GlobalSearch` → add manager search results alongside tickers

### Subscription Gating Matrix

| Feature | analyst (free) | portfolio | institutional+ |
|---|---|---|---|
| Asset detail summary bar | Visible | Visible | Visible |
| Asset detail holder details | Teaser/blurred | Full | Full |
| Asset detail history chart | Hidden | Visible | Visible |
| ConvictionEngine accumulation | Score only | Score + detail | Score + detail |
| Smart Money page | Teaser landing | Teaser landing | Full access |
| Clone Lab | Hidden | Hidden | Full access |

## Monitoring & Alerting

**Pipeline health (via `job_runs`):**
- Each `full_13f_ingest` run logs: `managers_checked`, `new_filings_found`, `holdings_inserted`, `cusip_resolution_failures`
- Alert if: zero new filings found during the 45-day filing window
- Alert if: CUSIP resolution failure rate exceeds 5%
- Alert if: curated manager hasn't filed in 60+ days past quarter-end

**Data validation (post-ingest):**
- Duplicate detection: same `(manager_id, period_of_report)` with multiple non-amendment filings
- Holdings sanity: flag single holding > 50% of reported AUM
- AUM continuity: flag >80% quarter-over-quarter AUM change
- CUSIP drift: flag CUSIP previously resolved to ticker X appearing under different issuer name

## Common Pitfalls & Mitigations

| Pitfall | Impact | Mitigation |
|---|---|---|
| 13F-HR/A amendments silently replace original | Stale data | Daily pipeline catches amendments. `supersedes_id` chain. Queries use latest filing. |
| CUSIP reuse after delisting | Wrong security mapping | Track `issuer_name` in security_master. CUSIP drift detection flags mismatches. |
| Class shares (GOOG A vs C) | Fragmented holder counts | OpenFIGI returns shared ticker. Aggregate across CUSIPs mapping to same ticker. |
| Confidential treatment (13F-CT) | Missing data for some funds/quarters | Accept the gap. Log when 13F-CT detected. No fabrication. |
| XML format variations pre-2013 | Parse failures | Backfill starts 2013. Parser handles both namespace variants. Poison filing detection. |
| Manager name changes / mergers | Duplicate rows | Match by CIK (immutable), not name. |
| 13F only covers long equity + options | Incomplete picture | Document in UI: "Based on 13F long equity filings." |
| 45-day filing delay | Stale perception | Display lag prominently. Frame as structural conviction signal. |
| SEC rate limiting / outages | Ingestion failures | Exponential backoff, circuit breaker, resume-safe idempotency. |

## Testing Strategy

- **Engine tests:** CUSIP resolution, signal computation, amendment dedup logic. Golden-value tests for accumulation scoring.
- **API tests:** All 13F endpoints with aiosqlite. Subscription gating tests (free sees teaser, institutional sees full).
- **Integration tests:** End-to-end pipeline with fixture XML filings. Verify: XML parse → CUSIP resolve → holdings insert → signal compute → API serve.
- **Web tests:** Vitest + RTL for institutional holders panel, smart money page tabs, gating behavior.

## Tech Stack Summary

| Component | Technology |
|---|---|
| Data source | SEC EDGAR API (primary), Finnhub (fallback) |
| CUSIP resolution | OpenFIGI API + fuzzy name matching |
| Pipeline orchestration | ARQ (existing worker) |
| Database | PostgreSQL (existing) |
| API | FastAPI (existing) |
| Frontend | Next.js 15 (existing) |
| Caching | Redis (existing) |
| Deployment | Railway (existing two-service setup) |
