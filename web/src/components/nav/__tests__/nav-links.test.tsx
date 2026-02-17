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
