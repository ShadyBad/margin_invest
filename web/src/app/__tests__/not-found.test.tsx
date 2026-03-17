import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import NotFound from "../not-found"

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

vi.mock("@/components/landing/hero-search", () => ({
  HeroSearch: () => <div data-testid="hero-search">HeroSearch</div>,
}))

describe("NotFound", () => {
  it("renders page not found heading", () => {
    render(<NotFound />)
    expect(screen.getByText("Page not found")).toBeInTheDocument()
  })

  it("renders helpful body text", () => {
    render(<NotFound />)
    expect(screen.getByText(/Try searching for a ticker/)).toBeInTheDocument()
  })

  it("renders HeroSearch component", () => {
    render(<NotFound />)
    expect(screen.getByTestId("hero-search")).toBeInTheDocument()
  })

  it("renders link back to home", () => {
    render(<NotFound />)
    const link = screen.getByRole("link", { name: /back to home/i })
    expect(link).toHaveAttribute("href", "/")
  })
})
