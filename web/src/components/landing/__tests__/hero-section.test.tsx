import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { HeroSection } from "../hero-section"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
}))

describe("HeroSection", () => {
  it("renders the headline", () => {
    render(<HeroSection />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
  })

  it("renders the subhead", () => {
    render(<HeroSection />)
    expect(screen.getByText(/deterministic scoring engine/i)).toBeInTheDocument()
  })

  it("renders primary CTA linking to dashboard", () => {
    render(<HeroSection />)
    const cta = screen.getByRole("link", { name: "Explore the Engine" })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders secondary CTA", () => {
    render(<HeroSection />)
    expect(screen.getByText("View methodology")).toBeInTheDocument()
  })

  it("contains the grid overlay", () => {
    const { container } = render(<HeroSection />)
    expect(container.querySelector("svg")).toBeInTheDocument()
  })
})
