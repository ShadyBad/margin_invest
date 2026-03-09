# Premium Redesign — Design Document

**Date:** 2026-03-08
**Status:** Approved
**Target user:** Prosumer now (serious individual investor, $19-49/mo), institutional-adjacent later (RIAs, small funds). Design must not exclude institutional evaluators.

## Context

Four independent design audits scored the product at 6.0-6.5/10 premium perception. A framework-based checklist scored 37/70 (borderline "Strong foundation" / "Premium"). An HNW trust audit scored 5.5/10.

All four audits converge on the same diagnosis: **strong design foundations (typography, color, positioning copy) with gaps in craft enforcement, institutional authority, and product visibility.**

All four independently recommend the same core change: **show the product instead of selling it.**

## Design Principles

1. **Show, don't tell.** The product is the pitch. Marketing copy explains; the product demonstrates.
2. **Absence of consumer signals > presence of institutional signals.** Don't build Bloomberg. Remove the things that make a fund manager think "consumer toy."
3. **System enforcement, not system definition.** The tokens exist. Enforce them everywhere.
4. **Restraint signals confidence.** Fewer sections, fewer font sizes, fewer competing signals.

## Architecture: Three Phases

### Phase 1: Kill Trust Destroyers (2-3 days)
### Phase 2: Product-Led Homepage (1-2 weeks)
### Phase 3: Craft Layer + Dashboard Depth (2-4 weeks, parallelizable)

---

## Phase 1: Kill Trust Destroyers

**Goal:** Remove every signal that makes a sophisticated user close the tab.

### 1.1 — Data Consistency Fix

**Problem:** Dashboard shows picks (e.g., ETSY score 72) that display as "ELIMINATED" on the asset detail page. The dashboard uses stale scoring data while asset detail runs fresh checks.

**Fix:** Dashboard must re-validate filter status before displaying picks. If a pick is now eliminated, either remove it from the picks grid or show it with a "Score changed — re-scoring" indicator. The dashboard and asset detail must never show contradictory states for the same ticker.

**Files:** `api/` scoring endpoint, `web/src/app/page.tsx` (homepage data fetch), `web/src/app/dashboard/page.tsx`

### 1.2 — Percentile Formatting

**Problem:** "99.5743287491814th percentile" — 13 decimal places displayed to users.

**Fix:** Round to 2 decimal places everywhere percentiles render. Apply to asset detail page, dashboard cards, and any API response rendered to UI.

**Files:** `web/src/app/asset/[ticker]/page.tsx`, any component rendering percentile values

### 1.3 — Remove LIVE Badge

**Problem:** Pulsing green dot + "LIVE" text in hero. Startup/streaming pattern flagged by all 4 audits.

**Fix:** Remove the entire eyebrow row (pulsing dot + "LIVE" label) from `hero-section.tsx`. The engine metadata above the hero card ("LIVE ENGINE OUTPUT — TODAY · UPDATED 9:20 PM EST · ENGINE V1.3.2") already communicates freshness. Keep the engine version stamp — it reads as engineering discipline.

**Files:** `web/src/components/landing/hero-section.tsx`

### 1.4 — Remove Comparison Table

**Problem:** Competitor names (Motley Fool, Seeking Alpha, Zacks) with strikethrough styling positions the product in the retail category and reads as insecure.

**Fix:** Delete the `DifferentiatorSection` component entirely from the homepage. The proof section already demonstrates differentiation through evidence. The methodology page is where depth comparison belongs.

**Files:** `web/src/components/landing/differentiator-section.tsx`, `web/src/components/landing/homepage-client.tsx`

### 1.5 — Copy Changes

| Location | Current | New |
|----------|---------|-----|
| Pricing section | "Founding members lock in this price forever. Pricing increases after launch." | Remove entirely |
| Homepage | "Methodology in development · Results are illustrative" | Remove from homepage. Keep on `/methodology` page only |
| Pricing CTAs | "Get Started" (all tiers) | "Search Any Ticker" (Scout), "Start Analyzing" (Analyst), "Start Building" (Portfolio) |
| Pricing section | "Scoring 3,000+ US equities daily for founding members" | "Scoring 3,056 US equities daily" |
| Hero subtext | "A deterministic capital allocation system that replaces narrative with structure. Search any ticker — the system shows you the quantitative evidence." | "A deterministic scoring engine for 3,056 US equities. No opinions. No overrides. Search one." |

**Files:** `web/src/components/landing/pricing-section.tsx`, `web/src/components/landing/hero-section.tsx`, homepage disclaimers

### 1.6 — Pipeline Cards Scroll Affordance

**Problem:** Horizontal scroll cards clipped on both edges with no visible indicator.

**Fix:** Add gradient fade masks on left/right edges showing content continues. Add subtle arrow buttons on hover for desktop. Consider converting to a responsive wrapping grid on mobile instead of horizontal scroll.

**Files:** `web/src/components/landing/engine-section.tsx`

---

## Phase 2: Product-Led Homepage

**Goal:** Replace the 10-section SaaS template with a product-first experience.

### 2.1 — New Homepage Architecture

**Current (10 sections):** Hero → Problem → Elimination Stat → Proof (4 cards) → Engine Pipeline → Positioning (Not For/For) → Comparison Table → Pricing → FAQ → Footer

**New (5 sections):** Product Hero → Authority Strip → Evidence Section → Pricing → Footer

**Sections removed:**
- Problem section — preaching to the converted
- Elimination stat (99.77% hero moment) — demonstrated naturally through product search
- Engine pipeline — moves to `/methodology`
- Positioning (Not For/For) — preachy tone, premium products self-select through experience
- Comparison table — killed in Phase 1
- FAQ — moves to `/faq` or `/support`

### 2.2 — Product Hero: Interactive Scoring Demo

Replace the current hero (headline + rotating card) with a full-width interactive search experience.

**Layout:**
- "Discipline. Engineered." headline (Instrument Serif, keep as-is but reduce max size to ~72px)
- Prominent search bar as the primary CTA — no "Get Started" button, the search IS the action
- Subtext: "A deterministic scoring engine for 3,056 US equities. No opinions. No overrides. Search one."
- Below search: clickable ticker chips — "Try: AAPL · TSLA · JNJ · COST · ETSY"

**Search result behavior:**
- Result appears inline on the homepage (no navigation)
- **Passing ticker:** Shows score, factor bars, price/target/MoS, tier badge. Link: "View full forensic report →" (goes to `/asset/TICKER`, login required for full depth)
- **Eliminated ticker:** Shows "ELIMINATED — Failed X of 6 filters" with filter names. Link: "See why it was eliminated →" (goes to `/asset/TICKER`)
- This IS the product demo. When someone searches TSLA and sees "ELIMINATED — Altman Z-Score: 0.82, threshold: 1.10" — the product has demonstrated its value without marketing copy.

**Removed:** Rotating candidate card, auto-carousel, LIVE badge.

**Files:** New component `web/src/components/landing/product-hero.tsx`, refactor `hero-search.tsx` for inline results

### 2.3 — Authority Strip

Single horizontal strip below the hero. Three columns of facts, no marketing copy.

| DATA SOURCES | COVERAGE | ENGINE |
|---|---|---|
| SEC EDGAR Filings | 3,056 equities | v1.3.2 |
| Earnings Transcripts | 11 GICS sectors | Scored daily |
| Daily Market Data | 6 elimination filters | |

**Style:** Monospace labels, compact, ~80px height. Maximum credibility per pixel.

**Optional fourth column:** Brief founder credential. One line. Deferred to user judgment.

**Files:** New component `web/src/components/landing/authority-strip.tsx`

### 2.4 — Evidence Section (Condensed Proof)

Replace 4 separate proof cards with a single unified panel.

**Contents:** Selectivity Funnel + Sector Breakdown + Correlation Heatmap in a 3-column layout within one surface. Remove Factor Transparency card (redundant with hero search results).

**Style:** Terminal/dashboard panel aesthetic — monospace header "SYSTEM OUTPUT — CURRENT SCORING CYCLE", subtle border, minimal decoration. Should feel like internal monitoring, not marketing.

**Footer:** "Structure replaces intuition with evidence. See full methodology →"

**Files:** Refactor `web/src/components/landing/proof-section.tsx`

### 2.5 — Pricing Changes

Keep 3-tier structure (Scout / Analyst / Portfolio). Changes:

- Replace headline "Invest in your process, not another guru." → "Start free. Full access from $19/month." (or remove headline entirely)
- Add institutional signal row below the 3 tiers: "Need API access or custom integration? Contact us →"
- Updated CTA text per Phase 1.5

**Files:** `web/src/components/landing/pricing-section.tsx`, `web/src/components/landing/pricing-tier-card.tsx`

### 2.6 — Footer Simplification

- Remove the trust badge strip (10px monospace text labels). Either design real badges with icons in a future iteration or remove entirely.
- Keep Product/Company link columns
- Keep bottom bar with copyright + tagline

**Files:** `web/src/components/landing/footer-section.tsx`

---

## Phase 3: Craft Layer + Dashboard Depth

**Goal:** Build the accumulation of details that moves the product from 6.5/10 to 8.5/10.

### 3.1 — Dashboard Rebuild

**New elements:**

1. **Personalized greeting + change summary:** "Good morning, Brandon. 2 scores changed since yesterday." Transforms the dashboard from data display to daily briefing.

2. **Score change deltas on pick cards:** "74 ▲2" instead of just "74." Green up arrow for increases, orange down for decreases. Requires storing/comparing previous scores.

3. **Left sidebar: Market Context panel.** Compact vertical strip showing market regime, sector coverage (X/11 scoring), universe stats, eligible count, active filter count. Consolidates currently scattered metadata.

4. **Recent Changes feed.** Chronological list: what changed, when, by how much. "EXPE: score 72 → 74 (+2) · Mar 8." Answers "what happened since I last looked?"

**Preserved:** Pick card layout (solid), watchlist table (functional), Portfolio Score top-right.

**Removed/relocated:** IngestionBanner → `/status` page. "Broad Opportunity" badge → sidebar context panel.

**Files:** `web/src/app/dashboard/page.tsx`, new components for sidebar, change feed, delta badges

### 3.2 — Design System Unification

**CSS token cleanup:**
- Remove all shadcn oklch variables from `globals.css` (`:root` lines 424-457, `.dark` lines 171-232)
- Remap any shadcn components to use custom tokens (`--color-bg-primary`, `--color-text-primary`, `--color-bg-elevated`)
- Remove or override `@import "shadcn/tailwind.css"` once all components are remapped
- Fix duplicated `@apply` declarations in `@layer base` (lines 460-467)

**Font size reduction — 4 levels only:**

| Level | Size | Usage |
|-------|------|-------|
| Display | clamp(40px, 6vw, 72px) | Hero headline only |
| Title | 20-24px | Page titles, section headers |
| Body | 15-16px | All body/card/table text |
| Caption | 12-13px | Metadata, labels, timestamps |

Kill `text-[10px]` and `text-[11px]` entirely. Minimum 12px.

**Opacity tokenization — 3 levels:**
```css
--color-accent-wash: rgba(26, 122, 90, 0.03);   /* background tints */
--color-accent-subtle: rgba(26, 122, 90, 0.08);  /* hover states, highlights */
--color-accent-medium: rgba(26, 122, 90, 0.15);  /* borders, active states */
```

Replace all hardcoded RGBA values in components with these tokens.

**Accent ≠ Bullish separation:**
```css
--color-accent: #1A7A5A;     /* brand, CTAs, interactive elements */
--color-bullish: #22C55E;    /* positive scores, upside, passing filters */
```

Different hues so users can distinguish "this is a button" from "this score is good."

**Files:** `web/src/app/globals.css`, all components with hardcoded RGBA values

### 3.3 — Interaction Polish

**Hover states:**

| Element | Behavior | Timing |
|---------|----------|--------|
| Pick cards | Border → accent-medium, shadow elevation | 150ms ease-out-expo |
| Watchlist rows | Background → accent-wash | 100ms |
| Pricing cards | Border shift, Y translate -2px | 200ms ease-out-expo |
| Nav links | Color → text-primary | 100ms |
| Buttons/CTAs | Background darkens 10% | 100ms |
| Footer links | Color → text-primary | 100ms |

**Skeleton loading:** Dashboard shows gray pulsing placeholders matching exact pick card and watchlist row dimensions while data loads. No spinner. No blank page.

**Transition timing cleanup:**
- Remove `duration-reveal` (600ms) and `duration-transition` (1000ms) — exceed 350ms ceiling
- Replace with: `duration-fast` (100ms), `duration-normal` (200ms), `duration-slow` (300ms)
- Keep `duration-ambient` for non-interactive ambient animations only

**Keyboard navigation:**
- `Cmd+K` → global ticker search
- Arrow keys → navigate watchlist rows
- `Enter` → open full report from pick card
- `Esc` → close overlays

**Files:** All interactive components, new `use-keyboard-nav.ts` hook, skeleton components

### 3.4 — Asset Detail Polish

- Round all numbers to 2 decimal places max
- Reformat raw filter diagnostic strings into structured mini-tables (columns: Check, Value, Threshold, Result)
- "Where EXPE Failed, Others Passed" — add median passing value as reference line on bar charts
- Replace gradient glow card borders with solid 1px borders + subtle elevation shadow

**Files:** `web/src/app/asset/[ticker]/page.tsx`, filter display components

### 3.5 — Light Mode Decision

**Recommendation:** Remove theme toggle. Ship dark-only. One excellent theme > two mediocre ones. Dark mode is the correct default for financial software. Light mode can be re-added when craft quality justifies two themes.

**Files:** `web/src/components/nav/theme-toggle.tsx`, `web/src/app/layout.tsx`, `globals.css` (dark overrides become defaults)

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Premium perception score (auditor consensus) | 6.0-6.5 | 8.0+ |
| Framework checklist score | 37/70 | 50+/70 |
| HNW trust score | 5.5/10 | 7.5+ |
| Homepage sections | 10 | 5 |
| Font sizes in active use | 8+ | 4 |
| Hardcoded RGBA values in components | ~15 | 0 |
| Interactive elements without hover states | ~60% | 0% |
| Data formatting bugs visible to users | 3+ | 0 |

## Risks

1. **Phase 2 hero search requires API changes.** The inline scoring demo needs an unauthenticated endpoint that returns a summary score or elimination result for any ticker. Currently `/api/v1/dashboard` requires auth. A public `/api/v1/score-preview/{ticker}` endpoint may be needed.
2. **Score change deltas (Phase 3.1) require historical comparison.** Check if `score_history` API endpoint exists and returns previous scores for delta calculation.
3. **Removing shadcn tokens (Phase 3.2) may break components that depend on them.** Audit all shadcn component usage before removing variables.
4. **Dark-only mode (Phase 3.5) may alienate users who prefer light mode.** Monitor user feedback after shipping.

## Dependencies

- Phase 1 has no dependencies — can start immediately
- Phase 2.2 (product hero) depends on a public score-preview API endpoint
- Phase 3.1 (dashboard deltas) depends on score history API availability
- Phase 3.2 (CSS cleanup) should happen before Phase 3.3 (interaction polish) to avoid double-work
