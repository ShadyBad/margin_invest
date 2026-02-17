# Navigation Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the monolithic `FloatingNav` with a headless `useNavigation()` hook + modular render-slot components, add a `UserDropdown`, and add a global `Footer`.

**Architecture:** A `useNavigation()` hook reads session/pathname and returns structured slot data (`links`, `cta`, `user`). A `<Navbar />` shell renders three zones (logo, center links, right slot) from that data. Sub-components are pure presentational. A new `<Footer />` renders globally in the root layout.

**Tech Stack:** Next.js 15, NextAuth v5 (`useSession`), React 18, Tailwind CSS v4, Vitest + React Testing Library

**Test runner:** `npx vitest run` from `web/` directory

---

### Task 1: Create `useNavigation()` hook

**Files:**
- Create: `web/src/hooks/use-navigation.ts`
- Test: `web/src/hooks/__tests__/use-navigation.test.ts`

**Step 1: Write the failing tests**

Create `web/src/hooks/__tests__/use-navigation.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { useNavigation } from "../use-navigation"

// Mock next-auth/react
const mockSignOut = vi.fn()
let mockSession: any = null
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: mockSession, status: mockSession ? "authenticated" : "unauthenticated" }),
  signOut: (...args: any[]) => mockSignOut(...args),
}))

// Mock next/navigation
let mockPathname = "/"
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}))

describe("useNavigation", () => {
  beforeEach(() => {
    mockSession = null
    mockPathname = "/"
    mockSignOut.mockClear()
  })

  describe("unauthenticated", () => {
    it("returns isAuthenticated false", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.isAuthenticated).toBe(false)
    })

    it("returns public links", () => {
      const { result } = renderHook(() => useNavigation())
      const labels = result.current.links.map((l) => l.label)
      expect(labels).toEqual(["Methodology", "Guides"])
    })

    it("returns login CTA", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.cta).not.toBeNull()
      expect(result.current.cta!.primary.label).toBe("Login")
      expect(result.current.cta!.primary.href).toBe("/login")
    })

    it("returns sign up secondary CTA", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.cta!.secondary).toBeDefined()
      expect(result.current.cta!.secondary!.label).toBe("Sign Up")
      expect(result.current.cta!.secondary!.href).toBe("/register")
    })

    it("returns user as null", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.user).toBeNull()
    })

    it("marks active link based on pathname", () => {
      mockPathname = "/methodology"
      const { result } = renderHook(() => useNavigation())
      const methodology = result.current.links.find((l) => l.href === "/methodology")
      expect(methodology!.isActive).toBe(true)
    })
  })

  describe("authenticated", () => {
    beforeEach(() => {
      mockSession = {
        user: { name: "Jane Doe", email: "jane@example.com", image: "https://oauth.example/avatar.jpg" },
        avatarUrl: null,
        oauthAvatarUrl: "https://oauth.example/avatar.jpg",
      }
    })

    it("returns isAuthenticated true", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.isAuthenticated).toBe(true)
    })

    it("returns app links", () => {
      const { result } = renderHook(() => useNavigation())
      const labels = result.current.links.map((l) => l.label)
      expect(labels).toEqual(["Dashboard", "Mainpage"])
    })

    it("returns cta as null", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.cta).toBeNull()
    })

    it("returns user object with session data", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.user).not.toBeNull()
      expect(result.current.user!.name).toBe("Jane Doe")
      expect(result.current.user!.email).toBe("jane@example.com")
    })

    it("returns dropdown items including sign out", () => {
      const { result } = renderHook(() => useNavigation())
      const items = result.current.user!.dropdownItems
      const labels = items.map((i) => i.label)
      expect(labels).toContain("Account")
      expect(labels).toContain("Settings")
      expect(labels).toContain("Sign Out")
    })

    it("includes a divider before Sign Out", () => {
      const { result } = renderHook(() => useNavigation())
      const items = result.current.user!.dropdownItems
      const signOutIdx = items.findIndex((i) => i.label === "Sign Out")
      expect(items[signOutIdx - 1].type).toBe("divider")
    })

    it("sign out item calls signOut", () => {
      const { result } = renderHook(() => useNavigation())
      const signOutItem = result.current.user!.dropdownItems.find((i) => i.label === "Sign Out")
      signOutItem!.onClick!()
      expect(mockSignOut).toHaveBeenCalled()
    })
  })

  it("always returns logoHref as /", () => {
    const { result } = renderHook(() => useNavigation())
    expect(result.current.logoHref).toBe("/")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: FAIL — module `../use-navigation` not found

**Step 3: Write minimal implementation**

Create `web/src/hooks/use-navigation.ts`:

```ts
"use client"

import { useSession, signOut } from "next-auth/react"
import { usePathname } from "next/navigation"

export interface NavLink {
  href: string
  label: string
  isActive: boolean
}

export interface UserDropdownItem {
  label: string
  href?: string
  onClick?: () => void
  type: "link" | "action" | "divider"
}

export interface NavigationCTA {
  primary: { label: string; href: string }
  secondary?: { label: string; href: string }
}

export interface NavigationUser {
  name: string
  email: string
  avatarUrl?: string | null
  oauthAvatarUrl?: string | null
  dropdownItems: UserDropdownItem[]
}

export interface NavigationState {
  isAuthenticated: boolean
  links: NavLink[]
  cta: NavigationCTA | null
  user: NavigationUser | null
  logoHref: string
}

const PUBLIC_LINKS = [
  { href: "/methodology", label: "Methodology" },
  { href: "/guides", label: "Guides" },
]

const APP_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/", label: "Mainpage" },
]

export function useNavigation(): NavigationState {
  const { data: session } = useSession()
  const pathname = usePathname()
  const isAuthenticated = !!session?.user

  const rawLinks = isAuthenticated ? APP_LINKS : PUBLIC_LINKS
  const links: NavLink[] = rawLinks.map((link) => ({
    ...link,
    isActive: pathname === link.href,
  }))

  const cta: NavigationCTA | null = isAuthenticated
    ? null
    : {
        primary: { label: "Login", href: "/login" },
        secondary: { label: "Sign Up", href: "/register" },
      }

  const user: NavigationUser | null = isAuthenticated
    ? {
        name: session.user.name || session.user.email || "",
        email: session.user.email || "",
        avatarUrl: (session as any).avatarUrl ?? null,
        oauthAvatarUrl: (session as any).oauthAvatarUrl ?? session.user.image ?? null,
        dropdownItems: [
          { label: "Account", href: "/account", type: "link" as const },
          { label: "Settings", href: "/settings", type: "link" as const },
          { label: "", type: "divider" as const },
          { label: "Sign Out", onClick: () => signOut(), type: "action" as const },
        ],
      }
    : null

  return { isAuthenticated, links, cta, user, logoHref: "/" }
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts`
Expected: All 11 tests PASS

**Step 5: Commit**

```bash
git add web/src/hooks/use-navigation.ts web/src/hooks/__tests__/use-navigation.test.ts
git commit -m "feat(web): add useNavigation headless hook for auth-based nav logic"
```

---

### Task 2: Create `NavLogo` component

**Files:**
- Create: `web/src/components/nav/nav-logo.tsx`
- Test: `web/src/components/nav/__tests__/nav-logo.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/nav/__tests__/nav-logo.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { NavLogo } from "../nav-logo"

describe("NavLogo", () => {
  it("renders a link to the provided href", () => {
    render(<NavLogo href="/" />)
    const link = screen.getByLabelText("Margin Invest home")
    expect(link).toHaveAttribute("href", "/")
  })

  it("renders the logo SVG", () => {
    render(<NavLogo href="/" />)
    const link = screen.getByLabelText("Margin Invest home")
    const svg = link.querySelector("svg")
    expect(svg).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/nav/__tests__/nav-logo.test.tsx`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

Create `web/src/components/nav/nav-logo.tsx`:

```tsx
import Link from "next/link"

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

interface NavLogoProps {
  href: string
}

export function NavLogo({ href }: NavLogoProps) {
  return (
    <Link
      href={href}
      className="text-text-primary opacity-80 hover:opacity-100 transition-opacity duration-200"
      aria-label="Margin Invest home"
    >
      <LogoIcon />
    </Link>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/nav/__tests__/nav-logo.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/nav-logo.tsx web/src/components/nav/__tests__/nav-logo.test.tsx
git commit -m "feat(web): add NavLogo component"
```

---

### Task 3: Create `NavLinks` component

**Files:**
- Create: `web/src/components/nav/nav-links.tsx`
- Test: `web/src/components/nav/__tests__/nav-links.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/nav/__tests__/nav-links.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { NavLinks } from "../nav-links"
import type { NavLink } from "@/hooks/use-navigation"

const links: NavLink[] = [
  { href: "/dashboard", label: "Dashboard", isActive: true },
  { href: "/", label: "Mainpage", isActive: false },
]

describe("NavLinks", () => {
  it("renders all links", () => {
    render(<NavLinks links={links} />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Mainpage")).toBeInTheDocument()
  })

  it("applies active styling to active link", () => {
    render(<NavLinks links={links} />)
    expect(screen.getByText("Dashboard").className).toContain("text-text-primary")
    expect(screen.getByText("Dashboard").className).not.toContain("text-text-secondary")
  })

  it("applies inactive styling to non-active link", () => {
    render(<NavLinks links={links} />)
    expect(screen.getByText("Mainpage").className).toContain("text-text-secondary")
  })

  it("renders correct hrefs", () => {
    render(<NavLinks links={links} />)
    expect(screen.getByText("Dashboard").closest("a")).toHaveAttribute("href", "/dashboard")
    expect(screen.getByText("Mainpage").closest("a")).toHaveAttribute("href", "/")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/nav/__tests__/nav-links.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `web/src/components/nav/nav-links.tsx`:

```tsx
import Link from "next/link"
import type { NavLink } from "@/hooks/use-navigation"

interface NavLinksProps {
  links: NavLink[]
}

export function NavLinks({ links }: NavLinksProps) {
  return (
    <div className="hidden md:flex items-center gap-8">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={`text-[14px] font-medium tracking-[-0.01em] transition-colors duration-200 ease-out ${
            link.isActive
              ? "text-text-primary"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          {link.label}
        </Link>
      ))}
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/nav/__tests__/nav-links.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/nav-links.tsx web/src/components/nav/__tests__/nav-links.test.tsx
git commit -m "feat(web): add NavLinks presentational component"
```

---

### Task 4: Create `NavCTA` component

**Files:**
- Create: `web/src/components/nav/nav-cta.tsx`
- Test: `web/src/components/nav/__tests__/nav-cta.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/nav/__tests__/nav-cta.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { NavCTA } from "../nav-cta"
import type { NavigationCTA } from "@/hooks/use-navigation"

describe("NavCTA", () => {
  const cta: NavigationCTA = {
    primary: { label: "Login", href: "/login" },
    secondary: { label: "Sign Up", href: "/register" },
  }

  it("renders primary CTA as a pill button", () => {
    render(<NavCTA cta={cta} />)
    const login = screen.getByText("Login")
    expect(login.closest("a")).toHaveAttribute("href", "/login")
    expect(login.className).toContain("rounded-full")
  })

  it("renders secondary CTA as a text link", () => {
    render(<NavCTA cta={cta} />)
    const signup = screen.getByText("Sign Up")
    expect(signup.closest("a")).toHaveAttribute("href", "/register")
  })

  it("renders without secondary CTA", () => {
    const ctaNoSecondary: NavigationCTA = {
      primary: { label: "Login", href: "/login" },
    }
    render(<NavCTA cta={ctaNoSecondary} />)
    expect(screen.getByText("Login")).toBeInTheDocument()
    expect(screen.queryByText("Sign Up")).not.toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/nav/__tests__/nav-cta.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `web/src/components/nav/nav-cta.tsx`:

```tsx
import Link from "next/link"
import type { NavigationCTA } from "@/hooks/use-navigation"

interface NavCTAProps {
  cta: NavigationCTA
}

export function NavCTA({ cta }: NavCTAProps) {
  return (
    <div className="flex items-center gap-3">
      {cta.secondary && (
        <Link
          href={cta.secondary.href}
          className="text-[13px] text-text-secondary hover:text-text-primary transition-colors duration-200 ease-out"
        >
          {cta.secondary.label}
        </Link>
      )}
      <Link
        href={cta.primary.href}
        className="bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2 hover:bg-bg-subtle transition-colors duration-200 ease-out"
      >
        {cta.primary.label}
      </Link>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/nav/__tests__/nav-cta.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/nav-cta.tsx web/src/components/nav/__tests__/nav-cta.test.tsx
git commit -m "feat(web): add NavCTA component for unauthenticated right slot"
```

---

### Task 5: Create `UserDropdown` component

**Files:**
- Create: `web/src/components/nav/user-dropdown.tsx`
- Test: `web/src/components/nav/__tests__/user-dropdown.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/nav/__tests__/user-dropdown.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { UserDropdown } from "../user-dropdown"
import type { NavigationUser } from "@/hooks/use-navigation"

const mockSignOut = vi.fn()

const user: NavigationUser = {
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
}

describe("UserDropdown", () => {
  beforeEach(() => {
    mockSignOut.mockClear()
  })

  it("renders the avatar button", () => {
    render(<UserDropdown user={user} />)
    expect(screen.getByRole("button", { name: /user menu/i })).toBeInTheDocument()
  })

  it("dropdown is closed by default", () => {
    render(<UserDropdown user={user} />)
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("opens dropdown on avatar click", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByRole("menu")).toBeInTheDocument()
  })

  it("renders dropdown items when open", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByText("Account")).toBeInTheDocument()
    expect(screen.getByText("Settings")).toBeInTheDocument()
    expect(screen.getByText("Sign Out")).toBeInTheDocument()
  })

  it("renders link items as anchor tags", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByText("Account").closest("a")).toHaveAttribute("href", "/account")
  })

  it("calls onClick for action items", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    await u.click(screen.getByText("Sign Out"))
    expect(mockSignOut).toHaveBeenCalled()
  })

  it("renders divider separator", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByRole("separator")).toBeInTheDocument()
  })

  it("closes on second click (toggle)", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    const trigger = screen.getByRole("button", { name: /user menu/i })
    await u.click(trigger)
    expect(screen.getByRole("menu")).toBeInTheDocument()
    await u.click(trigger)
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("closes on Escape key", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    await u.click(screen.getByRole("button", { name: /user menu/i }))
    expect(screen.getByRole("menu")).toBeInTheDocument()
    await u.keyboard("{Escape}")
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("has aria-expanded on trigger button", async () => {
    const u = userEvent.setup()
    render(<UserDropdown user={user} />)
    const trigger = screen.getByRole("button", { name: /user menu/i })
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    await u.click(trigger)
    expect(trigger).toHaveAttribute("aria-expanded", "true")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/user-dropdown.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `web/src/components/nav/user-dropdown.tsx`:

```tsx
"use client"

import { useState, useRef, useEffect } from "react"
import Link from "next/link"
import { Avatar } from "@/components/ui/avatar"
import type { NavigationUser } from "@/hooks/use-navigation"

interface UserDropdownProps {
  user: NavigationUser
}

export function UserDropdown({ user }: UserDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }

    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    document.addEventListener("keydown", handleEscape)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("keydown", handleEscape)
    }
  }, [isOpen])

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label="User menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="flex items-center"
      >
        <Avatar
          name={user.name}
          avatarUrl={user.avatarUrl}
          oauthAvatarUrl={user.oauthAvatarUrl}
          size="sm"
        />
      </button>

      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-2 w-48 bg-[#111113] border border-border-subtle rounded-xl py-1 shadow-[0_4px_24px_rgba(0,0,0,0.4)] animate-in fade-in zoom-in-95 duration-150 ease-out"
        >
          {user.dropdownItems.map((item, i) => {
            if (item.type === "divider") {
              return (
                <div
                  key={`divider-${i}`}
                  role="separator"
                  className="my-1 border-t border-border-subtle"
                />
              )
            }

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

            return (
              <button
                key={item.label}
                role="menuitem"
                className={`block w-full text-left px-4 py-2 text-[13px] transition-colors duration-150 ${
                  item.label === "Sign Out"
                    ? "text-red-400 hover:text-red-300 hover:bg-bg-elevated"
                    : "text-text-secondary hover:text-text-primary hover:bg-bg-elevated"
                }`}
                onClick={() => {
                  item.onClick?.()
                  setIsOpen(false)
                }}
              >
                {item.label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/user-dropdown.test.tsx`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/user-dropdown.tsx web/src/components/nav/__tests__/user-dropdown.test.tsx
git commit -m "feat(web): add UserDropdown with avatar trigger and accessible menu"
```

---

### Task 6: Create `MobileMenu` component

**Files:**
- Create: `web/src/components/nav/mobile-menu.tsx`
- Test: `web/src/components/nav/__tests__/mobile-menu.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/nav/__tests__/mobile-menu.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MobileMenu } from "../mobile-menu"
import type { NavigationState } from "@/hooks/use-navigation"

const publicNav: NavigationState = {
  isAuthenticated: false,
  links: [
    { href: "/methodology", label: "Methodology", isActive: false },
    { href: "/guides", label: "Guides", isActive: false },
  ],
  cta: {
    primary: { label: "Login", href: "/login" },
    secondary: { label: "Sign Up", href: "/register" },
  },
  user: null,
  logoHref: "/",
}

const appNav: NavigationState = {
  isAuthenticated: true,
  links: [
    { href: "/dashboard", label: "Dashboard", isActive: true },
    { href: "/", label: "Mainpage", isActive: false },
  ],
  cta: null,
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

describe("MobileMenu", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <MobileMenu nav={publicNav} isOpen={false} onClose={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })

  it("renders links when open", () => {
    render(<MobileMenu nav={publicNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Methodology")).toBeInTheDocument()
    expect(screen.getByText("Guides")).toBeInTheDocument()
  })

  it("renders Login CTA for unauthenticated", () => {
    render(<MobileMenu nav={publicNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Login")).toBeInTheDocument()
  })

  it("renders user info for authenticated", () => {
    render(<MobileMenu nav={appNav} isOpen={true} onClose={vi.fn()} />)
    expect(screen.getByText("Jane Doe")).toBeInTheDocument()
  })

  it("calls onClose when a link is clicked", async () => {
    const onClose = vi.fn()
    const u = userEvent.setup()
    render(<MobileMenu nav={publicNav} isOpen={true} onClose={onClose} />)
    await u.click(screen.getByText("Methodology"))
    expect(onClose).toHaveBeenCalled()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/mobile-menu.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `web/src/components/nav/mobile-menu.tsx`:

```tsx
import Link from "next/link"
import { Avatar } from "@/components/ui/avatar"
import type { NavigationState } from "@/hooks/use-navigation"

interface MobileMenuProps {
  nav: NavigationState
  isOpen: boolean
  onClose: () => void
}

export function MobileMenu({ nav, isOpen, onClose }: MobileMenuProps) {
  if (!isOpen) return null

  return (
    <div className="md:hidden mt-2 bg-[#111113] dark:bg-[#111113] border border-border-subtle rounded-2xl px-6 py-4">
      <div className="flex flex-col gap-1">
        {nav.links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`text-[14px] font-medium py-3 transition-colors duration-200 ease-out ${
              link.isActive
                ? "text-text-primary"
                : "text-text-secondary hover:text-text-primary"
            }`}
            onClick={onClose}
          >
            {link.label}
          </Link>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-border-subtle">
        {nav.user ? (
          <div className="flex flex-col gap-2">
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
        ) : nav.cta ? (
          <div className="flex flex-col gap-2">
            <Link
              href={nav.cta.primary.href}
              className="block text-center bg-bg-elevated text-text-primary text-[13px] font-semibold rounded-full px-5 py-2.5 hover:bg-bg-subtle transition-colors duration-200 ease-out"
              onClick={onClose}
            >
              {nav.cta.primary.label}
            </Link>
            {nav.cta.secondary && (
              <Link
                href={nav.cta.secondary.href}
                className="block text-center text-[13px] text-text-secondary hover:text-text-primary transition-colors duration-200 ease-out py-1"
                onClick={onClose}
              >
                {nav.cta.secondary.label}
              </Link>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/mobile-menu.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/mobile-menu.tsx web/src/components/nav/__tests__/mobile-menu.test.tsx
git commit -m "feat(web): add MobileMenu component for responsive nav"
```

---

### Task 7: Create `Navbar` shell orchestrator

**Files:**
- Create: `web/src/components/nav/navbar.tsx`
- Test: `web/src/components/nav/__tests__/navbar.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/nav/__tests__/navbar.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Navbar } from "../navbar"

// Mock useNavigation
let mockIsAuthenticated = false
const mockSignOut = vi.fn()

vi.mock("@/hooks/use-navigation", () => ({
  useNavigation: () => {
    if (mockIsAuthenticated) {
      return {
        isAuthenticated: true,
        links: [
          { href: "/dashboard", label: "Dashboard", isActive: true },
          { href: "/", label: "Mainpage", isActive: false },
        ],
        cta: null,
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
    }
    return {
      isAuthenticated: false,
      links: [
        { href: "/methodology", label: "Methodology", isActive: false },
        { href: "/guides", label: "Guides", isActive: false },
      ],
      cta: {
        primary: { label: "Login", href: "/login" },
        secondary: { label: "Sign Up", href: "/register" },
      },
      user: null,
      logoHref: "/",
    }
  },
}))

describe("Navbar", () => {
  beforeEach(() => {
    mockIsAuthenticated = false
    mockSignOut.mockClear()
  })

  it("renders nav element with aria-label", () => {
    render(<Navbar />)
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument()
  })

  it("renders logo", () => {
    render(<Navbar />)
    expect(screen.getByLabelText("Margin Invest home")).toBeInTheDocument()
  })

  describe("unauthenticated", () => {
    it("renders public links", () => {
      render(<Navbar />)
      expect(screen.getByText("Methodology")).toBeInTheDocument()
      expect(screen.getByText("Guides")).toBeInTheDocument()
    })

    it("renders Login CTA", () => {
      render(<Navbar />)
      expect(screen.getByText("Login")).toBeInTheDocument()
    })

    it("renders Sign Up link", () => {
      render(<Navbar />)
      expect(screen.getByText("Sign Up")).toBeInTheDocument()
    })

    it("does not render user dropdown", () => {
      render(<Navbar />)
      expect(screen.queryByRole("button", { name: /user menu/i })).not.toBeInTheDocument()
    })
  })

  describe("authenticated", () => {
    beforeEach(() => {
      mockIsAuthenticated = true
    })

    it("renders app links", () => {
      render(<Navbar />)
      expect(screen.getByText("Dashboard")).toBeInTheDocument()
      expect(screen.getByText("Mainpage")).toBeInTheDocument()
    })

    it("renders user avatar button", () => {
      render(<Navbar />)
      expect(screen.getByRole("button", { name: /user menu/i })).toBeInTheDocument()
    })

    it("does not render Login CTA", () => {
      render(<Navbar />)
      expect(screen.queryByText("Login")).not.toBeInTheDocument()
    })
  })

  describe("mobile", () => {
    it("has hamburger toggle button", () => {
      render(<Navbar />)
      expect(screen.getByLabelText("Toggle menu")).toBeInTheDocument()
    })

    it("toggles mobile menu open and closed", async () => {
      const u = userEvent.setup()
      render(<Navbar />)
      const toggle = screen.getByLabelText("Toggle menu")

      // Menu closed — only desktop links
      expect(screen.getAllByText("Methodology")).toHaveLength(1)

      await u.click(toggle)
      // Menu open — desktop + mobile links
      expect(screen.getAllByText("Methodology")).toHaveLength(2)

      await u.click(toggle)
      // Closed again
      expect(screen.getAllByText("Methodology")).toHaveLength(1)
    })
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/nav/__tests__/navbar.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `web/src/components/nav/navbar.tsx`:

```tsx
"use client"

import { useState } from "react"
import { useNavigation } from "@/hooks/use-navigation"
import { NavLogo } from "./nav-logo"
import { NavLinks } from "./nav-links"
import { NavCTA } from "./nav-cta"
import { UserDropdown } from "./user-dropdown"
import { MobileMenu } from "./mobile-menu"
import { UsagePill } from "./usage-pill"

export function Navbar() {
  const nav = useNavigation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <nav
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-32px)] max-w-[900px]"
      aria-label="Main navigation"
    >
      <div className="flex items-center justify-between bg-[#111113] dark:bg-[#111113] light:bg-[#FAFAF9] border border-border-subtle rounded-2xl px-6 py-3 shadow-[0_2px_16px_rgba(0,0,0,0.3)]">
        <NavLogo href={nav.logoHref} />

        <NavLinks links={nav.links} />

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

      <MobileMenu
        nav={nav}
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />
    </nav>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/nav/__tests__/navbar.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/nav/navbar.tsx web/src/components/nav/__tests__/navbar.test.tsx
git commit -m "feat(web): add Navbar shell orchestrator with useNavigation hook"
```

---

### Task 8: Create `Footer` component

**Files:**
- Create: `web/src/components/layout/footer.tsx`
- Test: `web/src/components/layout/__tests__/footer.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/layout/__tests__/footer.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Footer } from "../footer"

describe("Footer", () => {
  it("renders Support link", () => {
    render(<Footer />)
    expect(screen.getByText("Support").closest("a")).toHaveAttribute("href", "/support")
  })

  it("renders Methodology link", () => {
    render(<Footer />)
    expect(screen.getByText("Methodology").closest("a")).toHaveAttribute("href", "/methodology")
  })

  it("renders Legal link", () => {
    render(<Footer />)
    expect(screen.getByText("Legal").closest("a")).toHaveAttribute("href", "/legal")
  })

  it("renders copyright text", () => {
    render(<Footer />)
    expect(screen.getByText(/Margin/)).toBeInTheDocument()
  })

  it("renders a footer element", () => {
    render(<Footer />)
    expect(screen.getByRole("contentinfo")).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/layout/__tests__/footer.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `web/src/components/layout/footer.tsx`:

```tsx
import Link from "next/link"

const footerLinks = [
  { href: "/support", label: "Support" },
  { href: "/methodology", label: "Methodology" },
  { href: "/legal", label: "Legal" },
]

export function Footer() {
  return (
    <footer className="border-t border-border-subtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-wrap items-center justify-center gap-6 text-[12px] text-text-tertiary">
        {footerLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="hover:text-text-secondary transition-colors duration-200"
          >
            {link.label}
          </Link>
        ))}
        <span>&copy; {new Date().getFullYear()} Margin</span>
      </div>
    </footer>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/layout/__tests__/footer.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/layout/footer.tsx web/src/components/layout/__tests__/footer.test.tsx
git commit -m "feat(web): add global Footer component"
```

---

### Task 9: Wire `Navbar` and `Footer` into app, delete `FloatingNav`

This is the integration task. Replace all `FloatingNav` usage with `Navbar`, add `Footer` to root layout, delete old file + old tests.

**Files:**
- Modify: `web/src/app/layout.tsx`
- Modify: `web/src/components/layout/app-shell.tsx`
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/methodology/page.tsx`
- Delete: `web/src/components/nav/floating-nav.tsx`
- Delete: `web/src/components/nav/__tests__/floating-nav.test.tsx`
- Update: `web/src/components/layout/__tests__/app-shell.test.tsx`

**Step 1: Update `app-shell.tsx`**

Replace contents of `web/src/components/layout/app-shell.tsx`:

```tsx
import { Navbar } from "@/components/nav/navbar"

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg-primary">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-8">
        {children}
      </main>
    </div>
  )
}
```

**Step 2: Update `app/page.tsx`**

In `web/src/app/page.tsx`, replace:
- `import { FloatingNav } from "@/components/nav/floating-nav"` → `import { Navbar } from "@/components/nav/navbar"`
- `<FloatingNav variant="public" />` → `<Navbar />`

**Step 3: Update `app/methodology/page.tsx`**

In `web/src/app/methodology/page.tsx`, replace:
- `import { FloatingNav } from "@/components/nav/floating-nav"` → `import { Navbar } from "@/components/nav/navbar"`
- `<FloatingNav variant="public" />` → `<Navbar />`

**Step 4: Add Footer to root layout**

In `web/src/app/layout.tsx`, add import and render `<Footer />` after `{children}`:

```tsx
import { Footer } from "@/components/layout/footer"

// Inside the body, after SessionProvider:
<SessionProvider>
  {children}
  <Footer />
</SessionProvider>
```

**Step 5: Delete old files**

```bash
rm web/src/components/nav/floating-nav.tsx
rm web/src/components/nav/__tests__/floating-nav.test.tsx
```

**Step 6: Update `app-shell.test.tsx`**

Replace `web/src/components/layout/__tests__/app-shell.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AppShell } from "../app-shell"

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}))

describe("AppShell", () => {
  it("renders children", () => {
    render(<AppShell><div data-testid="child">Content</div></AppShell>)
    expect(screen.getByTestId("child")).toBeInTheDocument()
  })

  it("includes navigation", () => {
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

**Step 7: Run all nav + layout tests**

Run: `cd web && npx vitest run src/components/nav/ src/components/layout/ src/hooks/`
Expected: All tests PASS. No references to `FloatingNav` remain.

**Step 8: Verify no broken imports across the codebase**

Run: `cd web && npx vitest run`
Expected: Full test suite PASS (some tests in `landing/__tests__/page-assembly.test.tsx` may need FloatingNav mock updates — see Step 9)

**Step 9: Fix any remaining FloatingNav references in other test files**

Check `web/src/components/landing/__tests__/page-assembly.test.tsx` — it mocks `next-auth/react` for FloatingNav. Since `page.tsx` now uses `Navbar`, the mocks should still work (same underlying `useSession` call). If any test references `FloatingNav` by name in comments, update them.

Run: `cd web && npx vitest run`
Expected: Full suite PASS

**Step 10: Commit**

```bash
git add -A
git commit -m "refactor(web): replace FloatingNav with Navbar + useNavigation hook

- Wire Navbar into AppShell, landing page, methodology page
- Add Footer to root layout
- Delete monolithic FloatingNav component
- Update all tests"
```

---

### Summary of all new files

| File | Purpose |
|------|---------|
| `web/src/hooks/use-navigation.ts` | Headless nav controller |
| `web/src/hooks/__tests__/use-navigation.test.ts` | Hook tests |
| `web/src/components/nav/navbar.tsx` | Shell orchestrator |
| `web/src/components/nav/nav-logo.tsx` | Logo slot |
| `web/src/components/nav/nav-links.tsx` | Center links slot |
| `web/src/components/nav/nav-cta.tsx` | Unauthenticated right slot |
| `web/src/components/nav/user-dropdown.tsx` | Authenticated right slot |
| `web/src/components/nav/mobile-menu.tsx` | Responsive mobile menu |
| `web/src/components/layout/footer.tsx` | Global footer |
| `web/src/components/nav/__tests__/navbar.test.tsx` | Shell tests |
| `web/src/components/nav/__tests__/nav-logo.test.tsx` | Logo tests |
| `web/src/components/nav/__tests__/nav-links.test.tsx` | Links tests |
| `web/src/components/nav/__tests__/nav-cta.test.tsx` | CTA tests |
| `web/src/components/nav/__tests__/user-dropdown.test.tsx` | Dropdown tests |
| `web/src/components/nav/__tests__/mobile-menu.test.tsx` | Mobile tests |
| `web/src/components/layout/__tests__/footer.test.tsx` | Footer tests |

### Deleted files

| File | Reason |
|------|--------|
| `web/src/components/nav/floating-nav.tsx` | Replaced by modular components |
| `web/src/components/nav/__tests__/floating-nav.test.tsx` | Replaced by per-component tests |
