# Marketing & Conversion Implementation — Design Spec

**Date**: 2026-03-17
**Scope**: Phases 1-3 (Tasks 1-13) — frontend/conversion work
**Out of scope**: Email system (Task 14), Smart Money backend (Task 15) — separate future specs

## Problem

The product itself is strong (design system, forensic transparency, methodology depth) but the conversion infrastructure has critical gaps: navbar CTA is hardcoded to null, favicon/OG image missing, authenticated users can't navigate to paid features, onboarding is mocked, and there's zero social proof. These are high-ROI fixes — most are small but the cumulative effect is significant.

## Architecture

All changes are in `web/` (Next.js 16 frontend). No API changes required — existing endpoints cover all data needs. The work divides into three phases by dependency and impact/effort ratio.

---

## Phase 1: Broken Fundamentals

Five independent fixes for issues that actively harm the product. Each is small but the cumulative effect is significant.

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

### Task 3: Create Favicon & Apple Touch Icon

**Priority**: P0 — Every browser tab shows blank icon
**Files**: `web/public/` (new files), `web/src/app/layout.tsx`

The `/public` directory only contains `noise.svg`. No favicon assets exist.

**Design**: Generate from existing logo polyline SVG (`points="2,16 6,6 10,12 14,4 18,16"`). Emerald accent `#1A7A5A` on dark background `#0C1A13`.

**New files**:
- `web/public/favicon.ico` — 32x32 ICO
- `web/public/favicon.svg` — SVG favicon (modern browsers)
- `web/public/apple-touch-icon.png` — 180x180 PNG
- `web/public/favicon-16x16.png` — 16x16 PNG
- `web/public/favicon-32x32.png` — 32x32 PNG

**Change in `layout.tsx`**: Add `icons` field to `metadata` export:
```ts
icons: {
  icon: [
    { url: "/favicon.svg", type: "image/svg+xml" },
    { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
  ],
  apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  shortcut: "/favicon.ico",
}
```

**Test**: Load site → verify favicon in browser tab. Check iOS home screen bookmark renders touch icon.

### Task 4: Create Dynamic OG Image

**Priority**: P0 — Every social share shows broken image
**Files**: `web/src/app/opengraph-image.tsx` (new), `web/src/app/layout.tsx`

`layout.tsx` declares `images: [{ url: "/og-image.png", width: 1200, height: 630 }]` but the file doesn't exist. Every social share shows a broken image.

**Approach**: Dynamic OG image using Next.js built-in `ImageResponse` (Satori). This allows live stats in the image.

**New file** — `web/src/app/opengraph-image.tsx`:
- 1200x630 dimensions
- Dark background (`#0C1A13`)
- Logo polyline rendered as SVG path
- "Discipline. Engineered." headline in Inter Tight
- Live stat: "Scoring X,XXX+ US equities daily" (can be hardcoded initially, wired to API later)
- Emerald accent color

**Change in `layout.tsx`**: Remove the manual `openGraph.images` array from the `metadata` export — Next.js auto-discovers `opengraph-image.tsx` via the file-based convention. Keep the rest of the `openGraph` metadata (title, description, url, siteName, locale, type). Same for `twitter.images`.

**Test**: Use opengraph.xyz or Twitter Card Validator to verify image renders on share.

### Task 5: Create Branded 404 Page

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

### Task 6: Add Route Protection via proxy.ts

**Priority**: P1 — Prevent broken states for unauthenticated users
**Files**: `web/src/proxy.ts` (new)

No route protection exists. Unauthenticated users hitting `/dashboard`, `/smart-money`, `/backtesting`, `/admin/*`, `/account` see loading skeletons or errors.

**Note**: Next.js 16 renames `middleware.ts` to `proxy.ts`. Same concept, Node.js runtime. Place at `web/src/proxy.ts` (same level as `app/`).

**Implementation**:
- Check for NextAuth session token cookie (e.g., `next-auth.session-token` or `__Secure-next-auth.session-token`)
- Protected routes: `/dashboard`, `/smart-money`, `/backtesting`, `/admin/:path*`, `/account`
- Redirect to `/login?callbackUrl=[original_url]` for unauthenticated requests
- Public routes (pass through): `/`, `/login`, `/methodology`, `/guides`, `/legal`, `/terms`, `/privacy`, `/security`, `/contact`, `/asset/:ticker`, `/api/:path*`, `/explore`, `/about`, `/not-found`, `/_next/*`, static assets

**Matcher config**: Match all routes except static assets, then check against the protected routes list.

**Test**: Visit `/dashboard` logged out → redirected to `/login?callbackUrl=%2Fdashboard`. Log in → redirected back to `/dashboard`. Visit `/explore` logged out → page renders normally.

### Task 7: Install Global Toast System

**Priority**: P1 — Users get no feedback on actions
**Files**: `web/package.json`, `web/src/app/layout.tsx`, various interaction points

No global feedback system exists. Actions complete silently.

**Implementation**:
1. Install `sonner` (`cd web && npm install sonner`)
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

### Task 8: Wire Onboarding to Real Scoring

**Priority**: P1 — First product interaction is fake
**Files**: `web/src/components/onboarding/onboarding-flow.tsx`, possibly `web/src/lib/api/scores.ts`

The onboarding promises "see composite scores in 60 seconds" then fakes a 2-second `setTimeout` and redirects to dashboard.

**Implementation**:
1. Replace `setTimeout` mock in `handleSubmit` with real API calls
2. Call `/api/v1/scores/{ticker}` for each entered ticker via `Promise.all` (using existing `getScore()` from `@/lib/api/scores`)
3. Update step indicators as each phase completes:
   - "Data" → resolves immediately (request sent)
   - "Filter" → resolves when first response arrives
   - "Score" → resolves when all responses arrive
   - "Rank" → brief delay, then redirect
4. On success: redirect to `/asset/[firstTicker]` so user sees immediate, relevant content
5. Fallback: if all calls fail or timeout after 10 seconds, redirect to `/dashboard` with a toast (Task 7) explaining the delay: "Scoring is taking longer than usual. Your results will appear on the dashboard shortly."

**Test**: Enter AAPL, MSFT in onboarding → verify real API calls made → verify step indicators progress → verify redirect to `/asset/AAPL`. Test timeout fallback by simulating slow API.

### Task 9: Hero Copy Iteration

**Priority**: P2 — Incremental conversion lift
**Files**: `web/src/components/landing/sections/hero-section.tsx`

**Changes**:
1. Change subline (line 119) from:
   - `"Systematic equity analysis. Five factors. Zero emotion."`
   - To: `"3,000+ stocks filtered to the ones worth your capital. Every score auditable to the formula."`
2. Add secondary CTA below the `HeroSearch` component (inside `data-hero-ctas` div):
   - Text: "or browse this week's top picks →"
   - Link to `/explore` (Task 11)
   - Styled as subtle text link, `text-text-secondary hover:text-accent`, `text-sm`

Keep "Discipline. Engineered." headline unchanged — it's strong.

**Test**: Visual review. Verify responsive text scaling with `clamp()` still works. Verify explore link works.

---

## Phase 3: Conversion Expansion

Four tasks shipping as one bundled PR. New content that opens additional conversion paths and builds trust.

### Task 10: Comparison Table on Landing Page

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

**Test**: Visual review. Verify responsive layout on mobile.

### Task 11: Public Explore / Top Picks Page

**Priority**: P2 — Secondary CTA, SEO, proves system works
**Files**: `web/src/app/(landing)/explore/page.tsx` (new), `web/src/components/explore/` (new directory)

**Data source**: Existing `/api/v1/scores?page=1&page_size=20&min_percentile=70` endpoint. Supports pagination, `min_percentile`, and `conviction` filtering. No new API endpoint needed.

**Implementation**:
1. Server component `page.tsx`: fetch initial data via `serverFetch()`, pass to client component. Include `generateMetadata()` for SEO.
2. Client component `explore-client.tsx`: pagination, optional filtering by conviction level and sector.
3. Display per asset: ticker, name, sector, composite score, tier badge, "View full report →" link to `/asset/[ticker]`
4. Page is public and indexable (no auth required)
5. Graceful fallback if API is unavailable

**Linked from**: hero section secondary CTA (Task 9), navbar public links (`PUBLIC_LINKS` in `use-navigation.ts`), footer.

**Test**: Visit `/explore` logged out → see top picks. Click "View full report" → navigates to asset page. Verify page is server-rendered (view source shows content).

### Task 12: About / Founder Page

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

### Task 13: Social Proof Section on Landing Page

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
| Phase 1 | 5 individual PRs | Each is tiny (15-45 min), independent, shippable immediately |
| Phase 2 | 4 individual PRs | Tasks 6-9 are independent, different concerns |
| Phase 3 | 1 bundled PR | Tasks 10-13 land together as a cohesive content launch |

Total: 10 PRs.

## Verification Plan

### Phase 1 (Quick wins)
- **Visual**: Favicon in browser tab, OG image via opengraph.xyz, navbar CTA visible logged out, sidebar has all features, 404 page branded
- **Automated**: Unit test for `useNavigation` hook returning CTA for unauthenticated users

### Phase 2 (Conversion path)
- **Manual**: Walk through login redirect flow (proxy.ts), complete onboarding with real tickers, trigger toasts on key actions
- **Automated**: Unit tests for proxy route matching, onboarding API integration, toast rendering

### Phase 3 (Conversion expansion)
- **Manual**: Review comparison table, explore page, about page, social proof section visually
- **SEO**: Verify `/explore` is server-rendered and indexable (view page source)
- **Responsive**: Check all new sections on mobile viewport

## Deferred to Future Specs

- **Task 14 — Email System**: Score alerts, transactional email (welcome, password reset, weekly digest). Backend infrastructure: Resend integration, HTML templates, notification preferences UI. Separate spec, ~1-2 weeks.
- **Task 15 — Smart Money Backend**: API endpoints `new-positions` and `crowded_trades` return empty arrays because they need previous-quarter comparison logic. Frontend components (`MarketSignals`, `CloneLab`) are fully built. Separate spec, ~1-2 weeks.
