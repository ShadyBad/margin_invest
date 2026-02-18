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
    }
    return {
      isAuthenticated: false,
      links: [],
      cta: { primary: { label: "Dashboard", href: "/login" } },
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
    it("renders Dashboard button linking to /login", () => {
      render(<Navbar />)
      const dashboardLink = screen.getByText("Dashboard")
      expect(dashboardLink).toBeInTheDocument()
      expect(dashboardLink.closest("a")).toHaveAttribute("href", "/login")
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

    it("renders Guides center link", () => {
      render(<Navbar />)
      expect(screen.getByText("Guides")).toBeInTheDocument()
    })

    it("renders Dashboard button linking to /dashboard", () => {
      render(<Navbar />)
      const dashboardLinks = screen.getAllByText("Dashboard")
      const ctaLink = dashboardLinks.find(
        (el) => el.closest("a")?.getAttribute("href") === "/dashboard"
      )
      expect(ctaLink).toBeDefined()
    })

    it("renders user avatar button", () => {
      render(<Navbar />)
      expect(screen.getByRole("button", { name: /user menu/i })).toBeInTheDocument()
    })

    it("does not render Login or Sign Up", () => {
      render(<Navbar />)
      expect(screen.queryByText("Login")).not.toBeInTheDocument()
      expect(screen.queryByText("Sign Up")).not.toBeInTheDocument()
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

      // Menu closed — only desktop NavCTA
      expect(screen.getAllByText("Dashboard")).toHaveLength(1)

      await u.click(toggle)
      // Menu open — desktop NavCTA + mobile menu
      expect(screen.getAllByText("Dashboard")).toHaveLength(2)

      await u.click(toggle)
      // Closed again
      expect(screen.getAllByText("Dashboard")).toHaveLength(1)
    })
  })
})
