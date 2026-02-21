# Username in User Dropdown — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the static "Account" dropdown label with the user's derived display name, linking to `/account`.

**Architecture:** New `getDisplayName()` utility in `web/src/lib/user.ts` extracts the display name (priority: `user.name` > email prefix > `"User"`). The `useNavigation` hook calls it to build dropdown items. The `UserDropdown` component gains a `title` attribute for truncation tooltips.

**Tech Stack:** TypeScript, React, Next.js 15, Vitest, @testing-library/react

---

### Task 1: `getDisplayName` utility — tests

**Files:**
- Create: `web/src/lib/__tests__/user.test.ts`

**Step 1: Write the failing tests**

```typescript
import { describe, it, expect } from "vitest"
import { getDisplayName } from "../user"

describe("getDisplayName", () => {
  it("returns email prefix for standard email", () => {
    expect(getDisplayName({ email: "bpshay13@gmail.com" })).toBe("bpshay13")
  })

  it("prefers user.name over email prefix", () => {
    expect(getDisplayName({ name: "Brandon", email: "bpshay13@gmail.com" })).toBe("Brandon")
  })

  it("ignores whitespace-only name", () => {
    expect(getDisplayName({ name: "   ", email: "bpshay13@gmail.com" })).toBe("bpshay13")
  })

  it("falls back to User when email is missing", () => {
    expect(getDisplayName({})).toBe("User")
  })

  it("falls back to User when email prefix is empty", () => {
    expect(getDisplayName({ email: "@domain.com" })).toBe("User")
  })

  it("falls back to User for undefined email", () => {
    expect(getDisplayName({ email: undefined })).toBe("User")
  })

  it("truncates names longer than 20 characters", () => {
    expect(getDisplayName({ email: "averylongemailprefix123@example.com" })).toBe(
      "averylongemailprefix…"
    )
  })

  it("does not truncate names exactly 20 characters", () => {
    expect(getDisplayName({ email: "exactly20characters!@example.com" })).toBe(
      "exactly20characters!"
    )
  })

  it("ignores empty string name", () => {
    expect(getDisplayName({ name: "", email: "test@example.com" })).toBe("test")
  })

  it("truncates long user.name too", () => {
    expect(getDisplayName({ name: "A Very Long Display Name Here" })).toBe("A Very Long Display …")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/lib/__tests__/user.test.ts`
Expected: FAIL — `../user` module not found

---

### Task 2: `getDisplayName` utility — implementation

**Files:**
- Create: `web/src/lib/user.ts`

**Step 1: Write minimal implementation**

```typescript
const MAX_DISPLAY_LENGTH = 20

interface DisplayNameUser {
  name?: string | null
  email?: string | null
}

export function getDisplayName(user: DisplayNameUser): string {
  const name = user.name?.trim()
  if (name) return truncate(name)

  const prefix = user.email?.split("@")[0]
  if (prefix) return truncate(prefix)

  return "User"
}

function truncate(value: string): string {
  if (value.length <= MAX_DISPLAY_LENGTH) return value
  return value.slice(0, MAX_DISPLAY_LENGTH) + "…"
}
```

**Step 2: Run tests to verify they pass**

Run: `cd web && npx vitest run src/lib/__tests__/user.test.ts`
Expected: All 10 tests PASS

**Step 3: Commit**

```bash
git add web/src/lib/user.ts web/src/lib/__tests__/user.test.ts
git commit -m "feat(web): add getDisplayName utility with tests"
```

---

### Task 3: Add `title` field to `UserDropdownItem` interface

**Files:**
- Modify: `web/src/hooks/use-navigation.ts:12-17` (the `UserDropdownItem` interface)

**Step 1: Add optional `title` field**

In `web/src/hooks/use-navigation.ts`, add `title?: string` to the `UserDropdownItem` interface:

```typescript
export interface UserDropdownItem {
  label: string
  title?: string
  href?: string
  onClick?: () => void
  type: "link" | "action" | "divider"
}
```

**Step 2: Run existing tests to verify nothing breaks**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: All 10 tests PASS (adding an optional field is non-breaking)

**Step 3: Commit**

```bash
git add web/src/hooks/use-navigation.ts
git commit -m "feat(web): add optional title field to UserDropdownItem"
```

---

### Task 4: Wire `getDisplayName` into `useNavigation` hook

**Files:**
- Modify: `web/src/hooks/use-navigation.ts:1-3` (imports) and `:70-71` (dropdown items)
- Modify: `web/src/hooks/__tests__/use-navigation.test.ts:103-109` (update assertions)

**Step 1: Update the test to expect the display name instead of "Account"**

In `web/src/hooks/__tests__/use-navigation.test.ts`, update the test at line 103:

Replace:
```typescript
    it("returns dropdown items including sign out", () => {
      const { result } = renderHook(() => useNavigation())
      const items = result.current.user!.dropdownItems
      const labels = items.map((i) => i.label)
      expect(labels).toContain("Account")
      expect(labels).toContain("Sign Out")
    })
```

With:
```typescript
    it("returns dropdown items with display name and sign out", () => {
      const { result } = renderHook(() => useNavigation())
      const items = result.current.user!.dropdownItems
      const labels = items.map((i) => i.label)
      expect(labels).toContain("Jane Doe")
      expect(labels).toContain("Sign Out")
    })
```

The mock session at line 59 has `name: "Jane Doe"`, so `getDisplayName` will return `"Jane Doe"`.

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: FAIL — dropdown still contains "Account" not "Jane Doe"

**Step 3: Update the hook implementation**

In `web/src/hooks/use-navigation.ts`:

Add import at the top (after existing imports):
```typescript
import { getDisplayName } from "@/lib/user"
```

Replace lines 70-71 (the dropdown items array first element):
```typescript
          { label: "Account", href: "/account", type: "link" as const },
```
With:
```typescript
          {
            label: getDisplayName(session!.user!),
            title: session!.user?.name?.trim() || session!.user?.email?.split("@")[0] || "User",
            href: "/account",
            type: "link" as const,
          },
```

Note: `title` stores the full un-truncated value for the tooltip. `label` is the (possibly truncated) display value.

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add web/src/hooks/use-navigation.ts web/src/hooks/__tests__/use-navigation.test.ts
git commit -m "feat(web): use getDisplayName for dropdown label in useNavigation"
```

---

### Task 5: Add `title` tooltip to `UserDropdown` component

**Files:**
- Modify: `web/src/components/nav/user-dropdown.tsx:72-83` (link item rendering)
- Modify: `web/src/components/nav/__tests__/user-dropdown.test.tsx` (update test fixtures + add tooltip test)

**Step 1: Update test fixture and add tooltip test**

In `web/src/components/nav/__tests__/user-dropdown.test.tsx`:

Replace the user fixture (lines 9-19):
```typescript
const user: NavigationUser = {
  name: "Jane Doe",
  email: "jane@example.com",
  avatarUrl: null,
  oauthAvatarUrl: null,
  dropdownItems: [
    { label: "jane", title: "jane", href: "/account", type: "link" },
    { label: "", type: "divider" },
    { label: "Sign Out", onClick: mockSignOut, type: "action" },
  ],
}
```

Update test at line 47 (`renders dropdown items when open`):
```typescript
  it("renders dropdown items when open", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByText("jane")).toBeInTheDocument()
    expect(screen.getByText("Sign Out")).toBeInTheDocument()
  })
```

Update test at line 51 (`renders link items as anchor tags`):
```typescript
  it("renders link items as anchor tags", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByText("jane").closest("a")).toHaveAttribute("href", "/account")
  })
```

Add new test after the anchor tags test:
```typescript
  it("renders title tooltip on link items", async () => {
    const truncatedUser: NavigationUser = {
      ...user,
      dropdownItems: [
        { label: "averylongemailprefix…", title: "averylongemailprefix123", href: "/account", type: "link" },
        { label: "", type: "divider" },
        { label: "Sign Out", onClick: mockSignOut, type: "action" },
      ],
    }
    const u = userEvent.setup()
    render(<UserDropdown user={truncatedUser} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByText("averylongemailprefix…").closest("a")).toHaveAttribute(
      "title",
      "averylongemailprefix123"
    )
  })
```

Update test at line 92 (`closes dropdown when link item is clicked`):
```typescript
  it("closes dropdown when link item is clicked", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByRole("menu")).toBeInTheDocument()
    await u.click(screen.getByText("jane"))
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/user-dropdown.test.tsx`
Expected: FAIL — title tooltip test fails (no title attribute on link)

**Step 3: Add `title` attribute to the Link element**

In `web/src/components/nav/user-dropdown.tsx`, update the link rendering block (lines 72-84):

Replace:
```tsx
            if (item.type === "link" && item.href) {
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  role="menuitem"
                  className="block px-4 py-2 text-[13px] text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors duration-150"
                  onClick={() => setIsOpen(false)}
                >
                  {item.label}
                </Link>
              )
            }
```

With:
```tsx
            if (item.type === "link" && item.href) {
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  role="menuitem"
                  title={item.title ?? item.label}
                  className="block px-4 py-2 text-[13px] text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors duration-150"
                  onClick={() => setIsOpen(false)}
                >
                  {item.label}
                </Link>
              )
            }
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/user-dropdown.test.tsx`
Expected: All 11 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/user-dropdown.tsx web/src/components/nav/__tests__/user-dropdown.test.tsx
git commit -m "feat(web): add title tooltip to dropdown link items"
```

---

### Task 6: Update mobile menu tests

**Files:**
- Modify: `web/src/components/nav/__tests__/mobile-menu.test.tsx:34-36` (update fixture)

**Step 1: Update the test fixture**

In `web/src/components/nav/__tests__/mobile-menu.test.tsx`, replace the `dropdownItems` in `appNav` (lines 34-38):

Replace:
```typescript
    dropdownItems: [
      { label: "Account", href: "/account", type: "link" },
      { label: "", type: "divider" },
      { label: "Sign Out", onClick: vi.fn(), type: "action" },
    ],
```

With:
```typescript
    dropdownItems: [
      { label: "Jane Doe", title: "Jane Doe", href: "/account", type: "link" },
      { label: "", type: "divider" },
      { label: "Sign Out", onClick: vi.fn(), type: "action" },
    ],
```

No test assertion changes needed — the mobile menu renders `nav.user.name` ("Jane Doe") for the user info display and iterates dropdown items for the links. Since the fixture name is already "Jane Doe" and the label is now also "Jane Doe", the existing `screen.getByText("Jane Doe")` assertions still pass.

**Step 2: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/mobile-menu.test.tsx`
Expected: All 7 tests PASS

**Step 3: Commit**

```bash
git add web/src/components/nav/__tests__/mobile-menu.test.tsx
git commit -m "test(web): update mobile menu fixtures for username dropdown"
```

---

### Task 7: Run full test suite and verify

**Files:** None (verification only)

**Step 1: Run all nav-related tests**

Run: `cd web && npx vitest run src/lib/__tests__/user.test.ts src/hooks/__tests__/use-navigation.test.ts src/components/nav/__tests__/user-dropdown.test.tsx src/components/nav/__tests__/mobile-menu.test.tsx src/components/nav/__tests__/navbar.test.tsx`

Expected: All tests PASS

**Step 2: Run full web test suite to catch any regressions**

Run: `cd web && npx vitest run`

Expected: All tests PASS. If any fail, investigate — most likely a test elsewhere references "Account" in the dropdown context.

**Step 3: Final commit if any fixups were needed**

Only if Step 2 revealed issues that required fixes.
