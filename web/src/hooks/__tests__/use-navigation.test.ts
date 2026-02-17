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
