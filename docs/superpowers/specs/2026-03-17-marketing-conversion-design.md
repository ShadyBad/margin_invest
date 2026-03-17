# Marketing & Conversion Implementation — Design Spec

**Date**: 2026-03-17
**Scope**: Phases 1-3 (Tasks 1-12) — frontend/conversion work
**Out of scope**: Email system, Smart Money backend — separate future specs

## Problem

The product itself is strong (design system, forensic transparency, methodology depth) but the conversion infrastructure has critical gaps: navbar CTA is hardcoded to null, authenticated users can't navigate to paid features, onboarding is mocked, and there's zero social proof. These are high-ROI fixes — most are small but the cumulative effect is significant.

## Architecture

All changes are in `web/` (Next.js 16 frontend). No API changes required — existing endpoints cover all data needs. The work divides into three phases by dependency and impact/effort ratio.

---

## Phase 1: Broken Fundamentals

Three independent fixes for issues that actively harm the product, plus a metadata cleanup. Each is small but the cumulative effect is significant.

> **Note**: The original audit identified missing favicon and OG image as issues, but these were already implemented via Next.js file-based metadata convention in `web/src/app/` (not `web/public/`): `favicon.ico`, `icon.svg`, `apple-icon.png`, `opengraph-image.tsx`, `twitter-image.tsx`. A minor cleanup of stale metadata references in `layout.tsx` remains (Task 3).

### Task 1: Enable Navbar CTA for Unauthenticated Visitors

**Priority**: P0 — Highest-impact single change
**Files**: `web/src/hooks/use-navigation.ts`

The `NavCTA` component (`web/src/components/nav/nav-cta.tsx`) is fully built and renders primary/secondary buttons. The navigation hook on line 65 hardcodes `const cta: NavigationCTA | null = null`, so the CTA never renders.

**Change**: Replace line 65 with conditional logic:
- When `!isAuthenticated`: return `{ primary: { label: "Get Started", href: "/login" }, secondary: { label: "Sign In", href: "/login" } }`
- When `isAuthenticated`: return `null` (no CTA needed — user is already signed in)

**Test**: Unit test for `useNavigation` hook returning CTA when session is null. Visual: visit landing page logged out → "Get Started" / "Sign In" buttons in navbar. Visit logged in → buttons disappear.

### Task 2: Add Smart Money, Backtesting & Account to Sidebar

**Priority**: P0 — Paying users can't find paid features
**Files**: `web/src/components/layout/sidebar.tsx`, `web/src/hooks/use-navigation.ts`

The sidebar only links to Dashboard, Methodology, Guides, and Status. Smart Money (`/smart-money`) and Backtesting (`/backtesting`) are only accessible by typing the URL. Users paying $19-49/mo can't discover the features they're paying for.

**Changes**:
1. Add to `navGroups` in `sidebar.tsx`:
   - CORE group: `{ href: "/smart-money", label: "Smart Money", icon: <IconDollar /> }` and `{ href: "/backtesting", label: "Backtesting", icon: <IconChart /> }`
   - New ACCOUNT group: `{ href: "/account", label: "Account", icon: <IconUser /> }`
2. Create 3 new inline SVG icon components matching existing style (24x24 viewBox, `stroke="currentColor"`, strokeWidth 1.5)
3. Add Smart Money and Backtesting to `APP_LINKS` in `use-navigation.ts` for the mobile hamburger menu

**Test**: Log in → verify all features visible in sidebar (expanded + collapsed tooltip mode). Verify active state highlighting on each page. Verify mobile hamburger menu includes new links.

### Task 3: Clean Up Stale OG/Twitter Metadata in layout.tsx

**Priority**: P1 — Metadata conflict between manual and file-based convention
**Files**: `web/src/app/layout.tsx`

Favicon and OG image assets already exist via Next.js file-based metadata convention in `web/src/app/`: `favicon.ico`, `icon.svg`, `apple-icon.png`, `opengraph-image.tsx` (dynamic, 145 lines, uses `ImageResponse`), and `twitter-image.tsx`. However, `layout.tsx` still declares manual `openGraph.images` and `twitter.images` arrays pointing to a non-existent `/og-image.png`. This creates a conflict — the manual metadata overrides the file-based convention with a broken URL.

**Change**: Remove the `images` array from `openGraph` metadata and `images` from `twitter` metadata in `layout.tsx`. Keep all other metadata fields (title, description, url, siteName, locale, type, card). Next.js will auto-discover the existing `opengraph-image.tsx` and `twitter-image.tsx` files.

**Test**: Use opengraph.xyz or Twitter Card Validator to verify the dynamic OG image renders on social share (should already work once the stale manual reference is removed).

### Task 4: Create Branded 404 Page

**Priority**: P1 — Trust & professionalism
**Files**: `web/src/app/not-found.tsx` (new)

Currently uses default Next.js 404 page.

**New file** — `web/src/app/not-found.tsx`:
- Dark background matching design system
- "Page not found" heading
- "This URL doesn't exist. Try searching for a ticker instead." body text
- Embedded `HeroSearch` component (already exists at `web/src/components/landing/hero-search.tsx`)
- Link back to home: "← Back to home"
- Matches existing design tokens

**Test**: Visit `/nonexistent-page` → verify branded 404 with search bar renders.

---

## Phase 2: Conversion Path Fixes

Four tasks that expand engagement paths and prevent drop-offs.

### Task 5: Add Route Protection via middleware.ts

**Priority**: P1 — Prevent broken states for unauthenticated users
**Files**: `web/src/middleware.ts` (new)

No route protection exists. Unauthenticated users hitting `/dashboard`, `/smart-money`, `/backtesting`, `/admin/*`, `/account` see loading skeletons or errors.

**Note**: Using standard `middleware.ts` convention. Place at `web/src/middleware.ts` (same level as `app/`).

**Implementation**:
- Check for NextAuth session token cookie (e.g., `next-auth.session-token` or `__Secure-next-auth.session-token`)
- Protected routes: `/dashboard`, `/smart-money`, `/backtesting`, `/admin/:path*`, `/account`
- Redirect to `/login?callbackUrl=[original_url]` for unauthenticated requests
- Public routes (pass through): `/`, `/login`, `/methodology`, `/guides`, `/legal`, `/terms`, `/privacy`, `/security`, `/contact`, `/asset/:ticker`, `/api/:path*`, `/explore`, `/about`, `/not-found`, `/_next/*`, static assets

**Matcher config**: Match all routes except static assets, then check against the protected routes list.

**Test**: Visit `/dashboard` logged out → redirected to `/login?callbackUrl=%2Fdashboard`. Log in → redirected back to `/dashboard`. Visit `/explore` logged out → page renders normally.

### Task 6: Install Global Toast System

**Priority**: P1 — Users get no feedback on actions
**Files**: `web/package.json`, `web/src/app/layout.tsx`, various interaction points

No global feedback system exists. Actions complete silently.

**Implementation**:
1. Install `sonner` (`cd web && npm install sonner`). Verify Tailwind v4 compatibility before finalizing — test that the `<Toaster />` renders correctly with the project's Tailwind configuration.
2. Add `<Toaster />` provider in `layout.tsx` with theme configuration:
   - `theme="dark"`
   - Custom styling to match design tokens: dark bg, emerald accent for success, bearish red for errors, border-subtle borders
   - Position: `bottom-right`
3. Wire toasts into key interaction points:
   - Login success / failure
   - Watchlist add / remove
   - Score refresh
   - Account settings save
   - Pro-gate upgrade nudge (when free-tier users hit paid features)

**Test**: Perform key actions → verify toast appears with correct styling and auto-dismisses.

### Task 7: Wire Onboarding to Real Scoring

**Priority**: P1 — First product interaction is fake
**Files**: `web/src/components/onboarding/onboarding-flow.tsx`, possibly `web/src/lib/api/scores.ts`

The onboarding promises "see composite scores in 60 seconds" then fakes a 2-second `setTimeout` and redirects to dashboard.

**Implementation**:
1. Replace `setTimeout` mock in `handleSubmit` with real API calls
2. Call `/api/v1/public/score/{ticker}` for each entered ticker via `Promise.all` (using `apiFetch` — same pattern as `HeroSearch`). Must use the **public** endpoint since onboarding runs before the user has an authenticated session.
3. Update step indicators as each phase completes:
   - "Data" → resolves immediately (request sent)
   - "Filter" → resolves when first response arrives
   - "Score" → resolves when all responses arrive
   - "Rank" → brief delay, then redirect
4. On success: redirect to `/asset/[firstTicker]` so user sees immediate, relevant content. The redirect replaces the unused `"results"` stage — remove it from the `Stage` type.
5. Fallback: if all calls fail or timeout after 10 seconds, redirect to `/dashboard` with a toast (Task 6) explaining the delay: "Scoring is taking longer than usual. Your results will appear on the dashboard shortly."

**Test**: Enter AAPL, MSFT in onboarding → verify real API calls made → verify step indicators progress → verify redirect to `/asset/AAPL`. Test timeout fallback by simulating slow API.

### Task 8: Hero Copy Iteration

**Priority**: P2 — Incremental conversion lift
**Files**: `web/src/components/landing/sections/hero-section.tsx`

**Changes**:
1. Change the subline text in the `<p data-hero-subtext>` element from:
   - `"Systematic equity analysis. Five factors. Zero emotion."`
   - To: `"3,000+ stocks filtered to the ones worth your capital. Every score auditable to the formula."`
2. Add secondary CTA inside the `data-hero-ctas` div in `hero-section.tsx`, after the `<HeroSearch />` component:
   - Text: "or browse this week's top picks →"
   - Link to `/explore` (Task 10)
   - Styled as subtle text link, `text-text-secondary hover:text-accent`, `text-sm`

Keep "Discipline. Engineered." headline unchanged — it's strong.

**Test**: Visual review. Verify responsive text scaling with `clamp()` still works. Verify explore link works.

---

## Phase 3: Conversion Expansion

Four tasks shipping as one bundled PR. New content that opens additional conversion paths and builds trust.

### Task 9: Comparison Table on Landing Page

**Priority**: P2 — Competitive differentiation is buried in FAQ
**Files**: `web/src/components/landing/sections/comparison-section.tsx` (new), `web/src/components/landing/homepage-client.tsx`

**Placement**: Insert between `EvidenceSection` and `PricingSection` in `homepage-client.tsx`.

**Design**: Three-column comparison table styled as `terminal-card`:

| Dimension | Margin Invest | Traditional Screeners | Black-Box Ratings |
|-----------|--------------|----------------------|-------------------|
| Scoring | Sector-neutral percentiles | Absolute filters | Opaque composite |
| Transparency | Every formula documented | Filter-based | Hidden methodology |
| Filters | 6 forensic (Beneish, Altman) | Price/volume only | None |
| Auditability | Spreadsheet-verifiable | Limited | None |
| Bias | Deterministic, zero discretion | User-configured | Analyst opinions |

**Responsive**: On mobile, stacks vertically — each column becomes its own card with the same rows.

**Accessibility**: Use semantic HTML table markup with `<caption>`, `<thead>`, and `<th scope="col">` / `<th scope="row">` for screen reader compatibility.

**Test**: Visual review. Verify responsive layout on mobile.

### Task 10: Public Explore / Top Picks Page

**Priority**: P2 — Secondary CTA, SEO, proves system works
**Files**: `web/src/app/explore/page.tsx` (new), `web/src/components/explore/` (new directory)

**Data source**: Existing `/api/v1/scores?page=1&page_size=20&min_percentile=70` endpoint. Supports pagination, `min_percentile`, and `conviction` filtering. No new API endpoint needed. Note: this endpoint does not require authentication, so server-rendered public access works.

**Implementation**:
1. Server component `page.tsx`: fetch initial data via `serverFetch()` from `@/lib/api/server` (NOT `apiFetch` — server component). Include `generateMetadata()` for SEO.
2. Client component `explore-client.tsx`: pagination and filtering use `apiFetch()` from `@/lib/api/client` for client-side interactions.
3. Display per asset: ticker, name, sector, composite score, tier badge, "View full report →" link to `/asset/[ticker]`
4. Page is public and indexable (no auth required)
5. Graceful fallback if API is unavailable

**Linked from**: hero section secondary CTA (Task 8), navbar public links (`PUBLIC_LINKS` in `use-navigation.ts`), footer.

**Test**: Visit `/explore` logged out → see top picks. Click "View full report" → navigates to asset page. Verify page is server-rendered (view source shows content).

### Task 11: About / Founder Page

**Priority**: P2 — Trust & credibility for financial product
**Files**: `web/src/app/about/page.tsx` (new)

**Sections**:
1. **Why This Exists** — Mission statement. Deterministic analysis, anti-narrative, anti-black-box.
2. **How It Works** — Brief (2-3 sentences), links to `/methodology` for details.
3. **Who Built It** — Founder background and technical credentials. Content provided during implementation.
4. **Contact** — Links to `/contact` page.

**Style**: Dark background, consistent with design system. Direct, technical tone matching existing brand. No stock photos, no corporate speak.

**Navigation**: Add "About" to footer links.

**Test**: Visual review. Verify footer link works.

### Task 12: Social Proof Section on Landing Page

**Priority**: P3 — Important but uses system-generated data
**Files**: `web/src/components/landing/sections/social-proof-section.tsx` (new), `web/src/components/landing/homepage-client.tsx`

**Placement**: Insert below `AuthorityStrip` in `homepage-client.tsx`.

**Distinct from AuthorityStrip**: The authority strip is a compact stat bar with numbers. This section tells a narrative story about what those numbers mean.

**Content** (system-generated from `HomepageData`):
- "X,XXX positions scored this cycle" — with icon, short explanation of what a cycle means
- "XX% of US equities fail at least one forensic filter" — computed from `total_universe` and `surviving_count`
- "Every score links to its formula" — differentiator, links to methodology
- "Daily updates since [launch date]" — consistency/reliability signal

Each stat gets an icon, the number, and a one-line explanation. Styled as a grid of cards, distinct from the compact AuthorityStrip above.

**Future iteration**: Early adopter quotes, press mentions, user count. Not in this spec.

**Test**: Visual review. Verify stats pull from live `HomepageData`.

---

## PR Strategy

| Phase | PRs | Rationale |
|-------|-----|-----------|
| Phase 1 | 3 individual PRs | Tasks 1, 2, 4 are tiny and independent. Task 3 (metadata cleanup) can bundle with Task 1 |
| Phase 2 | 4 individual PRs | Tasks 5-8 are independent, different concerns |
| Phase 3 | 1 bundled PR | Tasks 9-12 land together as a cohesive content launch |

Total: 8 PRs.

## Verification Plan

### Phase 1 (Quick wins)
- **Visual**: OG image via opengraph.xyz (after metadata cleanup), navbar CTA visible logged out, sidebar has all features, 404 page branded
- **Automated**: Unit test for `useNavigation` hook returning CTA for unauthenticated users

### Phase 2 (Conversion path)
- **Manual**: Walk through login redirect flow (middleware.ts), complete onboarding with real tickers, trigger toasts on key actions
- **Automated**: Unit tests for middleware route matching, onboarding API integration, toast rendering

### Phase 3 (Conversion expansion)
- **Manual**: Review comparison table, explore page, about page, social proof section visually
- **SEO**: Verify `/explore` is server-rendered and indexable (view page source)
- **Responsive**: Check all new sections on mobile viewport

## Deferred to Future Specs

- **Email System**: Score alerts, transactional email (welcome, password reset, weekly digest). Backend infrastructure: Resend integration, HTML templates, notification preferences UI. Separate spec, ~1-2 weeks.
- **Smart Money Backend**: API endpoints `new-positions` and `crowded_trades` return empty arrays because they need previous-quarter comparison logic. Frontend components (`MarketSignals`, `CloneLab`) are fully built. Separate spec, ~1-2 weeks.
