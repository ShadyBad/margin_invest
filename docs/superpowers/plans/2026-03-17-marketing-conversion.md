# Marketing & Conversion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 12 frontend conversion gaps — from broken navbar CTA to missing social proof — to stop losing real conversions on an otherwise strong product.

**Architecture:** All changes are in `web/` (Next.js 16, React 19, Tailwind v4). No API changes. Existing endpoints (`/api/v1/scores`, `/api/v1/public/score/{ticker}`, `/api/v1/dashboard`) provide all needed data. Three phases: broken fundamentals, conversion path fixes, conversion expansion.

**Tech Stack:** Next.js 16.1.6, React 19, Tailwind v4, Vitest + @testing-library/react, sonner (new), NextAuth

**Spec:** `docs/superpowers/specs/2026-03-17-marketing-conversion-design.md`

---

## File Map

### Files to Modify
| File | Responsibility | Tasks |
|------|---------------|-------|
| `web/src/hooks/use-navigation.ts` | Navigation state for navbar + mobile menu | 1, 2 |
| `web/src/hooks/__tests__/use-navigation.test.ts` | Navigation hook tests | 1, 2 |
| `web/src/components/layout/sidebar.tsx` | Sidebar nav groups + icons | 2 |
| `web/src/components/layout/__tests__/sidebar.test.tsx` | Sidebar tests | 2 |
| `web/src/app/layout.tsx` | Root layout, metadata, providers | 3, 6 |
| `web/src/components/onboarding/onboarding-flow.tsx` | Onboarding scoring flow | 7 |
| `web/src/components/landing/sections/hero-section.tsx` | Hero headline + search | 8 |
| `web/src/components/landing/homepage-client.tsx` | Landing page section composition | 9, 12 |
| `web/src/components/landing/sections/footer-section.tsx` | Footer links | 10, 11 |

### Files to Create
| File | Responsibility | Task |
|------|---------------|------|
| `web/src/app/not-found.tsx` | Branded 404 page | 4 |
| `web/src/app/not-found.test.tsx` | 404 page test | 4 |
| `web/src/middleware.ts` | Route protection for auth | 5 |
| `web/src/__tests__/middleware.test.ts` | Middleware tests | 5 |
| `web/src/components/landing/sections/comparison-section.tsx` | Comparison table | 9 |
| `web/src/components/landing/sections/__tests__/comparison-section.test.tsx` | Comparison table test | 9 |
| `web/src/app/explore/page.tsx` | Explore page server component | 10 |
| `web/src/components/explore/explore-client.tsx` | Explore page client component | 10 |
| `web/src/components/explore/__tests__/explore-client.test.tsx` | Explore page test | 10 |
| `web/src/app/about/page.tsx` | About / founder page | 11 |
| `web/src/components/landing/sections/social-proof-section.tsx` | Social proof section | 12 |
| `web/src/components/landing/sections/__tests__/social-proof-section.test.tsx` | Social proof test | 12 |

---

## Phase 1: Broken Fundamentals

### Task 1: Enable Navbar CTA for Unauthenticated Visitors

**Files:**
- Modify: `web/src/hooks/use-navigation.ts`
- Modify: `web/src/hooks/__tests__/use-navigation.test.ts`

- [ ] **Step 1: Update the existing test expectation to require CTA for unauthenticated users**

In `web/src/hooks/__tests__/use-navigation.test.ts`, change the test at line 42-45 from asserting `cta` is null to asserting it returns the CTA object:

```typescript
it("returns CTA with Get Started and Sign In for unauthenticated users", () => {
  const { result } = renderHook(() => useNavigation())
  expect(result.current.cta).toEqual({
    primary: { label: "Get Started", href: "/login" },
    secondary: { label: "Sign In", href: "/login" },
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: FAIL — `cta` is still `null`

- [ ] **Step 3: Implement the CTA logic in use-navigation.ts**

In `web/src/hooks/use-navigation.ts`, replace line 65:

```typescript
// Before:
const cta: NavigationCTA | null = null

// After:
const cta: NavigationCTA | null = isAuthenticated
  ? null
  : {
      primary: { label: "Get Started", href: "/login" },
      secondary: { label: "Sign In", href: "/login" },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: All tests PASS. The authenticated test on line 73-75 still expects `cta` to be `null` — that remains correct.

- [ ] **Step 5: Commit**

```bash
git add web/src/hooks/use-navigation.ts web/src/hooks/__tests__/use-navigation.test.ts
git commit -m "feat(web): enable navbar CTA for unauthenticated visitors"
```

---

### Task 2: Add Smart Money, Backtesting & Account to Sidebar

**Files:**
- Modify: `web/src/components/layout/sidebar.tsx`
- Modify: `web/src/components/layout/__tests__/sidebar.test.tsx`
- Modify: `web/src/hooks/use-navigation.ts`
- Modify: `web/src/hooks/__tests__/use-navigation.test.ts`

- [ ] **Step 1: Write failing tests for new sidebar links**

In `web/src/components/layout/__tests__/sidebar.test.tsx`, add these tests after the existing ones:

```typescript
it("renders Smart Money link", () => {
  render(<Sidebar expanded={true} onToggle={vi.fn()} />)
  expect(screen.getByRole("link", { name: "Smart Money" })).toHaveAttribute("href", "/smart-money")
})

it("renders Backtesting link", () => {
  render(<Sidebar expanded={true} onToggle={vi.fn()} />)
  expect(screen.getByRole("link", { name: "Backtesting" })).toHaveAttribute("href", "/backtesting")
})

it("renders Account link", () => {
  render(<Sidebar expanded={true} onToggle={vi.fn()} />)
  expect(screen.getByRole("link", { name: "Account" })).toHaveAttribute("href", "/account")
})

it("renders ACCOUNT group title when expanded", () => {
  render(<Sidebar expanded={true} onToggle={vi.fn()} />)
  expect(screen.getByText("ACCOUNT")).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/layout/__tests__/sidebar.test.tsx`
Expected: 4 new tests FAIL

- [ ] **Step 3: Add icon components and nav groups to sidebar.tsx**

In `web/src/components/layout/sidebar.tsx`, add three new icon components after `IconPulse` (matching existing style: 24x24 viewBox, stroke, 1.5 width):

```typescript
function IconDollar() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 2v20m5-17a5 3 0 01-5 3 5 3 0 01-5-3 5 3 0 015-3 5 3 0 015 3zm0 12a5 3 0 01-5 3 5 3 0 01-5-3 5 3 0 015-3 5 3 0 015 3z" />
    </svg>
  )
}

function IconChart() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18h18M7 16l4-4 4 4 5-5" />
    </svg>
  )
}

function IconUser() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.5 20.25a8.25 8.25 0 0115 0" />
    </svg>
  )
}
```

Update the `navGroups` array:

```typescript
const navGroups: NavGroup[] = [
  {
    title: "CORE",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: <IconGrid /> },
      { href: "/smart-money", label: "Smart Money", icon: <IconDollar /> },
      { href: "/backtesting", label: "Backtesting", icon: <IconChart /> },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { href: "/methodology", label: "Methodology", icon: <IconBook /> },
      { href: "/guides", label: "Guides", icon: <IconCompass /> },
      { href: "/status", label: "Status", icon: <IconPulse /> },
    ],
  },
  {
    title: "ACCOUNT",
    items: [
      { href: "/account", label: "Account", icon: <IconUser /> },
    ],
  },
]
```

- [ ] **Step 4: Run sidebar tests to verify they pass**

Run: `cd web && npx vitest run src/components/layout/__tests__/sidebar.test.tsx`
Expected: All tests PASS

- [ ] **Step 5: Update APP_LINKS in use-navigation.ts for mobile menu**

In `web/src/hooks/use-navigation.ts`, update `APP_LINKS` (lines 49-52):

```typescript
const APP_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/smart-money", label: "Smart Money" },
  { href: "/backtesting", label: "Backtesting" },
  { href: "/guides", label: "Guides" },
]
```

- [ ] **Step 6: Update the navigation test to expect new links**

In `web/src/hooks/__tests__/use-navigation.test.ts`, update the test at line 67-71:

```typescript
it("returns Dashboard, Smart Money, Backtesting, and Guides as center links", () => {
  const { result } = renderHook(() => useNavigation())
  const labels = result.current.links.map((l) => l.label)
  expect(labels).toEqual(["Dashboard", "Smart Money", "Backtesting", "Guides"])
})
```

- [ ] **Step 7: Run all navigation and sidebar tests**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts src/components/layout/__tests__/sidebar.test.tsx`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add web/src/components/layout/sidebar.tsx web/src/components/layout/__tests__/sidebar.test.tsx web/src/hooks/use-navigation.ts web/src/hooks/__tests__/use-navigation.test.ts
git commit -m "feat(web): add Smart Money, Backtesting, Account to sidebar and mobile nav"
```

---

### Task 3: Clean Up Stale OG/Twitter Metadata in layout.tsx

**Files:**
- Modify: `web/src/app/layout.tsx`

- [ ] **Step 1: Remove stale images arrays from metadata**

In `web/src/app/layout.tsx`, modify the `metadata` export. Remove the `images` array from `openGraph` and `images` from `twitter`. Keep everything else:

```typescript
export const metadata: Metadata = {
  title: "Margin Invest",
  description:
    "Deterministic investment analysis — quantitative scoring without human bias",
  metadataBase: new URL("https://www.margin-invest.com"),
  openGraph: {
    title: "Margin Invest — Discipline. Engineered.",
    description:
      "A deterministic capital allocation system that replaces narrative with structure. Scoring 3,000+ US equities daily.",
    url: "https://www.margin-invest.com",
    siteName: "Margin Invest",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Margin Invest — Discipline. Engineered.",
    description:
      "A deterministic capital allocation system. Scoring 3,000+ US equities daily with zero human discretion.",
  },
}
```

- [ ] **Step 2: Verify existing OG image files are present**

Run: `ls web/src/app/opengraph-image.tsx web/src/app/twitter-image.tsx web/src/app/favicon.ico web/src/app/icon.svg web/src/app/apple-icon.png`
Expected: All 5 files exist

- [ ] **Step 3: Commit**

```bash
git add web/src/app/layout.tsx
git commit -m "fix(web): remove stale OG/twitter image metadata conflicting with file-based convention"
```

---

### Task 4: Create Branded 404 Page

**Files:**
- Create: `web/src/app/not-found.tsx`
- Create: `web/src/app/__tests__/not-found.test.tsx`

- [ ] **Step 1: Write the test**

Create `web/src/app/__tests__/not-found.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import NotFound from "../not-found"

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

vi.mock("@/components/landing/hero-search", () => ({
  HeroSearch: () => <div data-testid="hero-search">HeroSearch</div>,
}))

describe("NotFound", () => {
  it("renders page not found heading", () => {
    render(<NotFound />)
    expect(screen.getByText("Page not found")).toBeInTheDocument()
  })

  it("renders helpful body text", () => {
    render(<NotFound />)
    expect(screen.getByText(/Try searching for a ticker/)).toBeInTheDocument()
  })

  it("renders HeroSearch component", () => {
    render(<NotFound />)
    expect(screen.getByTestId("hero-search")).toBeInTheDocument()
  })

  it("renders link back to home", () => {
    render(<NotFound />)
    const link = screen.getByRole("link", { name: /back to home/i })
    expect(link).toHaveAttribute("href", "/")
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/app/__tests__/not-found.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement not-found.tsx**

Create `web/src/app/not-found.tsx`:

```typescript
import Link from "next/link"
import { HeroSearch } from "@/components/landing/hero-search"

export default function NotFound() {
  return (
    <div className="min-h-screen bg-bg-primary flex flex-col items-center justify-center px-6">
      <div className="max-w-md w-full text-center space-y-8">
        <div className="space-y-3">
          <p className="text-mono-label text-text-tertiary tracking-widest uppercase">
            404
          </p>
          <h1 className="text-[32px] font-bold text-text-primary tracking-tight">
            Page not found
          </h1>
          <p className="text-body text-text-secondary">
            This URL doesn&apos;t exist. Try searching for a ticker instead.
          </p>
        </div>

        <div className="max-w-sm mx-auto">
          <HeroSearch />
        </div>

        <Link
          href="/"
          className="inline-block text-sm text-text-secondary hover:text-accent transition-colors"
        >
          &larr; Back to home
        </Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/app/__tests__/not-found.test.tsx`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/app/not-found.tsx web/src/app/__tests__/not-found.test.tsx
git commit -m "feat(web): add branded 404 page with ticker search"
```

---

## Phase 2: Conversion Path Fixes

### Task 5: Add Route Protection via middleware.ts

**Files:**
- Create: `web/src/middleware.ts`
- Create: `web/src/__tests__/middleware.test.ts`

- [ ] **Step 1: Write the test**

Create `web/src/__tests__/middleware.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { NextRequest, NextResponse } from "next/server"

// Mock next-auth — middleware uses getToken
vi.mock("next-auth/jwt", () => ({
  getToken: vi.fn(),
}))

import { getToken } from "next-auth/jwt"
import { middleware, config } from "../middleware"

const mockedGetToken = vi.mocked(getToken)

function createRequest(path: string): NextRequest {
  return new NextRequest(new URL(`http://localhost:3000${path}`))
}

describe("middleware", () => {
  beforeEach(() => {
    mockedGetToken.mockReset()
  })

  it("redirects unauthenticated users from /dashboard to /login", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/dashboard")
    const res = await middleware(req)
    expect(res?.status).toBe(307)
    expect(res?.headers.get("location")).toContain("/login")
    expect(res?.headers.get("location")).toContain("callbackUrl=%2Fdashboard")
  })

  it("redirects unauthenticated users from /smart-money to /login", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/smart-money")
    const res = await middleware(req)
    expect(res?.status).toBe(307)
    expect(res?.headers.get("location")).toContain("/login")
  })

  it("redirects unauthenticated users from /admin/approvals to /login", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/admin/approvals")
    const res = await middleware(req)
    expect(res?.status).toBe(307)
    expect(res?.headers.get("location")).toContain("/login")
  })

  it("allows authenticated users to access /dashboard", async () => {
    mockedGetToken.mockResolvedValue({ sub: "user-1" } as never)
    const req = createRequest("/dashboard")
    const res = await middleware(req)
    expect(res).toEqual(NextResponse.next())
  })

  it("allows unauthenticated users to access /explore", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/explore")
    const res = await middleware(req)
    expect(res).toEqual(NextResponse.next())
  })

  it("allows unauthenticated users to access /methodology", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/methodology")
    const res = await middleware(req)
    expect(res).toEqual(NextResponse.next())
  })

  it("exports a matcher config excluding static assets and API routes", () => {
    expect(config.matcher).toBeDefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/__tests__/middleware.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Implement middleware.ts**

Create `web/src/middleware.ts`:

```typescript
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"
import { getToken } from "next-auth/jwt"

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/smart-money",
  "/backtesting",
  "/admin",
  "/account",
]

function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix + "/")
  )
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  if (!isProtectedRoute(pathname)) {
    return NextResponse.next()
  }

  const token = await getToken({ req })

  if (!token) {
    const loginUrl = new URL("/login", req.url)
    loginUrl.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico, icon.svg, apple-icon.png (metadata files)
     * - api routes (handled by NextAuth / FastAPI proxy)
     * - public assets
     */
    "/((?!_next/static|_next/image|favicon\\.ico|icon\\.svg|apple-icon\\.png|api/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/__tests__/middleware.test.ts`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/middleware.ts web/src/__tests__/middleware.test.ts
git commit -m "feat(web): add route protection middleware for authenticated pages"
```

---

### Task 6: Install Global Toast System

**Files:**
- Modify: `web/package.json` (install sonner)
- Modify: `web/src/app/layout.tsx`

- [ ] **Step 1: Install sonner**

Run: `cd web && npm install sonner`

- [ ] **Step 2: Add Toaster provider to layout.tsx**

In `web/src/app/layout.tsx`, add the import at the top:

```typescript
import { Toaster } from "sonner"
```

Add `<Toaster />` inside the `<div className="min-h-screen bg-bg-primary">` block, after `<AnalysisDisclaimerModal />`:

```typescript
<Toaster
  theme="dark"
  position="bottom-right"
  toastOptions={{
    style: {
      background: "var(--color-bg-elevated)",
      border: "1px solid var(--color-border-subtle)",
      color: "var(--color-text-primary)",
    },
  }}
/>
```

- [ ] **Step 3: Verify toast renders by running existing tests**

Run: `cd web && npx vitest run src/app/__tests__/ --reporter=verbose 2>&1 | head -30`
Expected: Existing layout-related tests still pass. No breakage from adding `<Toaster />`.

- [ ] **Step 4: Commit**

```bash
git add web/src/app/layout.tsx web/package.json web/package-lock.json
git commit -m "feat(web): install sonner toast system with dark theme"
```

**Note**: Wiring toasts into specific interaction points (login, watchlist, score refresh, account save, pro-gate) happens incrementally as those components are touched. The foundation is in place.

---

### Task 7: Wire Onboarding to Real Scoring

**Files:**
- Modify: `web/src/components/onboarding/onboarding-flow.tsx`

- [ ] **Step 1: Write the test**

Check if a test file exists for onboarding, then create/update it.

Run: `ls web/src/components/onboarding/__tests__/ 2>/dev/null || echo "no test dir"`

Create `web/src/components/onboarding/__tests__/onboarding-flow.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { OnboardingFlow } from "../onboarding-flow"

const mockPush = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}))

let mockApiFetchResponse: unknown = null
let mockApiFetchShouldFail = false
vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(async () => {
    if (mockApiFetchShouldFail) throw new Error("API error")
    return mockApiFetchResponse
  }),
}))

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}))

describe("OnboardingFlow", () => {
  beforeEach(() => {
    mockPush.mockClear()
    mockApiFetchShouldFail = false
    mockApiFetchResponse = {
      ticker: "AAPL",
      company_name: "Apple Inc.",
      composite_score: 72,
      composite_tier: "high",
      signal: "strong",
      factor_summary: { quality_percentile: 80, value_percentile: 65, momentum_percentile: 70 },
      eliminated: false,
      elimination_reason: null,
      scored_at: "2026-03-17T00:00:00Z",
    }
  })

  it("renders input stage initially", () => {
    render(<OnboardingFlow />)
    expect(screen.getByText("Score your portfolio.")).toBeInTheDocument()
  })

  it("redirects to /asset/AAPL on successful scoring", async () => {
    render(<OnboardingFlow />)
    const input = screen.getByPlaceholderText(/AAPL/i)
    await userEvent.type(input, "AAPL{enter}")

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/asset/AAPL")
    }, { timeout: 5000 })
  })

  it("redirects to /dashboard on API failure", async () => {
    mockApiFetchShouldFail = true
    render(<OnboardingFlow />)
    const input = screen.getByPlaceholderText(/AAPL/i)
    await userEvent.type(input, "AAPL{enter}")

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard")
    }, { timeout: 15000 })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/onboarding/__tests__/onboarding-flow.test.tsx`
Expected: FAIL — redirect still goes to `/dashboard` unconditionally (mock setTimeout behavior)

- [ ] **Step 3: Implement real scoring in onboarding-flow.tsx**

Rewrite `web/src/components/onboarding/onboarding-flow.tsx`:

```typescript
"use client"

import { useState, useRef } from "react"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api/client"
import { toast } from "sonner"
import { TickerInput } from "./ticker-input"

type Stage = "input" | "scoring"

interface PublicScoreResult {
  ticker: string
  company_name: string
  composite_score: number
  composite_tier: string
  signal: string
  factor_summary: {
    quality_percentile: number
    value_percentile: number
    momentum_percentile: number
  }
  eliminated: boolean
  elimination_reason: string | null
  scored_at: string
}

const STEPS = ["Data", "Filter", "Score", "Rank"] as const

export function OnboardingFlow() {
  const [stage, setStage] = useState<Stage>("input")
  const [tickers, setTickers] = useState<string[]>([])
  const [completedSteps, setCompletedSteps] = useState(0)
  const router = useRouter()
  const abortRef = useRef<AbortController | null>(null)

  const handleSubmit = async (inputTickers: string[]) => {
    setTickers(inputTickers)
    setStage("scoring")
    setCompletedSteps(0)

    abortRef.current = new AbortController()
    const timeout = setTimeout(() => abortRef.current?.abort(), 10000)

    try {
      // Step 1: Data (request sent)
      setCompletedSteps(1)

      const results = await Promise.all(
        inputTickers.map((ticker) =>
          apiFetch<PublicScoreResult>(
            `/api/v1/public/score/${ticker.toUpperCase()}`,
            { signal: abortRef.current!.signal }
          )
        )
      )

      // Step 2: Filter (first response)
      setCompletedSteps(2)

      // Step 3: Score (all responses)
      setCompletedSteps(3)

      // Step 4: Rank (brief pause, then redirect)
      await new Promise((r) => setTimeout(r, 400))
      setCompletedSteps(4)

      clearTimeout(timeout)

      // Redirect to the first scored ticker
      const firstTicker = results[0]?.ticker || inputTickers[0].toUpperCase()
      await new Promise((r) => setTimeout(r, 300))
      router.push(`/asset/${firstTicker}`)
    } catch {
      clearTimeout(timeout)
      toast.error("Scoring is taking longer than usual. Your results will appear on the dashboard shortly.")
      router.push("/dashboard")
    }
  }

  return (
    <div className="w-full max-w-[560px]">
      <div className="bg-bg-elevated/60 backdrop-blur-[16px] border border-border-subtle rounded-[8px] p-8 md:p-10">
        {stage === "input" && (
          <div className="flex flex-col items-center text-center">
            <h1 className="text-[28px] md:text-[32px] font-bold text-text-primary leading-tight tracking-[-0.3px] mb-2">
              Score your portfolio.
            </h1>
            <p className="text-[15px] text-text-secondary mb-8">
              Enter your tickers and see composite scores in 60 seconds.
            </p>
            <TickerInput onSubmit={handleSubmit} />
          </div>
        )}

        {stage === "scoring" && (
          <div className="flex flex-col items-center text-center py-8">
            <div className="flex items-center gap-3 mb-6">
              {STEPS.map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <div
                    className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs font-mono transition-colors ${
                      i < completedSteps
                        ? "border-accent bg-accent/10 text-accent"
                        : i === completedSteps
                          ? "border-accent/40 text-accent animate-pulse"
                          : "border-border-subtle text-text-tertiary"
                    }`}
                  >
                    {i < completedSteps ? "✓" : i + 1}
                  </div>
                  <span className="text-[12px] text-text-secondary">{step}</span>
                  {i < STEPS.length - 1 && (
                    <span className="text-text-tertiary mx-1">&rarr;</span>
                  )}
                </div>
              ))}
            </div>
            <p className="text-[15px] text-text-secondary">
              Scoring {tickers.join(", ")}...
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/onboarding/__tests__/onboarding-flow.test.tsx`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/components/onboarding/onboarding-flow.tsx web/src/components/onboarding/__tests__/onboarding-flow.test.tsx
git commit -m "feat(web): wire onboarding to real public scoring API with progress indicators"
```

---

### Task 8: Hero Copy Iteration

**Files:**
- Modify: `web/src/components/landing/sections/hero-section.tsx`

- [ ] **Step 1: Update the subline text**

In `web/src/components/landing/sections/hero-section.tsx`, find the `<p data-hero-subtext>` element and change its text:

```typescript
// Before:
Systematic equity analysis. Five factors. Zero emotion.

// After:
3,000+ stocks filtered to the ones worth your capital. Every score auditable to the formula.
```

- [ ] **Step 2: Add secondary CTA below HeroSearch**

In the `data-hero-ctas` div in `hero-section.tsx`, add after `<HeroSearch />`:

```typescript
<div data-hero-ctas className="max-w-md">
  <HeroSearch />
  <p className="mt-4 text-sm text-text-secondary">
    or{" "}
    <a
      href="/explore"
      className="text-text-secondary hover:text-accent transition-colors underline underline-offset-2"
    >
      browse this week&apos;s top picks &rarr;
    </a>
  </p>
</div>
```

Add `import Link from "next/link"` at the top if not already present, and use `<Link>` instead of `<a>` for client-side navigation:

```typescript
import Link from "next/link"
// ...
<Link
  href="/explore"
  className="text-text-secondary hover:text-accent transition-colors underline underline-offset-2"
>
  browse this week&apos;s top picks &rarr;
</Link>
```

- [ ] **Step 3: Run existing hero section tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | grep -i hero | head -10`
Expected: Existing tests pass (or identify any that need updating for the new text)

- [ ] **Step 4: Commit**

```bash
git add web/src/components/landing/sections/hero-section.tsx
git commit -m "feat(web): update hero copy and add secondary explore CTA"
```

---

## Phase 3: Conversion Expansion (Bundled PR)

### Task 9: Comparison Table on Landing Page

**Files:**
- Create: `web/src/components/landing/sections/comparison-section.tsx`
- Create: `web/src/components/landing/sections/__tests__/comparison-section.test.tsx`
- Modify: `web/src/components/landing/homepage-client.tsx`

- [ ] **Step 1: Write the test**

Create `web/src/components/landing/sections/__tests__/comparison-section.test.tsx`:

```typescript
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ComparisonSection } from "../comparison-section"

describe("ComparisonSection", () => {
  it("renders the section heading", () => {
    render(<ComparisonSection />)
    expect(screen.getByText(/how we compare/i)).toBeInTheDocument()
  })

  it("renders all three competitor columns", () => {
    render(<ComparisonSection />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
    expect(screen.getByText("Traditional Screeners")).toBeInTheDocument()
    expect(screen.getByText("Black-Box Ratings")).toBeInTheDocument()
  })

  it("renders comparison rows", () => {
    render(<ComparisonSection />)
    expect(screen.getByText("Scoring")).toBeInTheDocument()
    expect(screen.getByText("Transparency")).toBeInTheDocument()
    expect(screen.getByText("Auditability")).toBeInTheDocument()
  })

  it("uses semantic table markup with caption", () => {
    render(<ComparisonSection />)
    const table = screen.getByRole("table")
    expect(table).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/sections/__tests__/comparison-section.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement comparison-section.tsx**

Create `web/src/components/landing/sections/comparison-section.tsx`:

```typescript
const ROWS = [
  { label: "Scoring", us: "Sector-neutral percentiles", screeners: "Absolute filters", blackbox: "Opaque composite" },
  { label: "Transparency", us: "Every formula documented", screeners: "Filter-based", blackbox: "Hidden methodology" },
  { label: "Filters", us: "6 forensic (Beneish, Altman)", screeners: "Price/volume only", blackbox: "None" },
  { label: "Auditability", us: "Spreadsheet-verifiable", screeners: "Limited", blackbox: "None" },
  { label: "Bias", us: "Deterministic, zero discretion", screeners: "User-configured", blackbox: "Analyst opinions" },
]

export function ComparisonSection() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-[28px] md:text-[36px] font-bold text-text-primary tracking-tight text-center mb-12">
          How We Compare
        </h2>

        {/* Desktop: table */}
        <div className="hidden md:block terminal-card overflow-hidden">
          <table className="w-full text-left">
            <caption className="sr-only">
              Comparison of Margin Invest vs Traditional Screeners vs Black-Box Ratings
            </caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-6 py-3 text-xs uppercase tracking-wider text-text-tertiary font-medium w-1/6" />
                <th scope="col" className="px-6 py-3 text-xs uppercase tracking-wider text-accent font-medium w-[28%]">
                  Margin Invest
                </th>
                <th scope="col" className="px-6 py-3 text-xs uppercase tracking-wider text-text-tertiary font-medium w-[28%]">
                  Traditional Screeners
                </th>
                <th scope="col" className="px-6 py-3 text-xs uppercase tracking-wider text-text-tertiary font-medium w-[28%]">
                  Black-Box Ratings
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.label} className="border-b border-border-subtle last:border-b-0">
                  <th scope="row" className="px-6 py-4 text-sm font-medium text-text-primary">
                    {row.label}
                  </th>
                  <td className="px-6 py-4 text-sm text-text-primary">{row.us}</td>
                  <td className="px-6 py-4 text-sm text-text-tertiary">{row.screeners}</td>
                  <td className="px-6 py-4 text-sm text-text-tertiary">{row.blackbox}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile: stacked cards */}
        <div className="md:hidden space-y-4">
          {[
            { title: "Margin Invest", accent: true, key: "us" as const },
            { title: "Traditional Screeners", accent: false, key: "screeners" as const },
            { title: "Black-Box Ratings", accent: false, key: "blackbox" as const },
          ].map((col) => (
            <div key={col.title} className="terminal-card p-5 space-y-3">
              <h3 className={`text-sm font-semibold uppercase tracking-wider ${col.accent ? "text-accent" : "text-text-tertiary"}`}>
                {col.title}
              </h3>
              {ROWS.map((row) => (
                <div key={row.label} className="flex justify-between items-baseline gap-2">
                  <span className="text-xs text-text-tertiary">{row.label}</span>
                  <span className={`text-sm text-right ${col.accent ? "text-text-primary" : "text-text-tertiary"}`}>
                    {row[col.key]}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/landing/sections/__tests__/comparison-section.test.tsx`
Expected: All PASS

- [ ] **Step 5: Wire into homepage-client.tsx**

In `web/src/components/landing/homepage-client.tsx`, add the import and insert between `EvidenceSection` and `PricingSection`:

```typescript
import { ComparisonSection } from "./sections/comparison-section"
// ...
<EvidenceSection ... />
<PipelineSection data={data} />
<ResultsShowcaseSection data={data} />
<ComparisonSection />
<PricingSection totalUniverse={data?.total_universe} />
```

- [ ] **Step 6: Commit (do not push — bundled PR)**

```bash
git add web/src/components/landing/sections/comparison-section.tsx web/src/components/landing/sections/__tests__/comparison-section.test.tsx web/src/components/landing/homepage-client.tsx
git commit -m "feat(web): add comparison table to landing page"
```

---

### Task 10: Public Explore / Top Picks Page

**Files:**
- Create: `web/src/app/explore/page.tsx`
- Create: `web/src/components/explore/explore-client.tsx`
- Create: `web/src/components/explore/__tests__/explore-client.test.tsx`
- Modify: `web/src/hooks/use-navigation.ts`
- Modify: `web/src/components/landing/sections/footer-section.tsx`

- [ ] **Step 1: Write the test for explore-client**

Create `web/src/components/explore/__tests__/explore-client.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ExploreClient } from "../explore-client"

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}))

const mockScores = {
  items: [
    {
      ticker: "AAPL",
      company_name: "Apple Inc.",
      sector: "Technology",
      composite_percentile: 85,
      composite_tier: "high",
    },
    {
      ticker: "MSFT",
      company_name: "Microsoft Corp.",
      sector: "Technology",
      composite_percentile: 78,
      composite_tier: "high",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
}

describe("ExploreClient", () => {
  it("renders score cards for initial data", () => {
    render(<ExploreClient initialData={mockScores} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
  })

  it("renders company names", () => {
    render(<ExploreClient initialData={mockScores} />)
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders empty state when no data", () => {
    render(<ExploreClient initialData={{ items: [], total: 0, page: 1, page_size: 20 }} />)
    expect(screen.getByText(/no scored assets/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/explore/__tests__/explore-client.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement explore-client.tsx**

Create `web/src/components/explore/explore-client.tsx`:

```typescript
"use client"

import Link from "next/link"

interface ScoreItem {
  ticker: string
  company_name: string
  sector: string
  composite_percentile: number
  composite_tier: string
}

interface ScoreListData {
  items: ScoreItem[]
  total: number
  page: number
  page_size: number
}

interface ExploreClientProps {
  initialData: ScoreListData
}

function tierColor(tier: string): string {
  switch (tier) {
    case "exceptional": return "text-accent"
    case "high": return "text-[var(--color-bullish)]"
    case "medium": return "text-text-primary"
    case "low": return "text-[var(--color-warning)]"
    default: return "text-text-tertiary"
  }
}

export function ExploreClient({ initialData }: ExploreClientProps) {
  const { items } = initialData

  if (items.length === 0) {
    return (
      <div className="terminal-card p-12 text-center">
        <p className="text-text-secondary">No scored assets available right now. Check back after the next scoring cycle.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <Link
          key={item.ticker}
          href={`/asset/${item.ticker}`}
          className="terminal-card p-5 flex items-center justify-between gap-4 hover:bg-bg-elevated/80 transition-colors group"
        >
          <div className="flex items-center gap-4 min-w-0">
            <span className="text-lg font-mono font-semibold text-text-primary w-16 shrink-0">
              {item.ticker}
            </span>
            <div className="min-w-0">
              <p className="text-sm text-text-primary truncate">{item.company_name}</p>
              <p className="text-xs text-text-tertiary">{item.sector}</p>
            </div>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <span className={`text-lg font-mono font-semibold ${tierColor(item.composite_tier)}`}>
                {item.composite_percentile}
              </span>
              <span className="text-xs text-text-tertiary ml-1">/ 100</span>
            </div>
            <span className="text-xs text-text-tertiary group-hover:text-accent transition-colors">
              View &rarr;
            </span>
          </div>
        </Link>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/explore/__tests__/explore-client.test.tsx`
Expected: All PASS

- [ ] **Step 5: Create the server page component**

Create `web/src/app/explore/page.tsx`:

```typescript
import type { Metadata } from "next"
import { serverFetch } from "@/lib/api/server"
import { ExploreClient } from "@/components/explore/explore-client"

export const metadata: Metadata = {
  title: "Explore Top Picks — Margin Invest",
  description:
    "Browse the highest-scoring US equities from this scoring cycle. Every score is sector-neutral, deterministic, and auditable.",
}

interface ScoreListResponse {
  items: Array<{
    ticker: string
    company_name: string
    sector: string
    composite_percentile: number
    composite_tier: string
  }>
  total: number
  page: number
  page_size: number
}

async function getTopPicks(): Promise<ScoreListResponse> {
  try {
    return await serverFetch<ScoreListResponse>(
      "/api/v1/scores?page=1&page_size=20&min_percentile=70"
    )
  } catch {
    return { items: [], total: 0, page: 1, page_size: 20 }
  }
}

export default async function ExplorePage() {
  const data = await getTopPicks()

  return (
    <div className="min-h-screen bg-bg-primary">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h1 className="text-[32px] md:text-[40px] font-bold text-text-primary tracking-tight mb-3">
            This Week&apos;s Top Picks
          </h1>
          <p className="text-body text-text-secondary max-w-lg mx-auto">
            The highest-scoring equities from our latest scoring cycle. Every score is
            sector-neutral, deterministic, and auditable to the formula.
          </p>
        </div>
        <ExploreClient initialData={data} />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Add Explore to public nav links and footer**

In `web/src/hooks/use-navigation.ts`, add Explore to `PUBLIC_LINKS`:

```typescript
const PUBLIC_LINKS: { href: string; label: string }[] = [
  { href: "/login", label: "Dashboard" },
  { href: "/explore", label: "Explore" },
  { href: "/methodology", label: "Methodology" },
  { href: "/guides", label: "Guides" },
  { href: "/#pricing", label: "Pricing" },
]
```

In `web/src/components/landing/sections/footer-section.tsx`, add `{ href: "/explore", label: "Explore" }` to the Product links array.

- [ ] **Step 7: Commit (do not push — bundled PR)**

```bash
git add web/src/app/explore/ web/src/components/explore/ web/src/hooks/use-navigation.ts web/src/components/landing/sections/footer-section.tsx
git commit -m "feat(web): add public explore page with top-scoring assets"
```

---

### Task 11: About / Founder Page

**Files:**
- Create: `web/src/app/about/page.tsx`
- Modify: `web/src/components/landing/sections/footer-section.tsx`

- [ ] **Step 1: Create about page**

Create `web/src/app/about/page.tsx`:

```typescript
import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "About — Margin Invest",
  description:
    "Why we built a deterministic investment analysis system. Our mission, methodology, and the team behind it.",
}

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-bg-primary">
      <div className="max-w-2xl mx-auto px-6 py-16 space-y-16">
        {/* Section 1: Why This Exists */}
        <section className="space-y-4">
          <h1 className="text-[32px] md:text-[40px] font-bold text-text-primary tracking-tight">
            Why This Exists
          </h1>
          <div className="space-y-4 text-body text-text-secondary leading-relaxed">
            <p>
              Most investment analysis is narrative-driven. An analyst reads a 10-K,
              forms an opinion, and publishes a rating that reflects their confidence,
              biases, and incentives — not the data.
            </p>
            <p>
              Margin Invest replaces that process with deterministic scoring. Five
              quantitative factors. Six forensic filters. Every formula documented.
              Every score reproducible with a spreadsheet.
            </p>
            <p>
              The system doesn&apos;t have opinions. It doesn&apos;t override its own
              output. It scores 3,000+ US equities daily with zero human discretion.
            </p>
          </div>
        </section>

        {/* Section 2: How It Works */}
        <section className="space-y-4">
          <h2 className="text-[24px] font-bold text-text-primary tracking-tight">
            How It Works
          </h2>
          <p className="text-body text-text-secondary leading-relaxed">
            Every equity is scored across quality, value, momentum, sentiment, and
            growth — ranked within its GICS sector to eliminate cross-sector bias.
            Before scoring, six forensic filters (including Beneish M-Score and
            Altman Z-Score) eliminate candidates with accounting red flags.
          </p>
          <Link
            href="/methodology"
            className="inline-block text-sm text-accent hover:underline underline-offset-2"
          >
            Read the full methodology &rarr;
          </Link>
        </section>

        {/* Section 3: Who Built It */}
        <section className="space-y-4">
          <h2 className="text-[24px] font-bold text-text-primary tracking-tight">
            Who Built It
          </h2>
          <p className="text-body text-text-secondary leading-relaxed">
            {/* Founder content to be provided during implementation */}
            Built by an engineer who got tired of paying for black-box ratings.
          </p>
        </section>

        {/* Section 4: Contact */}
        <section className="space-y-4">
          <h2 className="text-[24px] font-bold text-text-primary tracking-tight">
            Contact
          </h2>
          <p className="text-body text-text-secondary">
            Questions, feedback, or partnership inquiries —{" "}
            <Link
              href="/contact"
              className="text-accent hover:underline underline-offset-2"
            >
              get in touch
            </Link>
            .
          </p>
        </section>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add About to footer**

In `web/src/components/landing/sections/footer-section.tsx`, add `{ href: "/about", label: "About" }` to the Company links array.

- [ ] **Step 3: Commit (do not push — bundled PR)**

```bash
git add web/src/app/about/page.tsx web/src/components/landing/sections/footer-section.tsx
git commit -m "feat(web): add about page with mission and methodology links"
```

---

### Task 12: Social Proof Section on Landing Page

**Files:**
- Create: `web/src/components/landing/sections/social-proof-section.tsx`
- Create: `web/src/components/landing/sections/__tests__/social-proof-section.test.tsx`
- Modify: `web/src/components/landing/homepage-client.tsx`

- [ ] **Step 1: Write the test**

Create `web/src/components/landing/sections/__tests__/social-proof-section.test.tsx`:

```typescript
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SocialProofSection } from "../social-proof-section"

const mockData = {
  candidates: [],
  allPicks: [],
  last_updated: "2026-03-17T12:00:00Z",
  universe_size: 3200,
  eligible_count: 200,
  total_scored: 3100,
  total_universe: 3200,
  surviving_count: 180,
}

describe("SocialProofSection", () => {
  it("renders scored positions stat", () => {
    render(<SocialProofSection data={mockData} />)
    expect(screen.getByText(/3,100/)).toBeInTheDocument()
    expect(screen.getByText(/positions scored/i)).toBeInTheDocument()
  })

  it("renders forensic filter stat", () => {
    render(<SocialProofSection data={mockData} />)
    // (3200 - 180) / 3200 * 100 ≈ 94%
    expect(screen.getByText(/94%/)).toBeInTheDocument()
  })

  it("renders auditability stat", () => {
    render(<SocialProofSection data={mockData} />)
    expect(screen.getByText(/every score links to its formula/i)).toBeInTheDocument()
  })

  it("renders null when data is null", () => {
    const { container } = render(<SocialProofSection data={null} />)
    expect(container.firstChild).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/sections/__tests__/social-proof-section.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement social-proof-section.tsx**

Create `web/src/components/landing/sections/social-proof-section.tsx`:

```typescript
import Link from "next/link"
import type { HomepageData } from "../shared/types"

interface SocialProofSectionProps {
  data: HomepageData | null
}

export function SocialProofSection({ data }: SocialProofSectionProps) {
  if (!data) return null

  const failRate = data.total_universe > 0
    ? Math.round(((data.total_universe - data.surviving_count) / data.total_universe) * 100)
    : 0

  const stats = [
    {
      value: data.total_scored.toLocaleString("en-US"),
      label: "positions scored this cycle",
      detail: "Five-factor analysis across quality, value, momentum, sentiment, and growth.",
    },
    {
      value: `${failRate}%`,
      label: "fail at least one forensic filter",
      detail: "Beneish M-Score, Altman Z-Score, and four other fraud and distress screens.",
    },
    {
      value: "100%",
      label: "every score links to its formula",
      detail: "No black boxes. Verify any score with a spreadsheet.",
      link: { href: "/methodology", text: "See methodology →" },
    },
    {
      value: "Daily",
      label: "updates, every market day",
      detail: "Automated pipeline. No human overrides. Same inputs always produce same outputs.",
    },
  ]

  return (
    <section className="py-16 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="terminal-card p-5 space-y-2">
              <p className="text-2xl font-mono font-semibold text-accent">
                {stat.value}
              </p>
              <p className="text-sm font-medium text-text-primary">
                {stat.label}
              </p>
              <p className="text-xs text-text-tertiary leading-relaxed">
                {stat.detail}
              </p>
              {stat.link && (
                <Link
                  href={stat.link.href}
                  className="inline-block text-xs text-accent hover:underline underline-offset-2 mt-1"
                >
                  {stat.link.text}
                </Link>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/landing/sections/__tests__/social-proof-section.test.tsx`
Expected: All PASS

- [ ] **Step 5: Wire into homepage-client.tsx**

In `web/src/components/landing/homepage-client.tsx`, add the import and insert after `AuthorityStrip`:

```typescript
import { SocialProofSection } from "./sections/social-proof-section"
// ...
<AuthorityStrip data={data} />
<SocialProofSection data={data} />
<EvidenceSection ... />
```

- [ ] **Step 6: Commit (do not push — bundled PR)**

```bash
git add web/src/components/landing/sections/social-proof-section.tsx web/src/components/landing/sections/__tests__/social-proof-section.test.tsx web/src/components/landing/homepage-client.tsx
git commit -m "feat(web): add social proof section to landing page"
```

---

## Final Verification

- [ ] **Run all web tests**

```bash
cd web && npx vitest run
```
Expected: All ~1370+ tests pass (plus new ones added in this plan)

- [ ] **Run lint**

```bash
cd web && npx eslint --fix .
```
Expected: No errors

---

## PR Strategy

| Phase | Commits | PR |
|-------|---------|-----|
| Phase 1 | Tasks 1-4 (4 commits) | 3 individual PRs: Task 1+3 bundled, Task 2, Task 4 |
| Phase 2 | Tasks 5-8 (4 commits) | 4 individual PRs |
| Phase 3 | Tasks 9-12 (4 commits) | 1 bundled PR |

Total: 8 PRs, 12 commits.
