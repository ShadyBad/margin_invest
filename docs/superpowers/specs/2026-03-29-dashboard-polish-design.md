# Dashboard Polish & Bug Fixes

**Date**: 2026-03-29
**Scope**: 8 independent fixes across dashboard UI, backend query logic, auth, and data seeding

---

## Overview

The dashboard has several rough edges that undermine trust and usability: avatar fallback not loading OAuth profile pictures, sentiment tracks showing empty when no data exists, score text clipping into names, sparse top-candidate cards, inconsistent ranking, empty Smart Money/Backtesting pages, and an auth bug preventing OAuth users from setting passwords.

All 8 fixes are independent and can be implemented in any order.

---

## Fix 1 — OAuth Avatar Not Loading

**Problem**: Users who sign in via Google/GitHub see a colored circle with initials instead of their profile picture.

**Root cause**: The `oauthAvatarUrl` is captured in the JWT at sign-in (`token.oauthAvatarUrl = user.image` in `web/src/lib/auth.ts:176`), but:
- If the user signed in before this code was added, the JWT doesn't carry the field.
- If the avatar URL expires or fails to load, the `Avatar` component silently falls back to initials with no diagnostic output.
- The 60s security-status refresh doesn't re-fetch the avatar URL from the backend.

**Changes**:

1. **Backend `security-status` endpoint** (`api/src/margin_api/routes/auth.py`): Include `avatar_url` in the response so the JWT refresh cycle can update it.

2. **JWT refresh branch** (`web/src/lib/auth.ts`, the `else if (token.userId)` branch ~line 204): When the security-status response arrives, also update `token.oauthAvatarUrl` if the backend returns an `avatar_url` and the token doesn't already have one (or if the existing one differs).

3. **Avatar component** (`web/src/components/ui/avatar.tsx`): Add `console.warn` in development mode when an image URL fails to load, so failed URLs are diagnosable instead of silently swallowed.

**Files**:
- `api/src/margin_api/routes/auth.py` — security-status response
- `api/src/margin_api/schemas/auth.py` — SecurityStatusResponse schema
- `web/src/lib/auth.ts` — JWT refresh branch
- `web/src/components/ui/avatar.tsx` — dev warning on error

---

## Fix 2 — Hide Sentiment Track When No Data

**Problem**: `FactorSignature` renders all 5 factor tracks (quality, value, momentum, sentiment, growth) regardless of whether data exists. When `sentiment` or `growth` is `null`, empty track lines with no dot waste vertical space.

**Changes**:

1. **`FactorSignature`** (`web/src/components/visualizations/factor-signature.tsx`): Filter `FACTOR_CONFIG` to only include factors where the value is not `null` before rendering. This affects the track-based variants (`full`, `compact`, `mini`) and the inline dot variant.

2. The connecting polyline already skips null factors, so it adapts naturally.

3. Dynamic height: Recalculate SVG `height` based on the number of visible factors instead of the fixed 5-factor height.

**Files**:
- `web/src/components/visualizations/factor-signature.tsx`

---

## Fix 3 — Score Clipping Into Name

**Problem**: On `PickHeroCard`, the 36px score and the name/ticker row are too close together. On narrow viewports or with long names, the score visually overlaps the name text.

**Changes**:

1. **`PickHeroCard`** (`web/src/components/dashboard/pick-hero-card.tsx`):
   - Change the score container from `mt-3` to `mt-4` for more breathing room.
   - Add `truncate` (overflow-hidden + text-ellipsis) on the name `<p>` element.

2. **`PickMediumCard`** (`web/src/components/dashboard/pick-medium-card.tsx`):
   - Same spacing fix — ensure the 28px score has adequate separation from the ticker/badge row.

**Files**:
- `web/src/components/dashboard/pick-hero-card.tsx`
- `web/src/components/dashboard/pick-medium-card.tsx`

---

## Fix 4 — Enrich Top Candidate Cards

**Problem**: The top 3 candidate cards feel sparse. The API returns rich data (margin of safety, price upside, opportunity type, timing signal, data freshness, scored_at) but the cards only show ticker, name, sector, score, price, conviction badge, and factor signature.

**Changes**:

### Hero Card (Rank #1) — `pick-hero-card.tsx`

Add below the score, in a horizontal metadata row:

| Field | Display | Condition |
|-------|---------|-----------|
| Margin of Safety | Green badge: "MoS 24%" | `pick.margin_of_safety != null` |
| Price Upside | Text: "+18.4%" (green if positive, red if negative) | `pick.price_upside != null` |
| Opportunity Type | Subtle label: "Compounder" | `pick.opportunity_type != null` |
| Data Freshness | Dot indicator (green/amber/red) | `pick.data_freshness != null` |
| Scored At | Relative time: "2h ago" | `pick.scored_at != null` |

### Medium Cards (Ranks #2-3) — `pick-medium-card.tsx`

Add in a compact row below the score:

| Field | Display | Condition |
|-------|---------|-----------|
| Margin of Safety | Small badge: "MoS 24%" | `pick.margin_of_safety != null` |
| Opportunity Type | Small label | `pick.opportunity_type != null` |
| Scored At | Relative time | `pick.scored_at != null` |

### Compact Rows (#4+) — No changes

Already appropriately dense for scan-ability.

**Files**:
- `web/src/components/dashboard/pick-hero-card.tsx`
- `web/src/components/dashboard/pick-medium-card.tsx`
- `web/src/lib/format.ts` — add `formatRelativeTime()` utility if not already exported

**Types**: `PickSummary` already includes all needed fields (`margin_of_safety`, `price_upside`, `opportunity_type`, `data_freshness`, `scored_at`). No type changes needed.

---

## Fix 5 — Top Candidates Minimum Score Floor

**Problem**: The dashboard shows picks where conviction is `exceptional` or `high` regardless of raw score. A stock can pass conviction gates with a composite score of 46 (displayed as 46.82) while higher-scoring stocks with `medium` conviction are excluded.

**Changes**:

1. **`_fetch_picks_and_watchlist`** (`api/src/margin_api/routes/dashboard.py`): Add a minimum score filter to the picks query:

   ```python
   MINIMUM_PICK_SCORE = 5.0  # 0-10 DB scale → 50 on 0-100 UI scale
   ```

   Add `.where(V4Score.composite_score >= MINIMUM_PICK_SCORE)` to the picks query (line ~324). This ensures no pick appears in "Top Picks" with a displayed score below 50.

2. The fallback top-10 query (line ~337) should also apply this floor.

3. The frontend sort in `tiered-picks-list.tsx` (`b.score - a.score`) remains unchanged.

**Files**:
- `api/src/margin_api/routes/dashboard.py`

---

## Fix 6 — Smart Money Data Seeding

**Problem**: The Smart Money page shows "No manager data available" because the 13F pipeline hasn't been seeded.

**Fix**: Operational — not a code change. Run:
```bash
uv run python -m margin_api.cli backfill-13f --start-year 2013 --max-managers 300
```

Then verify `full_13f_ingest` cron job (daily 22:00 UTC) is active on the worker.

**No code changes required.** Frontend components (Fund Tracker, Market Signals, Clone Lab) are already wired to real API endpoints.

---

## Fix 7 — Backtesting Data Seeding

**Problem**: The Backtesting page shows "Backtest validation in progress" because no backtest has been computed.

**Fix**: Operational — trigger the first backtest:
```bash
uv run python -m margin_api.cli run-backtest
```

Or wait for `precompute_default_backtest` cron (Sunday 3AM UTC). Requires at least one completed scoring cycle.

**No code changes required.** All 16 backtesting components are wired to real endpoints.

---

## Fix 8 — OAuth Users Can't Set Password (Auth Bug)

**Problem**: OAuth users who click "Set Password" on the account page get a silent failure. The request to `/api/v1/auth/set-password` falls through to the catch-all auth proxy (`web/src/app/api/v1/auth/[...path]/route.ts`) which forwards to the backend **without auth headers**. The backend's `get_current_user_id` returns 401.

The `change-password` endpoint works because it has a dedicated route handler (`web/src/app/api/v1/auth/change-password/route.ts`) that injects `X-User-Id` from the session.

**Changes**:

1. **Create `web/src/app/api/v1/auth/set-password/route.ts`**: Dedicated route handler following the same pattern as `change-password/route.ts`:
   - Call `auth()` to get the session
   - Return 401 if no session
   - Forward request to backend with `X-User-Id` and `X-User-Email` headers
   - Proxy response back

2. **Create `web/src/app/api/v1/auth/remove-password/route.ts`**: Same bug, same fix. The `remove-password` endpoint also needs auth headers.

**Files**:
- `web/src/app/api/v1/auth/set-password/route.ts` (new)
- `web/src/app/api/v1/auth/remove-password/route.ts` (new)

---

## Testing Strategy

| Fix | Test approach |
|-----|---------------|
| 1. Avatar | Manual — sign in via OAuth, verify profile picture loads. Unit test: mock failed URL, verify dev warning. |
| 2. Sentiment | Unit test: render `FactorSignature` with null sentiment, verify no sentiment track rendered. Update existing tests. |
| 3. Score clipping | Visual — verify on narrow viewport. Snapshot test update if applicable. |
| 4. Card enrichment | Unit test: render `PickHeroCard`/`PickMediumCard` with full data, verify new fields appear. Test conditional hiding when fields are null. |
| 5. Score floor | API test: create V4Score with composite_score < 5.0 and conviction "high", verify it's excluded from dashboard response. |
| 6. Smart Money | Manual — run backfill, verify page populates. |
| 7. Backtesting | Manual — run backtest, verify page populates. |
| 8. Auth bug | Integration test: mock authenticated session, POST to `/api/v1/auth/set-password`, verify `X-User-Id` header forwarded. Unit test for `remove-password` route. |

---

## Out of Scope

- Custom avatar upload (user can already set this via account page)
- Redesigning the compact row layout
- Changing conviction gate logic in the engine (we're only adding a score floor at the dashboard query level)
- Smart Money or Backtesting frontend redesign
