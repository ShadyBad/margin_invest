import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { FloatingNav } from "../floating-nav"

// Mock next-auth/react
const mockSignOut = vi.fn()
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: (...args: any[]) => mockSignOut(...args),
}))

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}))

describe("FloatingNav", () => {
  describe("public variant", () => {
    it("renders public links", () => {
      render(<FloatingNav variant="public" />)
      expect(screen.getByText("Methodology")).toBeInTheDocument()
      expect(screen.getByText("Guides")).toBeInTheDocument()
      expect(screen.getByText("Support")).toBeInTheDocument()
    })

    it("does not render app links", () => {
      render(<FloatingNav variant="public" />)
      expect(screen.queryByText("Backtesting")).not.toBeInTheDocument()
      expect(screen.queryByText("Settings")).not.toBeInTheDocument()
    })

    it("renders Dashboard CTA button", () => {
      render(<FloatingNav variant="public" />)
      const ctas = screen.getAllByText("Dashboard")
      expect(ctas.length).toBeGreaterThanOrEqual(1)
    })

    it("renders logo link to home", () => {
      render(<FloatingNav variant="public" />)
      const logo = screen.getByLabelText("Margin Invest home")
      expect(logo).toHaveAttribute("href", "/")
    })
  })

  describe("app variant", () => {
    it("renders app links", () => {
      render(<FloatingNav variant="app" />)
      expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText("Backtesting")).toBeInTheDocument()
      expect(screen.getByText("Settings")).toBeInTheDocument()
    })

    it("does not render public links", () => {
      render(<FloatingNav variant="app" />)
      expect(screen.queryByText("Methodology")).not.toBeInTheDocument()
      expect(screen.queryByText("Guides")).not.toBeInTheDocument()
      expect(screen.queryByText("Support")).not.toBeInTheDocument()
    })

    it("highlights active link", () => {
      render(<FloatingNav variant="app" />)
      const dashboardLinks = screen.getAllByText("Dashboard")
      // Desktop link should be active (text-text-primary)
      expect(dashboardLinks[0].className).toContain("text-text-primary")
    })

    it("shows Sign In when not authenticated", () => {
      render(<FloatingNav variant="app" />)
      expect(screen.getAllByText("Sign In").length).toBeGreaterThanOrEqual(1)
    })
  })

  describe("mobile menu", () => {
    it("toggles mobile menu", async () => {
      const user = userEvent.setup()
      render(<FloatingNav variant="app" />)
      const menuButton = screen.getByLabelText("Toggle menu")

      // Only desktop links visible initially
      expect(screen.getAllByText("Dashboard")).toHaveLength(1)

      // Open mobile menu
      await user.click(menuButton)

      // Desktop + mobile links now visible
      expect(screen.getAllByText("Dashboard")).toHaveLength(2)
    })

    it("closes mobile menu when link is clicked", async () => {
      const user = userEvent.setup()
      render(<FloatingNav variant="app" />)

      // Open menu
      await user.click(screen.getByLabelText("Toggle menu"))
      expect(screen.getAllByText("Backtesting")).toHaveLength(2)

      // Click mobile link
      const mobileLinks = screen.getAllByText("Backtesting")
      await user.click(mobileLinks[1])

      // Menu closed
      expect(screen.getAllByText("Backtesting")).toHaveLength(1)
    })

    it("has aria-expanded attribute", async () => {
      const user = userEvent.setup()
      render(<FloatingNav variant="app" />)
      const menuButton = screen.getByLabelText("Toggle menu")

      expect(menuButton).toHaveAttribute("aria-expanded", "false")
      await user.click(menuButton)
      expect(menuButton).toHaveAttribute("aria-expanded", "true")
    })
  })

  it("renders a nav element with aria-label", () => {
    const { container } = render(<FloatingNav variant="public" />)
    const nav = container.querySelector("nav")
    expect(nav).toBeInTheDocument()
    expect(nav).toHaveAttribute("aria-label", "Main navigation")
  })
})
