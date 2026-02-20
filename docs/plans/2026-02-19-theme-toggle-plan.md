# Theme Toggle Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an accessible light/dark theme toggle button to the navbar, persisting user choice and respecting system preference.

**Architecture:** Create a `ThemeToggle` component using `next-themes`' `useTheme()` hook. Place it in the navbar's right-side slot (visible to all users) and in the mobile menu. Fix hardcoded dark-only hex values in nav components so they respond to theme changes via existing CSS variables.

**Tech Stack:** Next.js 15, next-themes 0.4.6, Tailwind CSS 4 (CSS variable design tokens), Vitest + React Testing Library

---

### Task 1: Create ThemeToggle component with tests

**Files:**
- Create: `web/src/components/nav/theme-toggle.tsx`
- Create: `web/src/components/nav/__tests__/theme-toggle.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/nav/__tests__/theme-toggle.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ThemeToggle } from "../theme-toggle"

// Mock next-themes
const mockSetTheme = vi.fn()
let mockResolvedTheme = "dark"
let mockMounted = true

vi.mock("next-themes", () => ({
  useTheme: () => ({
    resolvedTheme: mockResolvedTheme,
    setTheme: mockSetTheme,
  }),
}))

// Mock mounted state — ThemeToggle uses useState+useEffect for mount detection.
// We test the mounted path; the unmounted placeholder is a visual-only concern.

describe("ThemeToggle", () => {
  beforeEach(() => {
    mockSetTheme.mockClear()
    mockResolvedTheme = "dark"
  })

  it("renders a button with accessible label", () => {
    render(<ThemeToggle />)
    expect(screen.getByRole("button", { name: /switch to light mode/i })).toBeInTheDocument()
  })

  it("shows sun icon in dark mode (meaning: switch to light)", () => {
    mockResolvedTheme = "dark"
    render(<ThemeToggle />)
    const button = screen.getByRole("button", { name: /switch to light mode/i })
    // Sun icon has a circle element
    expect(button.querySelector("svg")).toBeInTheDocument()
  })

  it("shows moon icon in light mode (meaning: switch to dark)", () => {
    mockResolvedTheme = "light"
    render(<ThemeToggle />)
    const button = screen.getByRole("button", { name: /switch to dark mode/i })
    expect(button.querySelector("svg")).toBeInTheDocument()
  })

  it("calls setTheme('light') when clicked in dark mode", async () => {
    mockResolvedTheme = "dark"
    const u = userEvent.setup()
    render(<ThemeToggle />)
    await u.click(screen.getByRole("button", { name: /switch to light mode/i }))
    expect(mockSetTheme).toHaveBeenCalledWith("light")
  })

  it("calls setTheme('dark') when clicked in light mode", async () => {
    mockResolvedTheme = "light"
    const u = userEvent.setup()
    render(<ThemeToggle />)
    await u.click(screen.getByRole("button", { name: /switch to dark mode/i }))
    expect(mockSetTheme).toHaveBeenCalledWith("dark")
  })

  it("has correct aria-label for dark mode", () => {
    mockResolvedTheme = "dark"
    render(<ThemeToggle />)
    expect(screen.getByRole("button")).toHaveAttribute("aria-label", "Switch to light mode")
  })

  it("has correct aria-label for light mode", () => {
    mockResolvedTheme = "light"
    render(<ThemeToggle />)
    expect(screen.getByRole("button")).toHaveAttribute("aria-label", "Switch to dark mode")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/theme-toggle.test.tsx`

Expected: FAIL — module `../theme-toggle` not found.

**Step 3: Implement ThemeToggle component**

Create `web/src/components/nav/theme-toggle.tsx`:

```tsx
"use client"

import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

function SunIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    // Invisible placeholder to prevent layout shift during SSR
    return <div className="w-8 h-8" />
  }

  const isDark = resolvedTheme === "dark"

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="flex items-center justify-center w-8 h-8 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-subtle transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary"
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </button>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/theme-toggle.test.tsx`

Expected: 7 tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/nav/theme-toggle.tsx web/src/components/nav/__tests__/theme-toggle.test.tsx
git commit -m "feat(web): add ThemeToggle component with tests"
```

---

### Task 2: Add ThemeToggle to desktop navbar

**Files:**
- Modify: `web/src/components/nav/navbar.tsx`
- Modify: `web/src/components/nav/__tests__/navbar.test.tsx`

**Step 1: Update navbar test to expect toggle**

Add to the end of the `describe("Navbar")` block in `web/src/components/nav/__tests__/navbar.test.tsx`:

```tsx
it("renders theme toggle button", () => {
  render(<Navbar />)
  expect(screen.getByRole("button", { name: /switch to (light|dark) mode/i })).toBeInTheDocument()
})
```

Also add the `next-themes` mock at the top of the file (after the existing mocks):

```tsx
vi.mock("next-themes", () => ({
  useTheme: () => ({
    resolvedTheme: "dark",
    setTheme: vi.fn(),
  }),
}))
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/navbar.test.tsx`

Expected: FAIL — no button matching "switch to light/dark mode" found.

**Step 3: Add ThemeToggle to navbar**

In `web/src/components/nav/navbar.tsx`:

Add import at top:

```tsx
import { ThemeToggle } from "./theme-toggle"
```

Replace the desktop right-side div (lines 25-30) with:

```tsx
<div className="hidden md:flex items-center gap-3">
  {nav.cta && <NavCTA cta={nav.cta} />}
  <ThemeToggle />
  {nav.user && (
    <UserDropdown user={nav.user} />
  )}
</div>
```

The `<ThemeToggle />` is placed between the CTA and UserDropdown so it's always visible regardless of auth state.

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/navbar.test.tsx`

Expected: All tests PASS (existing + new).

**Step 5: Commit**

```bash
git add web/src/components/nav/navbar.tsx web/src/components/nav/__tests__/navbar.test.tsx
git commit -m "feat(web): add theme toggle to desktop navbar"
```

---

### Task 3: Add ThemeToggle to mobile menu

**Files:**
- Modify: `web/src/components/nav/mobile-menu.tsx`
- Modify: `web/src/components/nav/__tests__/mobile-menu.test.tsx`

**Step 1: Read the existing mobile menu test to understand its patterns**

Read `web/src/components/nav/__tests__/mobile-menu.test.tsx` first to understand the existing mock setup and assertions.

**Step 2: Add test for theme toggle in mobile menu**

Add the `next-themes` mock at the top of the test file (same pattern as navbar test):

```tsx
vi.mock("next-themes", () => ({
  useTheme: () => ({
    resolvedTheme: "dark",
    setTheme: vi.fn(),
  }),
}))
```

Add a test case:

```tsx
it("renders theme toggle when menu is open", () => {
  render(<MobileMenu nav={mockNav} isOpen={true} onClose={vi.fn()} />)
  expect(screen.getByRole("button", { name: /switch to (light|dark) mode/i })).toBeInTheDocument()
})
```

Adapt the mock variable name (`mockNav`) to match whatever the existing test file uses for its nav prop.

**Step 3: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/mobile-menu.test.tsx`

Expected: FAIL — no button matching theme toggle.

**Step 4: Add ThemeToggle to mobile menu**

In `web/src/components/nav/mobile-menu.tsx`:

Add import at top:

```tsx
import { ThemeToggle } from "./theme-toggle"
```

Add `<ThemeToggle />` inside the mobile menu, in the bottom section near CTA/user items. Place it just before the CTA button or user section, inside the `<div className="mt-3 pt-3 border-t border-border-subtle">` div. Add it as the first child with a flex row wrapper:

```tsx
<div className="mt-3 pt-3 border-t border-border-subtle">
  <div className="flex items-center justify-between py-2">
    <span className="text-[13px] text-text-tertiary">Theme</span>
    <ThemeToggle />
  </div>
  {nav.cta && (
    // ... existing CTA code
  )}
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/mobile-menu.test.tsx`

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add web/src/components/nav/mobile-menu.tsx web/src/components/nav/__tests__/mobile-menu.test.tsx
git commit -m "feat(web): add theme toggle to mobile menu"
```

---

### Task 4: Fix hardcoded dark-only colors in nav components

**Files:**
- Modify: `web/src/components/nav/navbar.tsx`
- Modify: `web/src/components/nav/mobile-menu.tsx`
- Modify: `web/src/components/nav/user-dropdown.tsx`

**Step 1: Fix navbar.tsx**

In `web/src/components/nav/navbar.tsx`, replace the hardcoded background on the inner div:

Old:
```
bg-[#111113] dark:bg-[#111113] light:bg-[#FAFAF9]
```

New:
```
bg-bg-elevated
```

The full className for the inner div becomes:
```
flex items-center justify-between bg-bg-elevated border border-border-subtle rounded-2xl px-6 py-3 shadow-[0_2px_16px_rgba(0,0,0,0.3)]
```

**Step 2: Fix mobile-menu.tsx**

Replace hardcoded background:

Old:
```
bg-[#111113] dark:bg-[#111113]
```

New:
```
bg-bg-elevated
```

**Step 3: Fix user-dropdown.tsx**

Replace hardcoded background on the dropdown panel:

Old:
```
bg-[#111113]
```

New:
```
bg-bg-elevated
```

**Step 4: Run all nav tests**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run src/components/nav/__tests__/`

Expected: All tests PASS. (These tests don't assert on CSS class names, only on behavior and accessibility.)

**Step 5: Commit**

```bash
git add web/src/components/nav/navbar.tsx web/src/components/nav/mobile-menu.tsx web/src/components/nav/user-dropdown.tsx
git commit -m "fix(web): replace hardcoded nav hex colors with CSS variable tokens"
```

---

### Task 5: Run full test suite and manual verification

**Step 1: Run full web test suite**

Run: `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run`

Expected: All existing tests + new theme-toggle tests PASS.

**Step 2: Manual test plan**

Start the dev server: `cd /Users/brandon/repos/margin_invest/web && npm run dev`

Test checklist:
1. **First load (no preference):** Clear localStorage, open app → should use system theme
2. **Toggle dark → light:** Click sun icon → app switches to light mode, icon becomes moon
3. **Toggle light → dark:** Click moon icon → app switches to dark mode, icon becomes sun
4. **Persistence:** Refresh page → theme persists, no flash
5. **Navbar colors:** Verify navbar background changes between themes (no longer hardcoded dark)
6. **Mobile menu:** Open hamburger → theme toggle visible with "Theme" label
7. **Keyboard nav:** Tab to toggle button → focus ring visible → Enter to toggle
8. **Screen reader:** aria-label reads correctly for both states

**Step 3: Commit if any fixes needed**

If manual testing reveals issues, fix and commit individually.
