# Header Alignment Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Center the search overlay vertically within the navbar when opened.

**Architecture:** Change one Tailwind class (`top-3` → `top-[23px]`) on the search overlay div so it aligns with the navbar's vertical center instead of floating 4px above it.

**Tech Stack:** Next.js 15, Tailwind CSS, React

---

### Task 1: Fix search overlay vertical position

**Files:**
- Modify: `web/src/components/nav/ticker-search.tsx:102`
- Test: `web/src/components/nav/__tests__/ticker-search.test.tsx` (existing)

**Step 1: Write the failing test**

Add a test that checks the overlay has the correct `top` class:

```tsx
it("positions overlay at top-[23px] to center in navbar", async () => {
  const user = userEvent.setup();
  render(<TickerSearch />);
  await user.click(screen.getByRole("button", { name: /search ticker/i }));
  const dialog = screen.getByRole("dialog");
  expect(dialog.className).toContain("top-[23px]");
});
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/nav/__tests__/ticker-search.test.tsx`
Expected: FAIL — dialog has `top-3` not `top-[23px]`

**Step 3: Fix the class**

In `web/src/components/nav/ticker-search.tsx` line 102, change:
```tsx
// Before
className="fixed z-[61] top-3 left-1/2 w-[min(400px,calc(100vw-48px))] search-overlay-enter"

// After
className="fixed z-[61] top-[23px] left-1/2 w-[min(400px,calc(100vw-48px))] search-overlay-enter"
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/nav/__tests__/ticker-search.test.tsx`
Expected: ALL PASS

**Step 5: Visual verification**

Run: `cd web && npm run dev`
Open browser, click search icon or press Cmd+K. Confirm the overlay input is vertically centered within the navbar.

**Step 6: Commit**

```bash
git add web/src/components/nav/ticker-search.tsx web/src/components/nav/__tests__/ticker-search.test.tsx
git commit -m "fix(web): center search overlay vertically in navbar"
```
