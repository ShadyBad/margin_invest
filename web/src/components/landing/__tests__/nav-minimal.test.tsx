import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: "dark", setTheme: vi.fn() }),
}))

import { NavMinimal } from "../nav-minimal"

describe("NavMinimal", () => {
  it("renders logo text", () => {
    render(<NavMinimal />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
  })

  it("renders a CTA link", () => {
    render(<NavMinimal />)
    const cta = screen.getByRole("link", { name: /dashboard/i })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders a nav element", () => {
    const { container } = render(<NavMinimal />)
    const nav = container.querySelector("nav")
    expect(nav).toBeInTheDocument()
  })
})
