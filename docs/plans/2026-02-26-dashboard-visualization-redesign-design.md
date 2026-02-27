# Dashboard Visualization Redesign

## Overview

Redesign the 4 visualization slots in `ProofSection` on the landing page. Each answers a specific visitor question about the scoring system's credibility.

| Slot | Visualization | Question Answered | Data Source |
|---|---|---|---|
| 1 | Selectivity Funnel (NEW) | "Is this system actually selective?" | New `/api/v1/universe/funnel` |
| 2 | Sector Breakdown (replaces Growth vs. Value Tilt) | "Is this just a tech-heavy momentum strategy?" | `/api/v1/dashboard` (client aggregation) |
| 3 | Correlation Heatmap (updated) | "Would these picks diversify my portfolio?" | `/api/v1/correlations/showcase` (rewired) |
| 4 | Historical Application (real data) | "Does this actually outperform?" | `/api/v1/backtest/teaser` (extended) |

Order rationale: funnel establishes the "elimination first" narrative before showing what survived. The existing `ProofFactorBars` stays above these 4.

---

## Graph 1: Selectivity Funnel

**Component**: `proof-selectivity-funnel.tsx` (new)

**API endpoint**: `GET /api/v1/universe/funnel`

```json
{
  "universe_size": 3200,
  "survived_filters": 280,
  "exceptional_count": 12,
  "high_count": 35,
  "medium_count": 58,
  "last_scored_at": "2026-02-26T04:30:00Z"
}
```

**Visual**: 4 horizontal bars, full-width to narrow, top-to-bottom:

1. **Universe** (gray, full width) — "{N} equities screened"
2. **Survived Filters** (muted accent, proportional width) — "{N} survived elimination ({X}%)"
3. **High + Exceptional** (accent, proportional width) — "{N} reached High or Exceptional conviction"
4. **Exceptional** (bright accent, proportional width) — "{N} Exceptional candidates"

Each bar shows count on the left and survival percentage on the right.

**Implementation**: Pure CSS/Tailwind with Framer Motion `whileInView` width animation. No Recharts — styled divs with proportional widths are cleaner for this shape.

**Subtitle**: "Most equities are eliminated before scoring begins."

**Misinterpretation safeguard**: Below subtitle: "Elimination removes stocks with insufficient data or failing fundamentals — not a quality judgment on the business."

---

## Graph 2: Sector Breakdown

**Component**: `proof-sector-chart.tsx` (replaces `proof-tilt-chart.tsx`)

**Data source**: `/api/v1/dashboard` — client-side aggregation of `sector` × `conviction_level` from picks + watchlist arrays.

**Visual**: Recharts `BarChart` with `layout="vertical"`:

- Y-axis: GICS sector names, sorted by total candidate count descending
- X-axis: candidate count
- 3 grouped bars per sector: Exceptional (bright accent), High (muted accent), Medium (amber/muted)
- Only sectors with >= 1 candidate shown

**Legend**: Three dots — Exceptional, High, Medium

**Subtitle**: "Candidates by sector and conviction level"

**Empty state**: "Scoring in progress — sector breakdown updates after each scoring run."

**Responsive**: At <640px, switch from grouped to stacked bars (one bar per sector).

**Misinterpretation safeguard**: "Scoring is sector-neutral. Distribution reflects where quality + value currently concentrate."

---

## Graph 3: Correlation Heatmap

**Component**: Keep `proof-heatmap.tsx` → `correlation-grid.tsx` (existing)

**Data change**: Update `/api/v1/correlations/showcase` to select the 5 most recently scored candidates (currently selects top 5 by conviction score). Keeps the heatmap fresh and relevant.

**Visual enhancements**:

- Add an interpretation line below the grid, auto-generated from the matrix:
  - "X of 10 pairs show rho < 0.3 — strong diversification" or
  - "Caution: X pairs show rho > 0.7 — sector clustering detected"
- Existing color scheme, hover tooltips ("rho = {value}"), and gradient legend stay as-is.

**Subtitle update**: "Correlation between the 5 most recently analyzed candidates"

**Misinterpretation safeguards**:
- Keep "N = {days} trading days" on hover
- Add footnote: "Correlations shift during market stress. Past correlation does not guarantee future diversification."
- Exclude pairs with <60 days of overlapping data

---

## Graph 4: Historical Application

**Component**: `proof-historical-chart.tsx` (rewrite internals)

**Data source**: Extend `GET /api/v1/backtest/teaser` to include monthly equity curve:

```json
{
  "model_total_return": 0.42,
  "benchmark_total_return": 0.28,
  "max_drawdown": -0.18,
  "sharpe_ratio": 1.45,
  "num_months": 36,
  "equity_curve": [
    {"month": "2023-03", "portfolio": 10000, "benchmark": 10000},
    {"month": "2023-04", "portfolio": 10340, "benchmark": 10120}
  ]
}
```

**Visual**: Recharts `AreaChart`:
- Portfolio: solid accent green line, light fill below
- Benchmark: thin gray line, no fill
- Y-axis: portfolio value (starting $10,000)
- X-axis: month labels (every 3rd or 6th month)
- Tooltip: month, portfolio value, benchmark value, excess return

**Metric ribbon below chart** (4 stats, horizontal row):

| CAGR | Max Drawdown | Sharpe Ratio | Excess Return |
|---|---|---|---|
| font-mono, accent if positive | font-mono, danger if negative | font-mono | font-mono, accent if positive |

**Responsive**: Metric ribbon wraps to 2x2 grid at <640px.

**Backtest parameters**:
- Portfolio: top Exceptional + High candidates, equal-weighted
- Rebalance: quarterly
- Benchmark: S&P 500 total return
- Start date: earliest available scoring run

**Disclaimer**: "Past performance is not indicative of future results. Walk-forward methodology: no look-ahead bias."

---

## Files Deleted

- `web/src/components/landing/proof-tilt-chart.tsx` — replaced by sector breakdown
- `web/src/lib/classify-tilt.ts` — no longer needed

---

## UX Considerations

**Layout**: Single-column stack inside `ProofSection`. Each graph gets:
- Section heading (Inter Tight, `text-lg`, `text-text-primary`)
- Subtitle (Inter Tight, `text-sm`, `text-text-secondary`)
- Chart area (min-height ~240px)
- Footer/disclaimer where applicable

**Loading states**: Skeleton pulse per chart while data loads. Funnel and sector chart share the dashboard fetch. Heatmap and historical chart have independent endpoints.

**Animation**: Funnel bars animate width on scroll-into-view (Framer Motion `whileInView`). Other charts use Recharts built-in mount animation.

**Accessibility**: `aria-label` on all charts. Heatmap cells have `title` attributes. Color is never the sole differentiator — text labels accompany all conviction-level indicators.

---

## API Changes Summary

| Endpoint | Change |
|---|---|
| `GET /api/v1/universe/funnel` | NEW — returns universe_size, survived_filters, exceptional/high/medium counts |
| `GET /api/v1/correlations/showcase` | Change selection from top-5-by-score to top-5-by-scored_at |
| `GET /api/v1/backtest/teaser` | Extend response to include `equity_curve` array and `sharpe_ratio` |

---

## Data Assumptions

- Universe size from `universe/status` endpoint (`universe_size`)
- Filter survivors computed from Score rows with passing filter results
- Conviction counts from Score table `conviction_level` column
- Sector labels from `Asset.sector` (11 GICS sectors)
- Correlation window: 252 trading days (~1 year)
- Backtest: equal-weighted Exceptional + High, quarterly rebalance, S&P 500 benchmark
- Start date: earliest available scoring run (no cherry-picked timeframe)

---

## Risks & Safeguards

| Risk | Safeguard |
|---|---|
| Funnel implies system rejects "good" stocks | Explicit subtitle: elimination targets data gaps and failing fundamentals |
| Sector chart implies sector bets | Note: scoring is sector-neutral, distribution reflects where quality concentrates |
| Correlation = diversification assumption | Footnote: correlations shift during stress, past != future |
| Backtest implies future returns | Standard disclaimer + walk-forward methodology note |
| Small correlation sample size | N={days} on hover, exclude pairs with <60 days overlap |
| Backtest cherry-picks timeframe | Show full available history, label start date |
