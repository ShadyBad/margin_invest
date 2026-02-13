import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Nav } from "../nav"

// Mock next-auth/react
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}))

describe("Nav", () => {
  it("renders logo", () => {
    render(<Nav />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
  })

  it("renders navigation links", () => {
    render(<Nav />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Backtesting")).toBeInTheDocument()
    expect(screen.getByText("Settings")).toBeInTheDocument()
  })

  it("shows Sign In link when not authenticated", () => {
    render(<Nav />)
    // Desktop Sign In + Mobile Sign In (mobile menu not open yet, but link rendered conditionally)
    // Only desktop is rendered since mobile menu is closed
    const signInLinks = screen.getAllByText("Sign In")
    expect(signInLinks.length).toBeGreaterThanOrEqual(1)
  })

  it("highlights active link", () => {
    render(<Nav />)
    const dashboardLinks = screen.getAllByText("Dashboard")
    // The first Dashboard link (desktop) should have gold text for active route
    expect(dashboardLinks[0].className).toContain("text-gold")
  })

  it("toggles mobile menu", async () => {
    const user = userEvent.setup()
    render(<Nav />)
    const menuButton = screen.getByLabelText("Toggle menu")

    // Mobile menu should not show links initially (menu is closed)
    // There should be exactly one set of nav links (desktop only)
    expect(screen.getAllByText("Dashboard")).toHaveLength(1)

    // Click hamburger to open mobile menu
    await user.click(menuButton)

    // Now there should be two sets of nav links (desktop + mobile)
    expect(screen.getAllByText("Dashboard")).toHaveLength(2)
    expect(screen.getAllByText("Backtesting")).toHaveLength(2)
    expect(screen.getAllByText("Settings")).toHaveLength(2)
  })

  it("closes mobile menu when a link is clicked", async () => {
    const user = userEvent.setup()
    render(<Nav />)

    // Open menu
    await user.click(screen.getByLabelText("Toggle menu"))
    expect(screen.getAllByText("Dashboard")).toHaveLength(2)

    // Click a mobile nav link (the second one is the mobile version)
    const mobileLinks = screen.getAllByText("Settings")
    await user.click(mobileLinks[1])

    // Mobile menu should close, leaving only desktop links
    expect(screen.getAllByText("Dashboard")).toHaveLength(1)
  })
})
