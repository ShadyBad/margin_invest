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
