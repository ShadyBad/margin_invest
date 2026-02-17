# Floating Nav Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace both `NavMinimal` and `Nav` with a single premium floating pill navigation component.

**Architecture:** Single `FloatingNav` component with `variant` prop (`"public" | "app"`) that controls which links and right-side content appear. The component is a `"use client"` component using `usePathname`, `useSession`, and `useState` (for mobile menu). Pure CSS transitions, no framer-motion. Migration updates `AppShell`, landing page, and methodology page, then deletes the old nav components.

**Tech Stack:** Next.js 15 App Router, React 19, Tailwind CSS 4, next-auth, next-themes (removed from nav)

---

### Task 1: FloatingNav Component — Desktop Layout

**Files:**
- Create: `web/src/components/nav/floating-nav.tsx`

**Step 1: Create the component with desktop layout**

```tsx
"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import { useState } from "react"
import { Avatar } from "@/components/ui/avatar"

const publicLinks = [
  { href: "/methodology", label: "Methodology" },
  { href: "/guides", label: "Guides" },
  { href: "/support", label: "Support" },
]

const appLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/backtesting", label: "Backtesting" },
  { href: "/settings", label: "Settings" },
]

function LogoIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      stroke="currentColor"
      aria-hidden="true"
    >
      <polyline points="2,16 6,6 10,12 14,4 18,16" />
    </svg>
  )
}

interface FloatingNavProps {
  variant: "public" | "app"
}

export function FloatingNav({ variant }: FloatingNavProps) {
  const pathname = usePathname()
  const { data: session } = useSession()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const links = variant === "public" ? publicLinks : appLinks

  return (
    <nav
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-32px)] max-w-[900px]"
      aria-label="Main navigation"
    >
      <div className="flex items-center justify-between bg-[#111113] dark:bg-[#111113] light:bg-[#FAFAF9] border border-border-subtle rounded-2xl px-6 py-3 shadow-[0_2px_16px_rgba(0,0,0,0.3)]">
        {/* Logo */}
        <Link
          href="/"
          className="text-text-primary opacity-80 hover:opacity-100 transition-opacity duration-200"
          aria-label="Margin Invest home"
        >
          <LogoIcon />
        </Link>

        {/* Desktop center links */}
        <div className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-[14px] font-medium tracking-[-0.01em] transition-colors duration-200 ease-out ${
                pathname === link.href
                  ? "text-text-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Desktop right side */}
        <div className="hidden md:flex items-center gap-3">
          {variant === "public" ? (
            <Link
              href="/dashboard"
              className="bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2 hover:bg-bg-subtle transition-colors duration-200 ease-out"
            >
              Dashboard
            </Link>
          ) : session?.user ? (
            <div className="flex items-center gap-3">
              <Avatar
                name={session.user.name || session.user.email || ""}
                avatarUrl={session.avatarUrl}
                oauthAvatarUrl={session.oauthAvatarUrl ?? session.user.image}
                size="sm"
              />
              <button
                onClick={() => signOut()}
                className="text-[13px] text-text-secondary hover:text-text-primary transition-colors duration-200 ease-out"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2 hover:bg-bg-subtle transition-colors duration-200 ease-out"
            >
              Sign In
            </Link>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden text-text-primary"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
          aria-expanded={mobileMenuOpen}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            {mobileMenuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-2 bg-[#111113] dark:bg-[#111113] border border-border-subtle rounded-2xl px-6 py-4">
          <div className="flex flex-col gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-[14px] font-medium py-3 transition-colors duration-200 ease-out ${
                  pathname === link.href
                    ? "text-text-primary"
                    : "text-text-secondary hover:text-text-primary"
                }`}
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-border-subtle">
            {variant === "public" ? (
              <Link
                href="/dashboard"
                className="block text-center bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2.5 hover:bg-bg-subtle transition-colors duration-200 ease-out"
                onClick={() => setMobileMenuOpen(false)}
              >
                Dashboard
              </Link>
            ) : session?.user ? (
              <div className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <Avatar
                    name={session.user.name || session.user.email || ""}
                    avatarUrl={session.avatarUrl}
                    oauthAvatarUrl={session.oauthAvatarUrl ?? session.user.image}
                    size="sm"
                  />
                  <span className="text-[13px] text-text-secondary">
                    {session.user.name || session.user.email}
                  </span>
                </div>
                <button
                  onClick={() => signOut()}
                  className="text-[13px] text-text-secondary hover:text-text-primary transition-colors duration-200 ease-out"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="block text-center bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2.5 hover:bg-bg-subtle transition-colors duration-200 ease-out"
                onClick={() => setMobileMenuOpen(false)}
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/components/nav/floating-nav.tsx
git commit -m "feat(web): add FloatingNav component"
```

---

### Task 2: FloatingNav Tests

**Files:**
- Create: `web/src/components/nav/__tests__/floating-nav.test.tsx`

**Step 1: Write tests**

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { FloatingNav } from "../floating-nav"

// Mock next-auth/react
const mockSignOut = vi.fn()
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: (...args: any[]) => mockSignOut(...args),
}))

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}))

describe("FloatingNav", () => {
  describe("public variant", () => {
    it("renders public links", () => {
      render(<FloatingNav variant="public" />)
      expect(screen.getByText("Methodology")).toBeInTheDocument()
      expect(screen.getByText("Guides")).toBeInTheDocument()
      expect(screen.getByText("Support")).toBeInTheDocument()
    })

    it("does not render app links", () => {
      render(<FloatingNav variant="public" />)
      expect(screen.queryByText("Backtesting")).not.toBeInTheDocument()
      expect(screen.queryByText("Settings")).not.toBeInTheDocument()
    })

    it("renders Dashboard CTA button", () => {
      render(<FloatingNav variant="public" />)
      const ctas = screen.getAllByText("Dashboard")
      expect(ctas.length).toBeGreaterThanOrEqual(1)
    })

    it("renders logo link to home", () => {
      render(<FloatingNav variant="public" />)
      const logo = screen.getByLabelText("Margin Invest home")
      expect(logo).toHaveAttribute("href", "/")
    })
  })

  describe("app variant", () => {
    it("renders app links", () => {
      render(<FloatingNav variant="app" />)
      expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText("Backtesting")).toBeInTheDocument()
      expect(screen.getByText("Settings")).toBeInTheDocument()
    })

    it("does not render public links", () => {
      render(<FloatingNav variant="app" />)
      expect(screen.queryByText("Methodology")).not.toBeInTheDocument()
      expect(screen.queryByText("Guides")).not.toBeInTheDocument()
      expect(screen.queryByText("Support")).not.toBeInTheDocument()
    })

    it("highlights active link", () => {
      render(<FloatingNav variant="app" />)
      const dashboardLinks = screen.getAllByText("Dashboard")
      // Desktop link should be active (text-text-primary)
      expect(dashboardLinks[0].className).toContain("text-text-primary")
    })

    it("shows Sign In when not authenticated", () => {
      render(<FloatingNav variant="app" />)
      expect(screen.getAllByText("Sign In").length).toBeGreaterThanOrEqual(1)
    })
  })

  describe("mobile menu", () => {
    it("toggles mobile menu", async () => {
      const user = userEvent.setup()
      render(<FloatingNav variant="app" />)
      const menuButton = screen.getByLabelText("Toggle menu")

      // Only desktop links visible initially
      expect(screen.getAllByText("Dashboard")).toHaveLength(1)

      // Open mobile menu
      await user.click(menuButton)

      // Desktop + mobile links now visible
      expect(screen.getAllByText("Dashboard")).toHaveLength(2)
    })

    it("closes mobile menu when link is clicked", async () => {
      const user = userEvent.setup()
      render(<FloatingNav variant="app" />)

      // Open menu
      await user.click(screen.getByLabelText("Toggle menu"))
      expect(screen.getAllByText("Backtesting")).toHaveLength(2)

      // Click mobile link
      const mobileLinks = screen.getAllByText("Backtesting")
      await user.click(mobileLinks[1])

      // Menu closed
      expect(screen.getAllByText("Backtesting")).toHaveLength(1)
    })

    it("has aria-expanded attribute", async () => {
      const user = userEvent.setup()
      render(<FloatingNav variant="app" />)
      const menuButton = screen.getByLabelText("Toggle menu")

      expect(menuButton).toHaveAttribute("aria-expanded", "false")
      await user.click(menuButton)
      expect(menuButton).toHaveAttribute("aria-expanded", "true")
    })
  })

  it("renders a nav element with aria-label", () => {
    const { container } = render(<FloatingNav variant="public" />)
    const nav = container.querySelector("nav")
    expect(nav).toBeInTheDocument()
    expect(nav).toHaveAttribute("aria-label", "Main navigation")
  })
})
```

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/nav/__tests__/floating-nav.test.tsx`

Expected: All tests pass.

**Step 3: Commit**

```bash
git add web/src/components/nav/__tests__/floating-nav.test.tsx
git commit -m "test(web): add FloatingNav tests"
```

---

### Task 3: Migrate AppShell to use FloatingNav

**Files:**
- Modify: `web/src/components/layout/app-shell.tsx`
- Modify: `web/src/components/layout/index.ts`
- Modify: `web/src/components/layout/__tests__/app-shell.test.tsx`

**Step 1: Update AppShell**

Replace the contents of `web/src/components/layout/app-shell.tsx` with:

```tsx
import { FloatingNav } from "@/components/nav/floating-nav"

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg-primary">
      <FloatingNav variant="app" />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-8">
        {children}
      </main>
    </div>
  )
}
```

Note: `py-8` changed to `pt-24 pb-8` to account for the floating nav's height + offset.

**Step 2: Update barrel export**

Replace `web/src/components/layout/index.ts` with:

```ts
export { AppShell } from "./app-shell"
```

(Remove the `Nav` re-export since it will be deleted.)

**Step 3: Update AppShell tests**

Replace `web/src/components/layout/__tests__/app-shell.test.tsx` with:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AppShell } from "../app-shell"

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}))

describe("AppShell", () => {
  it("renders children", () => {
    render(<AppShell><div data-testid="child">Content</div></AppShell>)
    expect(screen.getByTestId("child")).toBeInTheDocument()
  })

  it("includes floating navigation", () => {
    render(<AppShell><div>Content</div></AppShell>)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })

  it("renders children inside main element", () => {
    render(<AppShell><div data-testid="child">Content</div></AppShell>)
    const main = screen.getByRole("main")
    expect(main).toBeInTheDocument()
    expect(main).toContainElement(screen.getByTestId("child"))
  })
})
```

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/layout/__tests__/app-shell.test.tsx`

Expected: All 3 tests pass.

**Step 5: Commit**

```bash
git add web/src/components/layout/app-shell.tsx web/src/components/layout/index.ts web/src/components/layout/__tests__/app-shell.test.tsx
git commit -m "refactor(web): migrate AppShell to FloatingNav"
```

---

### Task 4: Migrate Marketing Pages

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/methodology/page.tsx`

**Step 1: Update landing page**

In `web/src/app/page.tsx`, replace the `NavMinimal` import and usage:

Change import from:
```tsx
import { NavMinimal } from "@/components/landing/nav-minimal"
```
To:
```tsx
import { FloatingNav } from "@/components/nav/floating-nav"
```

Change usage from:
```tsx
<NavMinimal />
```
To:
```tsx
<FloatingNav variant="public" />
```

**Step 2: Update methodology page**

In `web/src/app/methodology/page.tsx`, make the same swap:

Change import from:
```tsx
import { NavMinimal } from "@/components/landing/nav-minimal"
```
To:
```tsx
import { FloatingNav } from "@/components/nav/floating-nav"
```

Change usage from:
```tsx
<NavMinimal />
```
To:
```tsx
<FloatingNav variant="public" />
```

**Step 3: Run full test suite**

Run: `cd web && npx vitest run`

Expected: All tests pass. (The landing page `sections.test.tsx` tests don't test `NavMinimal` directly — they test sections. The `nav-minimal.test.tsx` may fail since its import source still exists — that's expected, it gets deleted in Task 5.)

**Step 4: Commit**

```bash
git add web/src/app/page.tsx web/src/app/methodology/page.tsx
git commit -m "refactor(web): migrate landing + methodology pages to FloatingNav"
```

---

### Task 5: Delete Old Nav Components

**Files:**
- Delete: `web/src/components/landing/nav-minimal.tsx`
- Delete: `web/src/components/landing/__tests__/nav-minimal.test.tsx`
- Delete: `web/src/components/layout/nav.tsx`
- Delete: `web/src/components/layout/__tests__/nav.test.tsx`

**Step 1: Delete the files**

```bash
rm web/src/components/landing/nav-minimal.tsx
rm web/src/components/landing/__tests__/nav-minimal.test.tsx
rm web/src/components/layout/nav.tsx
rm web/src/components/layout/__tests__/nav.test.tsx
```

**Step 2: Run full test suite**

Run: `cd web && npx vitest run`

Expected: All tests pass. No remaining imports reference the deleted files.

**Step 3: Commit**

```bash
git add -A web/src/components/landing/nav-minimal.tsx web/src/components/landing/__tests__/nav-minimal.test.tsx web/src/components/layout/nav.tsx web/src/components/layout/__tests__/nav.test.tsx
git commit -m "refactor(web): delete old NavMinimal and Nav components"
```

---

### Task 6: Final Verification

**Step 1: Run the full web test suite**

Run: `cd web && npx vitest run`

Expected: All tests pass with no failures.

**Step 2: Check for any remaining references to old nav components**

Run: `grep -r "NavMinimal\|from.*layout/nav\|from.*nav-minimal" web/src/ --include="*.tsx" --include="*.ts"`

Expected: No matches.

**Step 3: Verify no TypeScript errors in nav files**

Run: `cd web && npx tsc --noEmit 2>&1 | grep -i "floating-nav\|app-shell\|nav/" || echo "No nav errors"`

Expected: No nav-related errors.
