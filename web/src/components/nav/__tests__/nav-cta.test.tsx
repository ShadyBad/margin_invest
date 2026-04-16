import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { NavCTA } from "../nav-cta"
import type { NavigationCTA } from "@/hooks/use-navigation"

describe("NavCTA", () => {
  const cta: NavigationCTA = {
    primary: { label: "Dashboard", href: "/login" },
  }

  it("renders primary CTA as a styled button", () => {
    render(<NavCTA cta={cta} />)
    const dashboard = screen.getByText("Dashboard")
    expect(dashboard.closest("a")).toHaveAttribute("href", "/login")
    expect(dashboard.closest("a")).toHaveStyle({ borderRadius: "0.375rem" })
  })

  it("renders without secondary CTA", () => {
    render(<NavCTA cta={cta} />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.queryByText("Sign Up")).not.toBeInTheDocument()
  })

  it("renders with secondary CTA when provided", () => {
    const ctaWithSecondary: NavigationCTA = {
      primary: { label: "Dashboard", href: "/login" },
      secondary: { label: "Learn More", href: "/about" },
    }
    render(<NavCTA cta={ctaWithSecondary} />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getByText("Learn More")).toBeInTheDocument()
  })
})
