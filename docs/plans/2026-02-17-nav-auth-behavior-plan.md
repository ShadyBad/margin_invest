# Nav Auth Behavior Refactor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Login/Sign Up nav buttons with a single Dashboard button that routes to `/login` (unauth) or `/dashboard` (auth), remove Methodology from nav, and make Guides authenticated-only.

**Architecture:** All changes flow from the `useNavigation()` hook — the single source of truth for nav state. The `cta` field becomes non-null for both auth states (Dashboard button). Link arrays change. Two rendering components update to show CTA alongside user controls.

**Tech Stack:** Next.js 15, NextAuth, React, Vitest, Testing Library

---

### Task 1: Update `useNavigation` hook tests

**Files:**
- Modify: `web/src/hooks/__tests__/use-navigation.test.ts`

**Step 1: Update unauthenticated test expectations**

Replace the existing unauthenticated tests to match new behavior. The full updated `describe("unauthenticated")` block:

```ts
describe("unauthenticated", () => {
  it("returns isAuthenticated false", () => {
    const { result } = renderHook(() => useNavigation())
    expect(result.current.isAuthenticated).toBe(false)
  })

  it("returns no center links", () => {
    const { result } = renderHook(() => useNavigation())
    expect(result.current.links).toEqual([])
  })

  it("returns Dashboard CTA linking to /login", () => {
    const { result } = renderHook(() => useNavigation())
    expect(result.current.cta).not.toBeNull()
    expect(result.current.cta!.primary.label).toBe("Dashboard")
    expect(result.current.cta!.primary.href).toBe("/login")
  })

  it("returns no secondary CTA", () => {
    const { result } = renderHook(() => useNavigation())
    expect(result.current.cta!.secondary).toBeUndefined()
  })

  it("returns user as null", () => {
    const { result } = renderHook(() => useNavigation())
    expect(result.current.user).toBeNull()
  })
})
```

Delete the "marks active link based on pathname" test (no links to be active).

**Step 2: Update authenticated test expectations**

Replace the `"returns app links"` and `"returns cta as null"` tests:

```ts
it("returns Guides as center link", () => {
  const { result } = renderHook(() => useNavigation())
  const labels = result.current.links.map((l) => l.label)
  expect(labels).toEqual(["Guides"])
})

it("returns Dashboard CTA linking to /dashboard", () => {
  const { result } = renderHook(() => useNavigation())
  expect(result.current.cta).not.toBeNull()
  expect(result.current.cta!.primary.label).toBe("Dashboard")
  expect(result.current.cta!.primary.href).toBe("/dashboard")
})

it("marks Guides active based on pathname", () => {
  mockPathname = "/guides"
  const { result } = renderHook(() => useNavigation())
  const guides = result.current.links.find((l) => l.href === "/guides")
  expect(guides!.isActive).toBe(true)
})
```

**Step 3: Run tests to verify they fail**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: Multiple FAIL — hook still returns old values.

---

### Task 2: Update `useNavigation` hook implementation

**Files:**
- Modify: `web/src/hooks/use-navigation.ts`

**Step 1: Update link arrays and CTA logic**

In `use-navigation.ts`, make these changes:

1. Change `PUBLIC_LINKS` to an empty array:
```ts
const PUBLIC_LINKS: { href: string; label: string }[] = []
```

2. Change `APP_LINKS` to Guides only:
```ts
const APP_LINKS = [
  { href: "/guides", label: "Guides" },
]
```

3. Change the `cta` assignment to be set for both states:
```ts
const cta: NavigationCTA = isAuthenticated
  ? { primary: { label: "Dashboard", href: "/dashboard" } }
  : { primary: { label: "Dashboard", href: "/login" } }
```

Note: `cta` type changes from `NavigationCTA | null` to `NavigationCTA` (always set). Update the `NavigationState` interface accordingly:
```ts
cta: NavigationCTA
```

**Step 2: Run hook tests to verify they pass**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: All PASS

**Step 3: Commit**

```bash
git add web/src/hooks/use-navigation.ts web/src/hooks/__tests__/use-navigation.test.ts
git commit -m "refactor(web): update useNavigation for Dashboard button behavior"
```

---

### Task 3: Update Navbar tests and component

**Files:**
- Modify: `web/src/components/nav/__tests__/navbar.test.tsx`
- Modify: `web/src/components/nav/navbar.tsx`

**Step 1: Update Navbar test mock data and assertions**

In `navbar.test.tsx`, update the `useNavigation` mock:

Authenticated mock return:
```ts
return {
  isAuthenticated: true,
  links: [
    { href: "/guides", label: "Guides", isActive: false },
  ],
  cta: { primary: { label: "Dashboard", href: "/dashboard" } },
  user: {
    name: "Jane Doe",
    email: "jane@example.com",
    avatarUrl: null,
    oauthAvatarUrl: null,
    dropdownItems: [
      { label: "Account", href: "/account", type: "link" },
      { label: "Settings", href: "/settings", type: "link" },
      { label: "", type: "divider" },
      { label: "Sign Out", onClick: mockSignOut, type: "action" },
    ],
  },
  logoHref: "/",
}
```

Unauthenticated mock return:
```ts
return {
  isAuthenticated: false,
  links: [],
  cta: { primary: { label: "Dashboard", href: "/login" } },
  user: null,
  logoHref: "/",
}
```

Update the test assertions:

- `describe("unauthenticated")`:
  - Remove `"renders public links"` test (no center links)
  - Change `"renders Login CTA"` → `"renders Dashboard button linking to /login"`: check for text "Dashboard" and href "/login"
  - Remove `"renders Sign Up link"` test
  - Add `"does not render Guides link"` test

- `describe("authenticated")`:
  - Change `"renders app links"` → `"renders Guides center link"`: check for "Guides"
  - Add `"renders Dashboard button linking to /dashboard"`: check for text "Dashboard" and href "/dashboard"
  - Keep `"renders user avatar button"` as-is
  - Change `"does not render Login CTA"` → `"does not render Login or Sign Up"`: check both absent

- `describe("mobile")`:
  - Update toggle test: the duplicated text will be "Dashboard" (from CTA in both desktop and mobile), not "Methodology"

**Step 2: Run Navbar tests to verify they fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/navbar.test.tsx`
Expected: FAIL — component still renders old mock data shape.

**Step 3: Update Navbar component**

In `navbar.tsx`, change the right-side desktop rendering (lines 26-34) from:

```tsx
<div className="hidden md:flex items-center gap-3">
  {nav.isAuthenticated && (
    <UsagePill used={0} limit={3} />
  )}
  {nav.user ? (
    <UserDropdown user={nav.user} />
  ) : nav.cta ? (
    <NavCTA cta={nav.cta} />
  ) : null}
</div>
```

To:

```tsx
<div className="hidden md:flex items-center gap-3">
  <NavCTA cta={nav.cta} />
  {nav.isAuthenticated && (
    <UsagePill used={0} limit={3} />
  )}
  {nav.user && (
    <UserDropdown user={nav.user} />
  )}
</div>
```

NavCTA now renders unconditionally (always truthy). UsagePill and UserDropdown still only render when authenticated.

**Step 4: Run Navbar tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/navbar.test.tsx`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/navbar.tsx web/src/components/nav/__tests__/navbar.test.tsx
git commit -m "refactor(web): navbar renders Dashboard button for both auth states"
```

---

### Task 4: Update MobileMenu tests and component

**Files:**
- Modify: `web/src/components/nav/__tests__/mobile-menu.test.tsx`
- Modify: `web/src/components/nav/mobile-menu.tsx`

**Step 1: Update MobileMenu test fixtures and assertions**

Update the `publicNav` fixture:
```ts
const publicNav: NavigationState = {
  isAuthenticated: false,
  links: [],
  cta: { primary: { label: "Dashboard", href: "/login" } },
  user: null,
  logoHref: "/",
}
```

Update the `appNav` fixture:
```ts
const appNav: NavigationState = {
  isAuthenticated: true,
  links: [
    { href: "/guides", label: "Guides", isActive: false },
  ],
  cta: { primary: { label: "Dashboard", href: "/dashboard" } },
  user: {
    name: "Jane Doe",
    email: "jane@example.com",
    avatarUrl: null,
    oauthAvatarUrl: null,
    dropdownItems: [
      { label: "Account", href: "/account", type: "link" },
      { label: "Settings", href: "/settings", type: "link" },
      { label: "", type: "divider" },
      { label: "Sign Out", onClick: vi.fn(), type: "action" },
    ],
  },
  logoHref: "/",
}
```

Update assertions:
- Change `"renders links when open"` → `"renders Guides link for authenticated"` using `appNav`
- Change `"renders Login CTA for unauthenticated"` → `"renders Dashboard button for unauthenticated"`: check for "Dashboard" text
- Add `"renders Dashboard button AND user info for authenticated"`: render with `appNav`, assert both "Dashboard" and "Jane Doe" visible
- Update `"calls onClose when a link is clicked"` to use `appNav` and click "Guides" instead of "Methodology"

**Step 2: Run MobileMenu tests to verify they fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/mobile-menu.test.tsx`
Expected: FAIL

**Step 3: Update MobileMenu component**

In `mobile-menu.tsx`, change the bottom section (lines 32-95) from either/or to additive:

```tsx
<div className="mt-3 pt-3 border-t border-border-subtle">
  {nav.cta && (
    <div className="flex flex-col gap-2">
      <Link
        href={nav.cta.primary.href}
        className="block text-center bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2.5 hover:bg-bg-subtle transition-colors duration-200 ease-out"
        onClick={onClose}
      >
        {nav.cta.primary.label}
      </Link>
    </div>
  )}
  {nav.user && (
    <div className="flex flex-col gap-2 mt-3">
      <div className="flex items-center gap-3 py-2">
        <Avatar
          name={nav.user.name}
          avatarUrl={nav.user.avatarUrl}
          oauthAvatarUrl={nav.user.oauthAvatarUrl}
          size="sm"
        />
        <span className="text-[13px] text-text-secondary">
          {nav.user.name}
        </span>
      </div>
      {nav.user.dropdownItems
        .filter((item) => item.type !== "divider")
        .map((item) =>
          item.type === "link" && item.href ? (
            <Link
              key={item.label}
              href={item.href}
              className="text-[13px] text-text-secondary hover:text-text-primary py-1 transition-colors duration-200 ease-out"
              onClick={onClose}
            >
              {item.label}
            </Link>
          ) : (
            <button
              key={item.label}
              className={`text-left text-[13px] py-1 transition-colors duration-200 ease-out ${
                item.label === "Sign Out"
                  ? "text-red-400 hover:text-red-300"
                  : "text-text-secondary hover:text-text-primary"
              }`}
              onClick={() => {
                item.onClick?.()
                onClose()
              }}
            >
              {item.label}
            </button>
          )
        )}
    </div>
  )}
</div>
```

Key change: removed the ternary (`nav.user ? ... : nav.cta ? ...`). Both sections render independently — CTA always, user section only when authenticated.

**Step 4: Run MobileMenu tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/mobile-menu.test.tsx`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/mobile-menu.tsx web/src/components/nav/__tests__/mobile-menu.test.tsx
git commit -m "refactor(web): mobile menu shows Dashboard button for both auth states"
```

---

### Task 5: Update NavCTA test for Dashboard label

**Files:**
- Modify: `web/src/components/nav/__tests__/nav-cta.test.tsx`

**Step 1: Update NavCTA test fixture**

The NavCTA component itself doesn't change, but the test uses old Login/Sign Up labels. Update to reflect actual usage:

```ts
describe("NavCTA", () => {
  const cta: NavigationCTA = {
    primary: { label: "Dashboard", href: "/login" },
  }

  it("renders primary CTA as a pill button", () => {
    render(<NavCTA cta={cta} />)
    const dashboard = screen.getByText("Dashboard")
    expect(dashboard.closest("a")).toHaveAttribute("href", "/login")
    expect(dashboard.className).toContain("rounded-full")
  })

  it("renders without secondary CTA", () => {
    render(<NavCTA cta={cta} />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.queryByText("Sign Up")).not.toBeInTheDocument()
  })

  it("renders with secondary CTA when provided", () => {
    const ctaWithSecondary: NavigationCTA = {
      primary: { label: "Dashboard", href: "/login" },
      secondary: { label: "Learn More", href: "/about" },
    }
    render(<NavCTA cta={ctaWithSecondary} />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Learn More")).toBeInTheDocument()
  })
})
```

**Step 2: Run NavCTA tests**

Run: `cd web && npx vitest run src/components/nav/__tests__/nav-cta.test.tsx`
Expected: All PASS (component unchanged, just test data updated)

**Step 3: Commit**

```bash
git add web/src/components/nav/__tests__/nav-cta.test.tsx
git commit -m "test(web): update NavCTA tests to use Dashboard label"
```

---

### Task 6: Run full nav test suite and verify

**Files:** None (verification only)

**Step 1: Run all nav-related tests**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts src/components/nav/__tests__/`
Expected: All PASS across all 5 test files

**Step 2: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: All PASS. If usage-pill tests or other nav-adjacent tests reference old nav state shapes, fix them.

**Step 3: Final commit if any fixups needed**

Only if step 2 revealed breakage in other test files.
