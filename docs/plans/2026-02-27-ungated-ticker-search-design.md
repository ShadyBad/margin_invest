# Ungated Ticker Search on Landing Page

## Problem

Visitors must create an account before experiencing any value. This is the single highest-leverage conversion gap — letting visitors type a ticker and see a score WITHOUT signing up creates the "holy shit" moment that drives signups.

## Solution

A public score endpoint + a search component embedded in the hero section. Visitors type a ticker, see a lightweight score summary, then get a CTA to sign up for the full forensic report.

## Architecture

### Public Score API Endpoint

**New file**: `api/src/margin_api/routes/public_scores.py`

```
GET /api/v1/public/score/{ticker}
```

No auth required. Rate limited at 30 req/min per IP via slowapi.

**Response schema** (`PublicScoreResponse`):

```python
class PublicScoreFactorSummary(BaseModel):
    quality_percentile: float
    value_percentile: float
    momentum_percentile: float

class PublicScoreResponse(BaseModel):
    ticker: str
    company_name: str
    composite_score: float          # 0-100
    composite_tier: str             # "exceptional", "high", "medium", "none"
    signal: str                     # "strong/stable/emerging/weak/failed/neutral"
    factor_summary: PublicScoreFactorSummary
    eliminated: bool
    elimination_reason: str | None
    scored_at: str                  # ISO 8601
```

**Fallback chain**:
1. V4Score with `published=True`, joined to Asset, ordered by `scored_at DESC`, limit 1
2. V4Score (any, regardless of published flag)
3. Base Score table
4. 404 if no score exists

**Factor percentile extraction**:
- V4Score: from `detail` JSONB → quality/value/momentum `average_percentile`
- Score fallback: from summary columns `quality_percentile`, `value_percentile`, `momentum_percentile`

**Elimination detection**:
- `eliminated = True` if any filter in `detail.filters_passed` has `passed=False`
- `elimination_reason` = name of the first failed filter, or null

**Caching**: `Cache-Control: public, max-age=300` header. Scores update daily; 5-min staleness is acceptable. CDN and browser caches handle the rest.

**Route registration**: Added to `app.py` alongside the transparency router — no auth middleware.

### HeroSearch Component

**New file**: `web/src/components/landing/hero-search.tsx`

Client component with four states:

1. **Idle** — Text input (placeholder "Search any ticker...") + search button
2. **Loading** — Input disabled, spinner in button
3. **Result** — Compact card below input:
   - Ticker + company name
   - Composite score (large font-mono) + tier badge
   - 3 factor bars (Quality / Value / Momentum percentiles)
   - If eliminated: red "ELIMINATED" badge + reason
   - CTA: "See the full forensic report →" → `/onboarding`
4. **Error** — "Ticker not found" or "Something went wrong"

**Fetch**: Uses `apiFetch()` from `@/lib/api/client`. Works without auth headers since the endpoint requires none.

**Interaction**:
- Submit on Enter or button click
- Input auto-uppercases on blur
- No debounce (explicit submit, not typeahead)

**Visual patterns**: `terminal-card` class, `--color-bullish`/`--color-bearish` tokens, `font-mono` for numbers, factor bar style from `hero-candidate-card.tsx`.

### Hero Section Integration

In `hero-section.tsx`, the existing CTA `<div data-hero-ctas>` is replaced by `<HeroSearch />`. The `data-hero-ctas` attribute moves to the HeroSearch wrapper so the GSAP stagger animation still works. The rotating candidate card on the right remains unchanged.

Result card appears inline below the search input in the left column. Rotating card stays undisturbed on the right.

## What This Does NOT Include

- Full forensic breakdown (sub-scores, price targets, ML fields) — that's behind auth
- Typeahead/autocomplete — explicit submit only
- Server-side rendering of the search result
- App-level Redis caching — HTTP Cache-Control is sufficient

## Testing

### API tests (`api/tests/routes/test_public_scores.py`)

- Happy path: Published V4Score returns correct schema
- Unpublished V4 fallback: Returns unpublished V4Score when no published exists
- Score fallback: Returns base Score when no V4 exists
- 404: Unknown ticker returns 404
- Eliminated ticker: `eliminated=True` with `elimination_reason`
- Schema leak check: Response does NOT contain forensic fields
- Rate limit decorator presence

### Web tests (`web/src/components/landing/__tests__/hero-search.test.tsx`)

- Renders input and button
- Shows loading state on submit
- Shows result card with score data
- Shows eliminated badge for eliminated tickers
- Shows error for 404
- Shows generic error for network failure
- CTA links to `/onboarding`

### Regression

- Existing authenticated score endpoint tests unchanged
- Hero section test updated for CTA → search replacement
