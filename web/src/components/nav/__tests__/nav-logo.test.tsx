import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { NavLogo } from "../nav-logo"

describe("NavLogo", () => {
  it("renders a link to the provided href", () => {
    render(<NavLogo href="/" />)
    const link = screen.getByLabelText("Margin Invest home")
    expect(link).toHaveAttribute("href", "/")
  })

  it("renders the logo SVG", () => {
    render(<NavLogo href="/" />)
    const link = screen.getByLabelText("Margin Invest home")
    const svg = link.querySelector("svg")
    expect(svg).toBeInTheDocument()
  })
})
