# API Sector Enhancements Design

**Date**: 2026-02-26
**Status**: Approved

## Goal

Wire four data fields into the API that the frontend UX strategy components already consume: market_cap on ScoreResponse, sector_pass_rate on FilterResultResponse, sector distribution stats (P10/P50/P90) per sub-factor, and a sector champion for the FailedComparison component.

## Guiding Principle

No new DB tables. All precomputed data stored in the existing V4Score.detail JSONB blob. market_cap already exists on Asset. Sector champion is a runtime query (eliminated tickers only).

---

## Enhancement 1: market_cap on ScoreResponse

**Source**: `Asset.market_cap` (Decimal column, already populated during ingest from yfinance)

**Change**:
- Add `market_cap: float | None` to ScoreResponse Pydantic schema
- In `_v4_score_response_from_row()`, accept the Asset record and extract market_cap
- Join Asset when querying V4Score in the score endpoint

**Frontend consumer**: `EliminatedHero` uses market_cap >= $100B for protective framing.

---

## Enhancement 2: sector_pass_rate on FilterResultResponse

**Source**: Computed during the V4 scoring pipeline after all tickers in a sector have been filtered.

**Computation**:
- After filter results are collected for all tickers, group by (sector, filter_name)
- For each group: `pass_rate = count(passed=True) / total_count`
- Store as `sector_filter_pass_rates: dict[str, dict[str, float]]` in V4Score.detail JSONB
  - Outer key: sector name
  - Inner key: filter name
  - Value: pass rate (0.0-1.0)

**API change**:
- Add `sector_pass_rate: float | None` to FilterResultResponse
- In response builder, look up `detail["sector_filter_pass_rates"][sector][filter.name]`

**Frontend consumer**: `FilterCard` shows "68% of Consumer Discretionary stocks pass this filter."

---

## Enhancement 3: Sector Distribution (P10/P50/P90 per sub-factor)

**Source**: Computed during `rank_and_compute_composites()` in `scoring.py`.

**Computation**:
- In the sector grouping loop (scoring.py:305-325), after `compute_percentile_ranks()` runs for each (sector, factor_name) group:
  - Sort raw values
  - Extract P10, P50 (median), P90 from the sorted array
  - Record count of stocks in sector
- Store as `sector_distribution: dict[str, { p10: float, p50: float, p90: float, count: int }]` in the detail JSONB
  - Key: sub-factor name (e.g., "gross_profitability")

**API change**:
- Add optional fields to FactorScoreResponse: `sector_p10: float | None`, `sector_p50: float | None`, `sector_p90: float | None`, `sector_count: int | None`
- In response builder, populate from `detail["sector_distribution"][factor_name]`

**Frontend consumer**: `SectorMicroBar` uses P10/P50/P90 markers. `SectorNeutralBanner` uses count for "compared to N peers."

---

## Enhancement 4: Sector Champion (for FailedComparison)

**Source**: Runtime query on eliminated ticker requests only.

**Query**:
```sql
SELECT v4.ticker, v4.detail, a.market_cap
FROM v4_scores v4
JOIN assets a ON a.ticker = v4.ticker
WHERE a.sector = :sector
  AND v4.detail->>'all_filters_passed' = 'true'
ORDER BY v4.composite_score DESC
LIMIT 1
```

**API change**:
- New schema: `SectorChampionResponse { ticker: str, filter_values: dict[str, float | None] }`
- Add `sector_champion: SectorChampionResponse | None` to ScoreResponse
- Only populated when the requested ticker has failed filters
- Extract champion's individual filter values from their `detail["filters_passed"]` JSONB

**Frontend consumer**: `FailedComparison` shows champion's values side-by-side with the failed ticker.

---

## Data Flow

```
Scoring Pipeline (precompute, stored in V4Score.detail JSONB):
  run_elimination_filters() -> sector_filter_pass_rates[sector][filter_name] = pass_rate
  rank_and_compute_composites() -> sector_distribution[factor_name] = {p10, p50, p90, count}

API Response (per request):
  Asset.market_cap -> ScoreResponse.market_cap
  detail.sector_filter_pass_rates -> FilterResultResponse.sector_pass_rate
  detail.sector_distribution -> FactorScoreResponse.sector_p10/p50/p90/sector_count
  Champion query (eliminated only) -> ScoreResponse.sector_champion
```

## Frontend Wiring

All frontend components already handle null gracefully. Once the API returns data:
- `EliminatedHero`: Uses `scoreData.market_cap` for protective framing threshold
- `FilterCard`: Uses `filter.sector_pass_rate` for "X% of sector stocks pass" line
- `SectorMicroBar`: Uses `sub.sector_p10/p50/p90` for real distribution markers
- `SectorNeutralBanner`: Uses `sector_count` for "compared to N peers"
- `FailedComparison`: Uses `scoreData.sector_champion` for champion ticker/values
