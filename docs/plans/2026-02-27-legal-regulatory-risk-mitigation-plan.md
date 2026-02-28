# Legal & Regulatory Risk Mitigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement all Tier 1 and Tier 2 codebase changes from the legal risk assessment to eliminate critical regulatory exposure before launch.

**Architecture:** Cross-cutting changes across engine (enum renaming), API (schema updates), and web (UI text, new pages, acknowledgment flows, disclaimer upgrades). Database column names are NOT renamed (would require migration + data backfill) — only display values change.

**Tech Stack:** Python/Pydantic (engine + API), Next.js 15/React 19/TypeScript (web), Vitest (web tests), pytest (Python tests)

**Design doc:** `docs/plans/2026-02-27-legal-regulatory-risk-assessment-design.md`

---

## Group A: Engine Signal & Conviction Renaming

### Task 1: Rename Signal enum values

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:23-29`
- Test: `engine/tests/test_scoring_models.py`, `engine/tests/models/test_scoring.py`

**Step 1: Update Signal enum values**

Change the enum string values (keep the Python names for backward compat in code):

```python
class Signal(StrEnum):
    BUY = "strong"
    HOLD = "stable"
    WATCH = "emerging"
    SELL = "weak"
    URGENT_SELL = "failed"
    NO_ACTION = "neutral"
```

**Step 2: Run engine tests to find all breakages**

Run: `uv run pytest engine/tests/ -x -v 2>&1 | head -80`

Fix every test that asserts old string values ("buy", "hold", "sell", "watch", "urgent_sell", "no_action") to use the new values ("strong", "stable", "weak", "emerging", "failed", "neutral"). This will touch many test files across engine/tests/ — grep for the old values and update all assertions.

**Key test files to update (non-exhaustive — grep will find all):**
- `engine/tests/test_scoring_models.py`
- `engine/tests/models/test_scoring.py`
- `engine/tests/scoring/test_v3_cascade.py`
- `engine/tests/scoring/test_v4_pipeline.py`
- `engine/tests/scoring/test_dual_track.py`
- `engine/tests/scoring/test_composite.py`
- `engine/tests/scoring/quantitative/test_price_targets.py`
- `engine/tests/scoring/test_position_sizing.py`
- Any other files found by `grep -r '"buy"\|"sell"\|"hold"\|"watch"\|"urgent_sell"\|"no_action"' engine/tests/`

**Step 3: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All ~2621 tests pass

**Step 4: Commit**

```bash
git add engine/
git commit -m "feat(engine): rename Signal enum values to non-advisory language

BUY→strong, HOLD→stable, WATCH→emerging, SELL→weak,
URGENT_SELL→failed, NO_ACTION→neutral. Eliminates directive
investment language per legal risk assessment."
```

---

### Task 2: Rename ConvictionLevel enum to CompositeTier

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:16-20`
- Modify: `engine/src/margin_engine/models/__init__.py` (re-export)
- Test: All engine test files referencing ConvictionLevel

**Step 1: Rename the enum class and values**

```python
class CompositeTier(StrEnum):
    EXCEPTIONAL = "exceptional"  # composite_raw_score >= 79
    HIGH = "high"  # composite_raw_score >= 72
    MEDIUM = "medium"  # composite_raw_score >= 65
    NONE = "none"  # < 65
```

Note: The string values ("exceptional", "high", etc.) stay the same — they are stored in the database. Only the class name and property name change.

**Step 2: Rename the property on CompositeScore**

In `scoring.py`, rename the `conviction_level` property to `composite_tier`:

```python
@property
def composite_tier(self) -> CompositeTier:
    if self.composite_raw_score >= 79.0:
        return CompositeTier.EXCEPTIONAL
    ...
```

Also add a backward-compat alias:

```python
@property
def conviction_level(self) -> CompositeTier:
    """Backward-compat alias — use composite_tier instead."""
    return self.composite_tier
```

**Step 3: Update all imports and references across engine/**

Search for `ConvictionLevel` and `conviction_level` across all engine files:
- `engine/src/margin_engine/models/__init__.py` — update re-export
- `engine/src/margin_engine/scoring/position_sizing.py`
- `engine/src/margin_engine/scoring/quantitative/price_targets.py`
- `engine/src/margin_engine/scoring/dual_track.py`
- `engine/src/margin_engine/scoring/v3_cascade.py`
- `engine/src/margin_engine/scoring/v3_pipeline.py`
- `engine/src/margin_engine/scoring/v3_thresholds.py`
- `engine/src/margin_engine/scoring/v4_pipeline.py`
- `engine/src/margin_engine/scoring/v4_orchestrator.py`
- `engine/src/margin_engine/ml/ensemble_override.py`
- `engine/src/margin_engine/optimization/models.py`
- All corresponding test files

Strategy: Use find-and-replace `ConvictionLevel` → `CompositeTier` across engine/src/ and engine/tests/. Keep the `conviction_level` backward-compat property alias on CompositeScore so API code doesn't break until Task 3.

**Step 4: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All pass

**Step 5: Commit**

```bash
git add engine/
git commit -m "refactor(engine): rename ConvictionLevel to CompositeTier

Class rename + property rename (conviction_level → composite_tier)
with backward-compat alias. Removes advisory 'conviction' language
per legal risk assessment."
```

---

### Task 3: Update API schemas and routes for new naming

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py`
- Modify: `api/src/margin_api/schemas/dashboard.py`
- Modify: `api/src/margin_api/schemas/score_history.py`
- Modify: `api/src/margin_api/schemas/thirteenf.py`
- Modify: `api/src/margin_api/routes/scores.py`
- Modify: `api/src/margin_api/routes/dashboard.py`
- Modify: `api/src/margin_api/routes/v3_scores.py`
- Modify: `api/src/margin_api/routes/transparency.py`
- Modify: `api/src/margin_api/routes/backtest.py`
- Modify: `api/src/margin_api/routes/correlations.py`
- Modify: `api/src/margin_api/routes/universe.py`
- Modify: `api/src/margin_api/routes/thirteenf.py`
- Test: `api/tests/`

**Step 1: Update API schemas**

In `schemas/scores.py`, rename the response field:
- `conviction_level: str` → `composite_tier: str`
- `signal: str` remains (the field name "signal" is fine — it's the VALUES that changed)

In `schemas/dashboard.py`, same pattern.

**Step 2: Update routes that build responses**

Update all routes that construct ScoreResponse or PickSummary objects to use `composite_tier` instead of `conviction_level`. The engine now exposes `composite_tier` property, and the backward-compat `conviction_level` alias still works, so this is a field rename in the response dict.

**Step 3: Update API imports**

Replace `from margin_engine.models import ConvictionLevel` with `from margin_engine.models import CompositeTier` across all API source files.

**Step 4: Update API tests**

Grep for `conviction_level` and old signal values ("buy", "sell", etc.) across `api/tests/` and update to new field names and values.

**Step 5: Run full API test suite**

Run: `uv run pytest api/tests/ -v --tb=short --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All ~1656 tests pass

**Step 6: Commit**

```bash
git add api/
git commit -m "refactor(api): update schemas and routes for CompositeTier + new signal values

API responses now use composite_tier (was conviction_level) and
signal values strong/stable/emerging/weak/failed/neutral."
```

---

## Group B: Web Signal & Conviction Display Renaming

### Task 4: Update web TypeScript types and API client

**Files:**
- Modify: `web/src/lib/api/types.ts`
- Modify: `web/src/lib/api/scores.ts`
- Modify: `web/src/lib/api/backtest.ts`
- Test: `web/src/lib/api/__tests__/scores.test.ts`

**Step 1: Update TypeScript interfaces**

In `types.ts`:
- `conviction_level: string` → `composite_tier: string`
- Update `SignalTransition` if it has `previous_conviction`/`new_conviction` fields

**Step 2: Update API client functions**

Any function that reads `conviction_level` from API responses should now read `composite_tier`.

**Step 3: Update tests**

Run: `cd web && npx vitest run src/lib/api/ --reporter=verbose`

**Step 4: Commit**

```bash
git add web/src/lib/
git commit -m "refactor(web): update API types for composite_tier + new signal values"
```

---

### Task 5: Update signal display components

**Files:**
- Modify: `web/src/components/ui/signal-badge.tsx` — update style keys
- Modify: `web/src/components/ui/action-pill.tsx` — update labels and keys
- Modify: `web/src/components/dashboard/signal-timeline.tsx` — update keys
- Modify: `web/src/components/asset-detail/hero-header.tsx` — update signal color map + label
- Test: All associated test files

**Step 1: Update ActionPill labels**

```typescript
const pillConfig: Record<string, { bg: string; text: string; label: string }> = {
  strong: { bg: "bg-bullish/10", text: "text-bullish", label: "STRONG" },
  stable: { bg: "bg-accent/10", text: "text-accent", label: "STABLE" },
  weak: { bg: "bg-warning/10", text: "text-warning", label: "WEAK" },
  emerging: { bg: "bg-text-secondary/10", text: "text-text-secondary", label: "EMERGING" },
  failed: { bg: "bg-bearish/10", text: "text-bearish", label: "FAILED" },
  neutral: { bg: "bg-bg-secondary", text: "text-text-tertiary", label: "—" },
}
```

**Step 2: Update SignalBadge styles**

Same pattern — update keys from old signal values to new ones.

**Step 3: Update SignalTimeline color map**

**Step 4: Update HeroHeader signal colors**

Replace keys: `buy` → `strong`, `hold` → `stable`, `sell` → `weak`, `watch` → `emerging`, `"urgent sell"` → `failed`

**Step 5: Run component tests**

Run: `cd web && npx vitest run src/components/ui/ src/components/dashboard/signal-timeline --reporter=verbose`
Fix any failing assertions.

**Step 6: Commit**

```bash
git add web/src/components/
git commit -m "refactor(web): update signal display components to non-advisory labels

BUY→STRONG, HOLD→STABLE, WATCH→EMERGING, SELL→WEAK,
URGENT_SELL→FAILED, NO_ACTION→neutral dash."
```

---

### Task 6: Update conviction display components to "composite tier"

**Files:**
- Modify: `web/src/components/ui/conviction-badge.tsx` — rename to composite-badge or update display text
- Modify: `web/src/components/asset-detail/hero-header.tsx` — update conviction label
- Modify: `web/src/components/asset-detail/conviction-engine.tsx` — rename heading
- Modify: `web/src/components/dashboard/stock-card.tsx` — update conviction references
- Modify: `web/src/components/dashboard/portfolio-conviction.tsx` — rename
- Modify: `web/src/components/dashboard/picks-grid.tsx`
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx`
- Modify: `web/src/components/dashboard/panel/executive-header.tsx`
- Modify: `web/src/components/dashboard/panel/score-history-table.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx`
- Modify: `web/src/components/asset-detail/hypothetical-scores.tsx`
- Modify: `web/src/components/asset-detail/ml-audit-panel.tsx`
- Modify: `web/src/components/landing/hero-candidate-card.tsx`
- Modify: `web/src/components/landing/candidate-data.ts`
- Modify: `web/src/components/landing/types.ts`
- Modify: `web/src/components/landing/engine-section.tsx`
- Modify: `web/src/components/methodology/sections/conviction-section.tsx`
- Modify: `web/src/lib/formula-definitions.ts`
- Test: All associated test files

**Step 1: Update ConvictionBadge component**

Rename file `conviction-badge.tsx` → keep filename but change display:
- Change heading label from "Conviction" to "Composite" or "Tier"
- `displayNames` map: keep values ("Exceptional", "High", "Medium", "None") — these are tier labels, not advisory

**Step 2: Update HeroHeader**

Change the metric label from "Conviction" to "Composite Tier":
```tsx
<div className="text-xs text-text-tertiary uppercase tracking-wide mb-1">Composite Tier</div>
```

**Step 3: Update ConvictionEngine component**

Change heading from "Conviction Engine" to "Composite Engine" or "Score Engine":
```tsx
<h2 className="text-lg font-semibold text-text-primary">Score Engine</h2>
```

Change "Conviction Tracks" to "Scoring Tracks".

**Step 4: Update all other components**

Replace "Conviction" display text with "Composite" or "Score" throughout. Replace prop names like `conviction_level` → `composite_tier` where they map to API response fields.

**Step 5: Update formula-definitions.ts**

Any formula definition referencing "conviction" in its display text should be updated.

**Step 6: Update methodology sections**

`conviction-section.tsx` heading and content — rename from "Conviction" to "Composite Score" or "Score Synthesis".

**Step 7: Run full web test suite**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Fix all failing assertions. This will touch many test files — grep for "conviction", "Conviction", "conviction_level" across web/src/__tests__/ and all `__tests__` directories.

**Step 8: Commit**

```bash
git add web/
git commit -m "refactor(web): rename all conviction references to composite/score terminology

Conviction Engine→Score Engine, Conviction Tracks→Scoring Tracks,
conviction_level→composite_tier throughout all components."
```

---

## Group C: Marketing Copy Remediation

### Task 7: Update landing page marketing copy

**Files:**
- Modify: `web/src/components/landing/hero-section.tsx:72-78`
- Modify: `web/src/components/landing/positioning-section.tsx`
- Modify: `web/src/components/landing/proof-section.tsx:76`
- Modify: `web/src/components/landing/pricing-section.tsx:29`
- Modify: `web/src/components/landing/engine-section.tsx` (if "Conviction" appears)
- Test: Associated test files

**Step 1: Replace hero headline**

Replace "Conviction. Engineered." with a non-advisory headline. Suggestions:
- "Structure. Engineered."
- "Discipline. Engineered."
- "Clarity. Engineered."

Replace "we'll show you exactly what the math says" with:
- "Search any ticker — the system shows you the quantitative evidence."

**Step 2: Replace proof section headline**

Replace "Structure creates measurable advantage." with:
- "Structure creates measurable discipline."
- Or: "Structure replaces intuition with evidence."

**Step 3: Replace pricing tier feature name**

Replace "Conviction alerts" with "Score alerts" or "Factor alerts" in the Portfolio tier features.

**Step 4: Update positioning section**

Replace "Narrative-driven conviction" in the "Not for" list with "Narrative-driven investing" or similar.

**Step 5: Run landing page tests**

Run: `cd web && npx vitest run src/components/landing/ --reporter=verbose`
Fix any assertions that check for old copy.

**Step 6: Commit**

```bash
git add web/src/components/landing/
git commit -m "fix(web): replace advisory marketing copy with analytical framing

Removes 'conviction', 'advantage', 'exactly' language per legal
risk assessment. Replaces with structure/discipline/evidence framing."
```

---

## Group D: Legal Pages & Acceptance Flows

### Task 8: Publish Terms of Service page

**Files:**
- Create: `web/src/app/terms/page.tsx`
- Modify: `web/src/components/layout/footer.tsx` — add Terms link
- Modify: `web/src/components/landing/footer-section.tsx` — add Terms link
- Test: Create `web/src/app/terms/__tests__/page.test.tsx`

**Step 1: Create Terms of Service page**

Create `/terms` route. Use Version 2 (Balanced) from `docs/legal/2026-02-22-terms-of-service-draft.md` as content. Render as a static page with the same layout pattern as `/legal` (centered content, section headings, readable typography).

Replace all placeholder items (entity name, email, etc.) with:
- Entity: "Margin Invest" (until LLC formed, then update)
- Contact: legal@margin-invest.com
- Governing law: Delaware (anticipating Delaware LLC)

**Step 2: Write test**

Test that the page renders and contains key sections (Eligibility, Service Description, Subscriptions, Limitation of Liability).

**Step 3: Update footer links**

Add "Terms" link to both footer components, linking to `/terms`.

**Step 4: Run tests**

Run: `cd web && npx vitest run src/app/terms/ src/components/layout/ --reporter=verbose`

**Step 5: Commit**

```bash
git add web/src/app/terms/ web/src/components/layout/ web/src/components/landing/footer-section.tsx
git commit -m "feat(web): publish Terms of Service page at /terms

Implements balanced version from legal drafts. Adds footer link."
```

---

### Task 9: Publish Privacy Policy page

**Files:**
- Create: `web/src/app/privacy/page.tsx`
- Modify: `web/src/components/layout/footer.tsx` — add Privacy link
- Modify: `web/src/components/landing/footer-section.tsx` — add Privacy link
- Test: Create `web/src/app/privacy/__tests__/page.test.tsx`

**Step 1: Create Privacy Policy page**

Same pattern as Task 8. Use Version 2 (Balanced) from `docs/legal/2026-02-22-privacy-policy-draft.md`. Replace placeholders with same values.

**Step 2: Write test**

Test that page renders and contains key sections (Information We Collect, How We Use It, How We Share It, Your Rights, Security).

**Step 3: Update footer links**

Add "Privacy" link to both footer components.

**Step 4: Run tests and commit**

```bash
git add web/src/app/privacy/ web/src/components/layout/ web/src/components/landing/footer-section.tsx
git commit -m "feat(web): publish Privacy Policy page at /privacy

Implements balanced version from legal drafts. Adds footer link.
Required for CCPA/CalOPPA compliance and Stripe ToS."
```

---

### Task 10: Add ToS acceptance checkbox to registration

**Files:**
- Modify: `web/src/components/login/login-card.tsx`
- Test: Modify existing login-card tests or create new ones

**Step 1: Add checkbox to signup form**

In the signup mode of login-card.tsx, add a required checkbox before the "Create Account" button:

```tsx
<label className="flex items-start gap-2 text-sm text-text-secondary">
  <input
    type="checkbox"
    required
    checked={tosAccepted}
    onChange={(e) => setTosAccepted(e.target.checked)}
    className="mt-0.5"
    data-testid="tos-checkbox"
  />
  <span>
    I agree to the{" "}
    <a href="/terms" target="_blank" className="text-accent hover:underline">Terms of Service</a>
    {" "}and{" "}
    <a href="/privacy" target="_blank" className="text-accent hover:underline">Privacy Policy</a>
  </span>
</label>
```

Add `tosAccepted` state. Disable the submit button when `!tosAccepted`.

**Step 2: Write tests**

- Test that checkbox is present in signup mode
- Test that submit is disabled when unchecked
- Test that submit works when checked

**Step 3: Run tests and commit**

```bash
git add web/src/components/login/
git commit -m "feat(web): add Terms + Privacy acceptance checkbox to registration

Users must accept ToS and Privacy Policy before creating account.
Creates enforceable click-through agreement."
```

---

### Task 11: Add "not investment advice" acknowledgment gate

**Files:**
- Create: `web/src/components/modals/analysis-disclaimer-modal.tsx`
- Modify: `web/src/app/layout.tsx` — add modal to root layout
- Create: `web/src/components/modals/__tests__/analysis-disclaimer-modal.test.tsx`

**Step 1: Create the disclaimer modal component**

Pattern: Follow MfaRequiredModal exactly. Create a modal that:
- Listens for a custom `analysis-disclaimer-required` window event
- Shows a modal with the disclaimer text:
  - Title: "Quantitative Analysis Tool"
  - Body: "Margin Invest provides quantitative factor analysis for informational purposes only. It does not provide investment advice, recommendations, or fiduciary guidance. You are solely responsible for your own investment decisions. Scores and signals reflect historical and current factor data — they are not predictions of future performance."
  - Primary CTA: "I Understand" — sets `localStorage.setItem("disclaimer_acknowledged", "true")` and closes modal
  - No dismiss/go-back — user must click "I Understand"
- Checks `localStorage` on mount — if already acknowledged, never fires

**Step 2: Integrate trigger**

The modal should be triggered before the first score/dashboard view. Options:
- Dispatch `analysis-disclaimer-required` event from dashboard page on mount if `localStorage.getItem("disclaimer_acknowledged")` is falsy
- Or: Add a wrapper component that checks localStorage and dispatches if needed

**Step 3: Add to root layout**

Add `<AnalysisDisclaimerModal />` alongside `<MfaRequiredModal />` in layout.tsx.

**Step 4: Write tests**

Follow MfaRequiredModal test pattern:
- Not visible initially
- Appears when event dispatched
- "I Understand" button sets localStorage and closes
- Does not reappear after acknowledgment (mock localStorage)

**Step 5: Run tests and commit**

```bash
git add web/src/components/modals/ web/src/app/layout.tsx
git commit -m "feat(web): add one-time 'not investment advice' acknowledgment modal

Users must acknowledge disclaimer before viewing scores.
Stored in localStorage. Defeats 'I thought it was advice' claims."
```

---

## Group E: Backtesting Disclaimer Upgrades

### Task 12: Add HYPOTHETICAL PERFORMANCE labels and expanded disclaimers

**Files:**
- Modify: `web/src/components/landing/proof-section.tsx`
- Modify: `web/src/components/landing/proof-historical-chart.tsx`
- Modify: `web/src/app/backtesting/page.tsx`
- Modify: `web/src/components/smart-money/clone-lab.tsx`
- Modify: `web/src/components/backtesting/cost-disclosure.tsx`
- Test: Associated test files

**Step 1: Create a shared disclaimer constant**

Create or add to an existing constants file:

```typescript
export const HYPOTHETICAL_DISCLAIMER =
  "HYPOTHETICAL PERFORMANCE RESULTS HAVE MANY INHERENT LIMITATIONS. " +
  "No representation is made that any portfolio will or is likely to achieve profits or losses similar to those shown. " +
  "There are frequently sharp differences between hypothetical performance results and the actual results achieved by any particular trading program. " +
  "Hypothetical trading does not involve financial risk, and no hypothetical trading record can completely account for the impact of financial risk in actual trading. " +
  "All results shown are backtested using point-in-time data and include estimated transaction costs. " +
  "Actual results may differ materially."
```

**Step 2: Update proof-historical-chart.tsx**

Add a "HYPOTHETICAL PERFORMANCE" badge directly above or on the chart:
```tsx
<div className="text-xs font-mono uppercase tracking-widest text-warning/80 mb-2">
  Simulated Performance — Not Actual Trading Results
</div>
```

Replace the one-line disclaimer with the full `HYPOTHETICAL_DISCLAIMER` text, styled as a visible callout (not collapsed, not fine print).

**Step 3: Update proof-section.tsx**

Expand the existing disclaimer. Add "HYPOTHETICAL" labeling.

**Step 4: Update backtesting/page.tsx**

Add "HYPOTHETICAL RESULTS" header above the metrics section. Replace the fallback disclaimer text with the full disclaimer. Ensure the disclaimer is visually proximate to the performance data (same viewport section, not separated).

**Step 5: Update clone-lab.tsx**

Add "HYPOTHETICAL" labeling. Existing disclaimer text is adequate but add the hypothetical label.

**Step 6: Make cost-disclosure non-collapsible**

If the component is currently collapsible (accordion/details), change it to always-visible. Or add an inline summary line showing transaction cost assumption.

**Step 7: Run tests and fix assertions**

Run: `cd web && npx vitest run src/components/landing/ src/app/backtesting/ src/components/smart-money/ src/components/backtesting/ --reporter=verbose`

**Step 8: Commit**

```bash
git add web/src/
git commit -m "feat(web): add HYPOTHETICAL PERFORMANCE labels and expanded disclaimers

All backtest charts now labeled 'Simulated Performance' with
NFA/CFTC-standard hypothetical performance disclaimer co-located
with performance data. Cost disclosure made non-collapsible."
```

---

## Group F: Guide & Content Updates

### Task 13: Update guides and methodology content for new terminology

**Files:**
- Modify: `web/src/content/guides/conviction-and-tracks.mdx`
- Modify: `web/src/content/guides/scoring-factors.mdx`
- Modify: `web/src/content/guides/getting-started.mdx`
- Modify: `web/src/content/guides/analyzing-a-stock.mdx`
- Modify: `web/src/content/guides/reading-the-dashboard.mdx`
- Modify: `web/src/content/guides/glossary.mdx`
- Modify: `web/src/content/guides/building-a-portfolio.mdx`
- Modify: `web/src/content/guides/institutional-signals.mdx`
- Modify: `web/src/content/guides/weekly-review.mdx`
- Modify: `web/src/content/guides/data-freshness.mdx`
- Modify: `web/src/content/guides/ml-pipeline.mdx`
- Modify: `web/src/components/methodology/sections/conviction-section.tsx`
- Modify: `web/src/components/methodology/sections/outputs-section.tsx`
- Modify: `web/src/components/methodology/sections/scoring-section.tsx`
- Modify: `web/src/components/methodology/sections/hero-section.tsx`
- Modify: `web/src/components/methodology/sections/pipeline-section.tsx`
- Modify: `web/src/app/methodology/page.tsx`
- Modify: `web/src/components/support/support-data.ts`
- Modify: `web/src/app/api-docs/page.tsx`
- Modify: `web/src/app/onboarding/page.tsx`
- Modify: `web/src/components/onboarding/onboarding-flow.tsx`
- Test: `web/src/components/methodology/__tests__/sections.test.tsx`, `web/src/components/guides/__tests__/guide-category-tabs.test.tsx`

**Step 1: Bulk rename in guides**

Replace across all .mdx files:
- "conviction" → "composite score" (where referring to the metric)
- "Conviction Engine" → "Score Engine"
- "BUY signal" → "STRONG signal"
- "SELL signal" → "WEAK signal"
- "HOLD" → "STABLE"
- "WATCH" → "EMERGING"
- "URGENT_SELL" / "URGENT SELL" → "FAILED"
- "Conviction alerts" → "Score alerts"

Be careful: "conviction" in natural language ("my personal conviction") can stay — only change where it refers to the platform's conviction level/engine.

**Step 2: Rename conviction-and-tracks.mdx**

The guide file itself may need renaming. If the filename is used in routing, update accordingly. The content should reference "Composite Score and Scoring Tracks" instead of "Conviction and Tracks".

**Step 3: Update methodology sections**

Same find-and-replace for conviction → composite score, signal renames.

**Step 4: Update support-data.ts**

FAQ entries mentioning signals or conviction levels.

**Step 5: Update onboarding**

Any onboarding copy referencing conviction or signal names.

**Step 6: Update api-docs**

If the API docs page shows field names or example responses, update to reflect new names.

**Step 7: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`

**Step 8: Commit**

```bash
git add web/
git commit -m "docs(web): update all guides, methodology, and support content for new terminology

Replaces conviction→composite score, BUY→STRONG, SELL→WEAK
throughout all user-facing documentation and guides."
```

---

## Group G: Legal Page Update

### Task 14: Update existing /legal page with enhanced disclaimers

**Files:**
- Modify: `web/src/app/legal/page.tsx`
- Test: Existing legal page tests

**Step 1: Update the Investment Disclaimer section**

Add the "What Margin Invest IS / IS NOT" table from the legal drafts (Deliverable B). Add to Section 2:

```
Margin Invest IS:
- A quantitative analysis tool
- A software platform with automated scoring models
- An informational resource
- A backtested data provider

Margin Invest IS NOT:
- A financial adviser or investment adviser
- A broker-dealer
- A custodian of your assets
- A guarantee of investment returns
- A replacement for professional financial advice
- A financial product or security
- A margin or leverage provider
- A fiduciary
```

**Step 2: Add cross-links**

Add links to the new /terms and /privacy pages from the legal page.

**Step 3: Update signal/conviction terminology**

Replace any references to old signal names or "conviction" with new terminology.

**Step 4: Run tests and commit**

```bash
git add web/src/app/legal/
git commit -m "feat(web): enhance /legal page with IS/IS NOT table and cross-links

Adds explicit platform classification table and links to
Terms of Service and Privacy Policy pages."
```

---

## Execution Order & Dependencies

```
Group A (Engine):  T1 → T2 → T3 (sequential — each builds on prior)
Group B (Web UI):  T4 → T5, T6 (T5 and T6 can be parallel after T4)
Group C (Copy):    T7 (independent)
Group D (Legal):   T8 → T9 → T10 → T11 (sequential)
Group E (Backtest): T12 (independent)
Group F (Content): T13 (after T1 and T2 for terminology)
Group G (Legal):   T14 (after T8 and T9 for cross-links)

Full dependency chain:
T1 → T2 → T3 → T4 → T5, T6 (parallel)
T7 (anytime)
T8 → T9 → T10 → T11
T12 (anytime)
T1, T2 → T13
T8, T9 → T14
```

## Verification

After all tasks complete:

```bash
uv run pytest engine/tests/ -v --tb=short    # ~2621 tests
uv run pytest api/tests/ -v --tb=short --ignore=api/tests/services/test_xbrl_parser.py  # ~1656 tests
cd web && npx vitest run --reporter=verbose   # ~1223 tests
```

All three suites must pass green before final commit.

## Out of Scope (External Actions — Not Codebase)

These items from the design doc require external action, not code:
- Form LLC (Delaware or Wyoming)
- Open business bank account
- Obtain E&O / D&O / cyber insurance
- Engage securities attorney for publisher's exclusion opinion letter
- Document data breach incident response plan
- Monitor state blue sky law requirements
