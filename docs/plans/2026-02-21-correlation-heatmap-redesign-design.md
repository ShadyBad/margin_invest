# Correlation Heatmap Redesign

**Date:** 2026-02-21
**Status:** Approved

## Goal

1. Remove the Portfolio Correlations chart from the Dashboard (full cleanup)
2. Update the landing page correlation heatmap to display real Exceptional/High conviction tickers instead of hardcoded static data

## Part 1: Dashboard Cleanup

Remove all dashboard correlation infrastructure:

**Delete files:**
- `web/src/components/dashboard/correlation-heatmap.tsx`
- `web/src/app/api/v1/correlations/route.ts` (authenticated proxy)

**Edit files:**
- `web/src/app/dashboard/page.tsx` — remove CorrelationHeatmap import and `<section>`
- `web/src/components/dashboard/index.ts` — remove CorrelationHeatmap export
- `web/src/lib/api/correlations.ts` — remove `getCorrelations()`, keep `getShowcaseCorrelations()`
- `api/src/margin_api/routes/correlations.py` — remove authenticated `GET /api/v1/correlations` endpoint, keep `/showcase`

**Keep (shared):**
- `web/src/components/ui/correlation-grid.tsx` — used by landing page heatmap
- Engine correlation computation functions
- `/showcase` endpoint and its proxy route

## Part 2: Landing Page Heatmap with Real Tickers

### API: Enhance `/showcase` endpoint

Current behavior: reads `correlation:showcase` from Redis, falls back to hardcoded 5-ticker matrix.

New behavior on cache miss:
1. Query `scores` + `assets` tables for top 5 tickers by `composite_raw_score` DESC where score >= 72.0 (High conviction threshold, covers both Exceptional >=79 and High >=72)
2. Load `price_history` JSONB from `financial_data` for each ticker
3. Call engine's `compute_return_correlations()` to build the matrix
4. Cache result in Redis with key `correlation:showcase`, TTL = 1 hour
5. If fewer than 5 qualifying tickers exist, return static fallback data unchanged

### Frontend: No changes needed

`ProofHeatmap` already calls `/api/v1/correlations/showcase` and falls back to static data on error. It will automatically display real tickers once the API returns them.

### Cache strategy

- 1-hour TTL via Redis
- Natural expiry handles staleness (scoring runs are less frequent than hourly)
- No manual invalidation needed

## Decisions

- **Grid size:** 5 tickers (5x5 grid) — matches current visual
- **Ticker selection:** Top 5 by composite_raw_score where score >= 72.0 (Exceptional first, High as fallback)
- **Fallback:** Static hardcoded data when <5 qualifying tickers available
- **Computation:** Live on first request, cached 1 hour in Redis
- **Cleanup scope:** Full removal of dashboard correlation infrastructure
