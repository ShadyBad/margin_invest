import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { useNavigation } from "../use-navigation"

// Mock next-auth/react
const mockSignOut = vi.fn()
let mockSession: Record<string, unknown> | null = null
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: mockSession, status: mockSession ? "authenticated" : "unauthenticated" }),
  signOut: (...args: unknown[]) => mockSignOut(...args),
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

    it("returns public nav links", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.links).toEqual([
        { href: "/login", label: "Dashboard", isActive: false },
        { href: "/methodology", label: "Methodology", isActive: false },
        { href: "/guides", label: "Guides", isActive: false },
        { href: "/#pricing", label: "Pricing", isActive: false },
      ])
    })

    it("returns cta as null", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.cta).toBeNull()
    })

    it("returns user as null", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.user).toBeNull()
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

    it("returns Dashboard and Guides as center links", () => {
      const { result } = renderHook(() => useNavigation())
      const labels = result.current.links.map((l) => l.label)
      expect(labels).toEqual(["Dashboard", "Guides"])
    })

    it("returns cta as null", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.cta).toBeNull()
    })

    it("marks Dashboard active based on pathname", () => {
      mockPathname = "/dashboard"
      const { result } = renderHook(() => useNavigation())
      const dashboard = result.current.links.find((l) => l.href === "/dashboard")
      expect(dashboard!.isActive).toBe(true)
    })

    it("marks Guides active based on pathname", () => {
      mockPathname = "/guides"
      const { result } = renderHook(() => useNavigation())
      const guides = result.current.links.find((l) => l.href === "/guides")
      expect(guides!.isActive).toBe(true)
    })

    it("returns user object with session data", () => {
      const { result } = renderHook(() => useNavigation())
      expect(result.current.user).not.toBeNull()
      expect(result.current.user!.name).toBe("Jane Doe")
      expect(result.current.user!.email).toBe("jane@example.com")
    })

    it("returns dropdown items with display name and sign out", () => {
      const { result } = renderHook(() => useNavigation())
      const items = result.current.user!.dropdownItems
      const labels = items.map((i) => i.label)
      expect(labels).toContain("Jane Doe")
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
