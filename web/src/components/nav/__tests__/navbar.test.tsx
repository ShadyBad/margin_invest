import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Navbar } from "../navbar"

// Mock useNavigation
let mockIsAuthenticated = false
const mockSignOut = vi.fn()

vi.mock("next-themes", () => ({
  useTheme: () => ({
    resolvedTheme: "dark",
    setTheme: vi.fn(),
  }),
}))

vi.mock("@/hooks/use-navigation", () => ({
  useNavigation: () => {
    if (mockIsAuthenticated) {
      return {
        isAuthenticated: true,
        links: [
          { href: "/dashboard", label: "Dashboard", isActive: false },
          { href: "/guides", label: "Guides", isActive: false },
        ],
        cta: null,
        user: {
          name: "Jane Doe",
          email: "jane@example.com",
          avatarUrl: null,
          oauthAvatarUrl: null,
          dropdownItems: [
            { label: "Account", href: "/account", type: "link" },
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
        { href: "/login", label: "Dashboard", isActive: false },
        { href: "/guides", label: "Guides", isActive: false },
      ],
      cta: null,
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
    it("renders Dashboard nav link pointing to /login", () => {
      render(<Navbar />)
      const dashboardLink = screen.getByText("Dashboard")
      expect(dashboardLink).toBeInTheDocument()
      expect(dashboardLink.closest("a")).toHaveAttribute("href", "/login")
    })

    it("renders Guides nav link", () => {
      render(<Navbar />)
      expect(screen.getByText("Guides")).toBeInTheDocument()
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

    it("renders Dashboard and Guides center links", () => {
      render(<Navbar />)
      expect(screen.getByText("Dashboard")).toBeInTheDocument()
      expect(screen.getByText("Guides")).toBeInTheDocument()
    })

    it("does not render Dashboard CTA button", () => {
      render(<Navbar />)
      // Dashboard appears as a center link, not as a CTA pill button
      const dashboard = screen.getByText("Dashboard")
      expect(dashboard.closest("a")).toHaveAttribute("href", "/dashboard")
      expect(dashboard.className).not.toContain("rounded-full")
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

      // Menu closed — only desktop nav link "Dashboard"
      expect(screen.getAllByText("Dashboard")).toHaveLength(1)

      await u.click(toggle)
      // Menu open — desktop nav link + mobile nav link
      expect(screen.getAllByText("Dashboard")).toHaveLength(2)

      await u.click(toggle)
      // Closed again
      expect(screen.getAllByText("Dashboard")).toHaveLength(1)
    })
  })

  it("renders theme toggle button", () => {
    render(<Navbar />)
    expect(screen.getByRole("button", { name: /switch to (light|dark) mode/i })).toBeInTheDocument()
  })
})
