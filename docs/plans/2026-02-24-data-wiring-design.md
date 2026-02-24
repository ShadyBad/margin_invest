# Data Wiring Design: Backtest + Elimination Vignette

**Date:** 2026-02-24
**Status:** Approved

## Problem

Four frontend components use hardcoded/mock data despite API endpoints existing that serve the real data. This creates a disconnect where the UI shows synthetic numbers instead of actual computed results.

## Scope

| Component | Current State | Fix |
|-----------|--------------|-----|
| BacktestTeaser | Hardcoded props, wrong TS type | Fix type mismatch, wire API call |
| EliminationVignette | Defaults to 70% | Compute from existing HomepageData |
| Backtest page (9 components) | Mock data constants | Wire to `GET /backtest/default` |
| Shadow portfolio section | Mock data | Wire to `GET /backtest/shadow-portfolio` |

No new API endpoints are needed. All data sources already exist.

## Task A: Fix BacktestTeaser Type + Wire to API

### Problem
- TS type `BacktestTeaserResponse` has `start_year: number`
- API returns `start_date: date` and `end_date: date`
- Component receives hardcoded numbers in `asset-detail-view.tsx`

### Changes
1. **`web/src/lib/api/types.ts`** — Update `BacktestTeaserResponse` to match API schema:
   - Replace `start_year: number` with `start_date: string`, `end_date: string`
   - Add `ticker: string | null`

2. **`web/src/components/asset-detail/backtest-teaser.tsx`** — Change prop from `startYear` to `startDate`, extract year internally via `new Date(startDate).getFullYear()`

3. **`web/src/components/asset-detail/asset-detail-view.tsx`** — Replace hardcoded `<BacktestTeaser>` with async fetch:
   - Call `getBacktestTeaser(ticker)`
   - On success, render with API data
   - On failure, hide the teaser (don't show stale hardcoded numbers)

4. **Update tests** for new prop interface and conditional rendering

## Task B: Wire EliminationVignette to Real Data

### Problem
- `EliminationVignette` takes optional `eliminatedPct`, defaults to 70%
- `HomepageData` already has `total_scored` and `eligible_count`
- The math: `eliminatedPct = round(((totalScored - eligibleCount) / totalScored) * 100)`

### Changes
1. **`web/src/components/landing/homepage-client.tsx`** — Compute elimination percentage from `data.total_scored` and `data.eligible_count`, pass to `<EliminationVignette>`

2. **Update test** to verify the prop is passed through

## Task C: Wire Backtest Page to Replay API

### Problem
- Page defines ~80 lines of mock data constants
- API `GET /backtest/default` returns `FullBacktestResponse` with all the data the components need
- API `GET /backtest/shadow-portfolio` returns `ShadowPortfolioResponse`
- Page needs to transform API shapes to component prop shapes

### API Response → Component Mapping

| API Field | Component | Transform |
|-----------|-----------|-----------|
| `regime_segments[]` | `RegimeCards` | Map `num_months` → `months`, compute `excessReturn`, add labels |
| `equity_curve[]` | `EquityCurve` | Map dict fields to typed interface, compute drawdown |
| `factor_timeline[]` | `FactorTimeline` | Map `as_of_date` → `date`, `available` → `factors` |
| `audit_log[]` | `AuditLog` | Map `rebalance_date` → `date`, `factor_coverage` → `factorCoverage`, compute turnover |
| `metrics` | `StatsSummary` | Direct mapping with camelCase conversion |
| `failure_audit[]` | `FailureAudit` | Map fields, add `recoveryMonths: null` (not computed by API) |
| `config` | `KnobsPanel` | Direct mapping |
| Shadow portfolio response | `ShadowSection` | Direct mapping |

### Changes
1. **`web/src/lib/api/types.ts`** — Add types: `FullBacktestResponse`, `RegimeSegmentResponse`, `AuditRecordResponse`, `FactorTimelineResponse`, `FailurePeriodResponse`, `ShadowPortfolioResponse`, `ShadowSnapshotResponse`

2. **`web/src/lib/api/backtest.ts`** — Add functions:
   - `getDefaultBacktest(): Promise<FullBacktestResponse>`
   - `runReplay(config): Promise<FullBacktestResponse>`
   - `getShadowPortfolio(): Promise<ShadowPortfolioResponse>`

3. **`web/src/lib/api/index.ts`** — Export new functions and types

4. **`web/src/app/backtesting/page.tsx`** — Major rewrite:
   - Remove all `MOCK_*` constants
   - Fetch `getDefaultBacktest()` + `getShadowPortfolio()` on mount
   - Add transform functions to map API shapes → component props
   - Wire KnobsPanel submit to `runReplay()`
   - Keep graceful empty states when API returns empty arrays

5. **Update page tests** to mock new API functions

## Out of Scope

- ConvictionEngine `institutionalAccumulation` (needs 13F data pipeline — separate milestone)
- Real PIT data providers for ReplayOrchestrator (API returns synthetic defaults)
- Shadow portfolio worker job (endpoint returns placeholder until worker runs)

## Success Criteria

- No hardcoded/mock data remains in any component
- All components fetch from API and render real responses
- Graceful degradation when API returns empty/error
- All existing tests pass, new tests cover wiring logic
