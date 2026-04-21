# Detail Page, Data Pipeline and Methodology Overhaul - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan. Steps use checkbox syntax for tracking.

**Goal:** Fix broken signals/scores, redesign detail page UX (timing signal hero, filter pills, max position context), unblock shadow portfolio, add smart money market pulse, fix methodology page visuals, and color reference guides.

**Architecture:** API-layer signal recomputation replaces broken model_dump() fallback. Frontend UX changes are component-level refactors. Shadow portfolio worker removes governance filter. Market pulse is a new aggregation endpoint over existing accumulation_signals data. Methodology fixes are CSS plus static data corrections.

**Spec:** `docs/superpowers/specs/2026-04-19-detail-pipeline-methodology-overhaul-design.md`

---

## Task Summary (12 tasks)

Each task below has full code, test steps, and commit instructions available in the conversation context where this plan was created. The spec document contains all design details.

### Task 1: Fix Signal Recomputation in API
- Create `api/tests/routes/test_signal_recompute.py` with 9 tests
- Add `_recompute_signal()` to `api/src/margin_api/routes/scores.py`
- Replace line 229 broken fallback with recomputation from tier plus margin_of_safety
- Signal mapping: exceptional/high with positive margin returns "strong", negative returns "stable", medium returns "emerging", none returns "neutral"

### Task 2: Define color-value CSS Variable
- Add `--color-value: #14B8A6` to `web/src/app/globals.css` theme block
- Fixes invisible Value bars in methodology Stage 3 example and Stage 7 factor breakdown

### Task 3: Elevate Timing Signal to Hero Position
- Add `timingSignal` prop to `instrument-header.tsx`, render color-coded pill below tier badge
- Colors: buy_now uses green (bullish), add_on_pullback uses amber (warning), wait_for_catalyst uses muted
- Pass from `asset-detail-view.tsx`, remove from `conviction-engine.tsx` to avoid duplication
- 4 tests in `__tests__/instrument-header.test.tsx`

### Task 4: Elimination Gauntlet to Filter Pills
- Refactor `filter-card.tsx` into FilterPill (compact rounded pill) plus FilterDetail (expandable)
- Rewrite `elimination-gauntlet.tsx` with pill strip plus click-to-expand
- Pills show: icon plus short name plus value, colored border (green/red/amber)
- 3 tests in `__tests__/elimination-gauntlet.test.tsx`

### Task 5: Remove Growth Stage Weights plus Expand Max Position
- Strip `scoring-pillars.tsx` of growth stage text, remove `growthStage` prop
- Expand max position in `conviction-engine.tsx`: show Quarter-Kelly label, dollar example per 50K portfolio, risk context

### Task 6: Sentiment PENDING State
- Update `factor-profile.tsx` FactorBar: show "PENDING" instead of dash for null sentiment
- Dashed border track at 30% opacity, tooltip explaining NLP pipeline requirement

### Task 7: Unblock Shadow Portfolio Worker
- Extract `_build_shadow_positions()` helper in `workers.py`
- Remove `.where(V4Score.published.is_(True))` filter
- Add `source` field ("published" or "staged") to each position
- 2 tests in `test_shadow_portfolio_fix.py`

### Task 8: Smart Money Market Pulse Backend
- Add `SectorFlowItem`, `ConsensusPick`, `MarketPulseResponse` schemas to `schemas/thirteenf.py`
- Add `GET /analytics/market-pulse` endpoint to `routes/thirteenf.py`
- Computes: breadth pct, sector flows, consensus picks (top 5), flow trend (QoQ)
- All derived from existing accumulation_signals plus assets tables
- 2 tests in `test_market_pulse.py`

### Task 9: Smart Money Market Pulse Frontend
- Add types plus `getMarketPulse()` to `lib/api/thirteenf.ts`
- Create `market-pulse.tsx` component: 4-metric grid (breadth, sector rotation, consensus, flow trend)
- Wire into `market-signals.tsx` at top of tab
- 4 tests in `__tests__/market-pulse.test.tsx`

### Task 10: Methodology Page Visual Fixes
- `filter-funnel.tsx`: Replace accent-subtle with explicit rgba plus left border accent
- `candidate-journey-chart.tsx`: strokeWidth 2 to 3, add SVG glow filter, dot radius 4 to 5, add score labels

### Task 11: Reference Guide Color Amber
- Update `guide-card.tsx` CATEGORY_COLORS/TEXT/BG for Reference: gray to #D4A843 (amber)
- Creates palette: Concepts=blue, Workflows=teal, Reference=amber

### Task 12: Run Full Test Suite
- API: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
- Engine: `uv run pytest engine/tests/ -v`
- Web: `cd web && npx vitest run`
- Lint: `uv run ruff check --fix . && uv run ruff format .`