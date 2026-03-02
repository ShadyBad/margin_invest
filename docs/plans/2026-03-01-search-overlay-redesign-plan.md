# Search Ticker Overlay Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the always-visible navbar ticker search input with a magnifying glass icon that opens an overlay search dialog, reducing visual clutter while improving usability.

**Architecture:** Single component rewrite of `TickerSearch`. The icon button lives in the navbar flow; the overlay uses a React portal-free fixed-position dialog. Cmd+K global shortcut. All CSS transitions via Tailwind.

**Tech Stack:** React 19, Next.js 16, Tailwind v4, Vitest + Testing Library

---

### Task 1: Write failing tests for the icon button default state

**Files:**
- Modify: `web/src/components/nav/__tests__/ticker-search.test.tsx`

**Step 1: Replace the existing test file with new tests for icon button rendering**

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TickerSearch } from "../ticker-search"

const pushMock = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

describe("TickerSearch", () => {
  beforeEach(() => {
    pushMock.mockClear()
  })

  describe("icon button (default state)", () => {
    it("renders a search button with magnifying glass icon", () => {
      render(<TickerSearch />)
      const button = screen.getByRole("button", { name: /search ticker/i })
      expect(button).toBeInTheDocument()
      expect(button.querySelector("svg")).toBeInTheDocument()
    })

    it("does not show the search overlay by default", () => {
      render(<TickerSearch />)
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })

    it("has correct ARIA attributes", () => {
      render(<TickerSearch />)
      const button = screen.getByRole("button", { name: /search ticker/i })
      expect(button).toHaveAttribute("aria-haspopup", "dialog")
      expect(button).toHaveAttribute("aria-expanded", "false")
    })
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/ticker-search.test.tsx`
Expected: FAIL — current component renders a form/input, not a button with role "button"

---

### Task 2: Implement the icon button default state

**Files:**
- Modify: `web/src/components/nav/ticker-search.tsx`

**Step 1: Rewrite TickerSearch with the icon button (no overlay yet)**

```tsx
"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"

function SearchIcon({ size = 16 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

export function TickerSearch() {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState("")
  const buttonRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()

  const close = useCallback(() => {
    setIsOpen(false)
    setQuery("")
    buttonRef.current?.focus()
  }, [])

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      const ticker = query.trim().toUpperCase()
      if (ticker) {
        router.push(`/asset/${ticker}`)
        setIsOpen(false)
        setQuery("")
      }
    },
    [query, router]
  )

  return (
    <>
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(true)}
        aria-label="Search ticker"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        className="flex items-center justify-center w-8 h-8 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-subtle transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary"
      >
        <SearchIcon />
      </button>
    </>
  )
}
```

**Step 2: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/ticker-search.test.tsx`
Expected: PASS (3 tests)

**Step 3: Commit**

```bash
git add web/src/components/nav/ticker-search.tsx web/src/components/nav/__tests__/ticker-search.test.tsx
git commit -m "feat(web): replace ticker search input with icon button"
```

---

### Task 3: Write failing tests for overlay open/close behavior

**Files:**
- Modify: `web/src/components/nav/__tests__/ticker-search.test.tsx`

**Step 1: Add overlay interaction tests after the icon button describe block**

```tsx
  describe("overlay (open state)", () => {
    it("opens the search overlay when icon is clicked", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    })

    it("sets aria-expanded to true when open", () => {
      render(<TickerSearch />)
      const button = screen.getByRole("button", { name: /search ticker/i })
      fireEvent.click(button)
      expect(button).toHaveAttribute("aria-expanded", "true")
    })

    it("auto-focuses the input when overlay opens", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      expect(input).toHaveFocus()
    })

    it("closes the overlay on Escape key", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      expect(screen.getByRole("dialog")).toBeInTheDocument()
      fireEvent.keyDown(screen.getByLabelText(/ticker symbol/i), { key: "Escape" })
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })

    it("closes the overlay on backdrop click", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const backdrop = screen.getByTestId("search-backdrop")
      fireEvent.click(backdrop)
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })

    it("has correct ARIA attributes on the dialog", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const dialog = screen.getByRole("dialog")
      expect(dialog).toHaveAttribute("aria-label", "Ticker search")
      expect(dialog).toHaveAttribute("aria-modal", "true")
    })
  })
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/ticker-search.test.tsx`
Expected: FAIL — no dialog element rendered yet

---

### Task 4: Implement the overlay open/close behavior

**Files:**
- Modify: `web/src/components/nav/ticker-search.tsx`

**Step 1: Add the overlay JSX after the button in the fragment**

In `ticker-search.tsx`, replace the empty fragment closing `</>` with the overlay. The full return statement becomes:

```tsx
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        close()
      }
    },
    [close]
  )

  return (
    <>
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(true)}
        aria-label="Search ticker"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        className="flex items-center justify-center w-8 h-8 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-subtle transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary"
      >
        <SearchIcon />
      </button>

      {isOpen && (
        <>
          <div
            data-testid="search-backdrop"
            className="fixed inset-0 z-[60] bg-black/20"
            onClick={close}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-label="Ticker search"
            aria-modal="true"
            className="fixed z-[61] top-3 left-1/2 -translate-x-1/2 w-[min(400px,calc(100vw-48px))] animate-in fade-in zoom-in-95 duration-200"
          >
            <form onSubmit={handleSubmit} className="relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none">
                <SearchIcon />
              </div>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search any ticker..."
                aria-label="Ticker symbol"
                className="w-full h-11 pl-10 pr-4 text-sm bg-bg-elevated border border-border-subtle rounded-xl text-text-primary placeholder-text-tertiary shadow-[0_4px_24px_rgba(0,0,0,0.2)] focus:outline-none focus:border-accent/40 transition-colors"
              />
            </form>
          </div>
        </>
      )}
    </>
  )
```

Note: The `useEffect` for auto-focus and `handleKeyDown` go above the return statement, after the existing `handleSubmit`. The `close` function already exists from Task 2.

**Step 2: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/ticker-search.test.tsx`
Expected: PASS (9 tests)

**Step 3: Commit**

```bash
git add web/src/components/nav/ticker-search.tsx web/src/components/nav/__tests__/ticker-search.test.tsx
git commit -m "feat(web): add search overlay with open/close behavior"
```

---

### Task 5: Write failing tests for submit and Cmd+K shortcut

**Files:**
- Modify: `web/src/components/nav/__tests__/ticker-search.test.tsx`

**Step 1: Add submit and keyboard shortcut tests**

```tsx
  describe("submit behavior", () => {
    it("navigates to /asset/{TICKER} on submit", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      fireEvent.change(input, { target: { value: "TSLA" } })
      fireEvent.submit(input.closest("form")!)
      expect(pushMock).toHaveBeenCalledWith("/asset/TSLA")
    })

    it("uppercases the ticker before navigating", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      fireEvent.change(input, { target: { value: "aapl" } })
      fireEvent.submit(input.closest("form")!)
      expect(pushMock).toHaveBeenCalledWith("/asset/AAPL")
    })

    it("does not navigate on empty input", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      fireEvent.change(input, { target: { value: "   " } })
      fireEvent.submit(input.closest("form")!)
      expect(pushMock).not.toHaveBeenCalled()
    })

    it("closes the overlay after successful submit", () => {
      render(<TickerSearch />)
      fireEvent.click(screen.getByRole("button", { name: /search ticker/i }))
      const input = screen.getByLabelText(/ticker symbol/i)
      fireEvent.change(input, { target: { value: "MSFT" } })
      fireEvent.submit(input.closest("form")!)
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
  })

  describe("keyboard shortcut", () => {
    it("opens overlay on Cmd+K", () => {
      render(<TickerSearch />)
      fireEvent.keyDown(document, { key: "k", metaKey: true })
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    })

    it("opens overlay on Ctrl+K", () => {
      render(<TickerSearch />)
      fireEvent.keyDown(document, { key: "k", ctrlKey: true })
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    })

    it("does not open on plain K key", () => {
      render(<TickerSearch />)
      fireEvent.keyDown(document, { key: "k" })
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    })
  })
```

**Step 2: Run tests to verify the Cmd+K tests fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/ticker-search.test.tsx`
Expected: Submit tests PASS (already implemented in Task 4). Cmd+K tests FAIL — no global keydown listener yet.

---

### Task 6: Implement Cmd+K keyboard shortcut

**Files:**
- Modify: `web/src/components/nav/ticker-search.tsx`

**Step 1: Add a global keydown useEffect after the auto-focus useEffect**

```tsx
  useEffect(() => {
    function handleGlobalKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setIsOpen(true)
      }
    }
    document.addEventListener("keydown", handleGlobalKeyDown)
    return () => document.removeEventListener("keydown", handleGlobalKeyDown)
  }, [])
```

**Step 2: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/ticker-search.test.tsx`
Expected: PASS (all 16 tests)

**Step 3: Commit**

```bash
git add web/src/components/nav/ticker-search.tsx web/src/components/nav/__tests__/ticker-search.test.tsx
git commit -m "feat(web): add Cmd+K shortcut and submit tests for search overlay"
```

---

### Task 7: Run the full web test suite to verify no regressions

**Files:** None changed — verification only.

**Step 1: Run the full web test suite**

Run: `cd web && npx vitest run`
Expected: All ~1285 tests pass. The navbar test should still pass since it just renders `<TickerSearch />` and doesn't query for the old input directly.

**Step 2: Check the navbar test specifically**

Run: `cd web && npx vitest run src/components/nav/__tests__/navbar.test.tsx`
Expected: PASS — if any test was querying for the old placeholder input in the navbar context, it will fail and needs updating.

**Step 3: Fix any broken navbar tests if needed**

If `navbar.test.tsx` queries for `screen.getByPlaceholderText(/Search any ticker/i)`, update it to query for the button: `screen.getByRole("button", { name: /search ticker/i })`.

**Step 4: Commit any fixes**

```bash
git add -u
git commit -m "test(web): fix navbar tests for search overlay redesign"
```

---

### Task 8: Visual QA in the browser

**Files:** None changed — manual verification.

**Step 1: Start the dev server**

Run: `cd web && npm run dev`

**Step 2: Verify these interactions in the browser**

1. Magnifying glass icon visible in navbar, same size as theme toggle
2. Click icon → overlay appears with smooth animation, input focused
3. Type "AAPL" + Enter → navigates to `/asset/AAPL`, overlay closes
4. Click icon → overlay appears → press Escape → overlay closes, focus returns to icon
5. Click icon → overlay appears → click backdrop → overlay closes
6. Press Cmd+K → overlay opens
7. Toggle dark/light mode → icon and overlay colors adapt correctly
8. Resize to mobile → icon is hidden (search is in mobile menu only)

**Step 3: Final commit if any tweaks were needed**

```bash
git add -u
git commit -m "fix(web): visual polish for search overlay"
```
