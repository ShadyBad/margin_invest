import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { Sidebar } from "../sidebar"

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}))

describe("Sidebar", () => {
  it("renders navigation groups when expanded", () => {
    render(<Sidebar expanded={true} onToggle={vi.fn()} />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Watchlist")).toBeInTheDocument()
    expect(screen.getByText("Search")).toBeInTheDocument()
    expect(screen.getByText("Smart Money")).toBeInTheDocument()
    expect(screen.getByText("Backtesting")).toBeInTheDocument()
    expect(screen.getByText("Methodology")).toBeInTheDocument()
    expect(screen.getByText("Guides")).toBeInTheDocument()
    expect(screen.getByText("Status")).toBeInTheDocument()
  })

  it("renders group titles when expanded", () => {
    render(<Sidebar expanded={true} onToggle={vi.fn()} />)
    expect(screen.getByText("CORE")).toBeInTheDocument()
    expect(screen.getByText("TOOLS")).toBeInTheDocument()
    expect(screen.getByText("SYSTEM")).toBeInTheDocument()
  })

  it("hides text labels when collapsed", () => {
    render(<Sidebar expanded={false} onToggle={vi.fn()} />)
    expect(screen.queryByText("Dashboard")).not.toBeInTheDocument()
    expect(screen.queryByText("Watchlist")).not.toBeInTheDocument()
    expect(screen.queryByText("Search")).not.toBeInTheDocument()
    expect(screen.queryByText("CORE")).not.toBeInTheDocument()
    expect(screen.queryByText("TOOLS")).not.toBeInTheDocument()
    expect(screen.queryByText("SYSTEM")).not.toBeInTheDocument()
  })

  it("renders correct navigation links", () => {
    render(<Sidebar expanded={true} onToggle={vi.fn()} />)
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard")
    expect(screen.getByRole("link", { name: "Watchlist" })).toHaveAttribute("href", "/watchlist")
    expect(screen.getByRole("link", { name: "Search" })).toHaveAttribute("href", "/search")
    expect(screen.getByRole("link", { name: "Smart Money" })).toHaveAttribute("href", "/smart-money")
    expect(screen.getByRole("link", { name: "Backtesting" })).toHaveAttribute("href", "/backtesting")
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute("href", "/methodology")
    expect(screen.getByRole("link", { name: "Guides" })).toHaveAttribute("href", "/guides")
    expect(screen.getByRole("link", { name: "Status" })).toHaveAttribute("href", "/status")
  })

  it("shows engine version", () => {
    render(<Sidebar expanded={true} onToggle={vi.fn()} />)
    expect(screen.getByText("v4.2")).toBeInTheDocument()
  })

  it("shows plan tier badge when expanded", () => {
    render(<Sidebar expanded={true} onToggle={vi.fn()} />)
    expect(screen.getByText("Analyst")).toBeInTheDocument()
  })

  it("renders sidebar navigation landmark", () => {
    render(<Sidebar expanded={true} onToggle={vi.fn()} />)
    expect(screen.getByRole("navigation", { name: "Sidebar navigation" })).toBeInTheDocument()
  })

  it("sets expanded width to 240px", () => {
    render(<Sidebar expanded={true} onToggle={vi.fn()} />)
    const sidebar = screen.getByTestId("sidebar")
    expect(sidebar.style.width).toBe("240px")
  })

  it("sets collapsed width to 64px", () => {
    render(<Sidebar expanded={false} onToggle={vi.fn()} />)
    const sidebar = screen.getByTestId("sidebar")
    expect(sidebar.style.width).toBe("64px")
  })

  it("provides tooltips when collapsed", () => {
    render(<Sidebar expanded={false} onToggle={vi.fn()} />)
    const links = screen.getAllByRole("link")
    // When collapsed, each link should have a title attribute
    links.forEach((link) => {
      expect(link).toHaveAttribute("title")
    })
  })

  it("renders collapse toggle button", () => {
    render(<Sidebar expanded={true} onToggle={vi.fn()} />)
    expect(screen.getByRole("button", { name: "Collapse sidebar" })).toBeInTheDocument()
  })

  it("renders expand toggle button when collapsed", () => {
    render(<Sidebar expanded={false} onToggle={vi.fn()} />)
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument()
  })
})
