import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
  },
  useInView: () => true,
}))

import { HeroSection } from "../hero-section"

describe("HeroSection", () => {
  it("renders headline", () => {
    render(<HeroSection pick={null} />)
    expect(screen.getByText("Conviction.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()
  })

  it("renders subheadline", () => {
    render(<HeroSection pick={null} />)
    expect(screen.getByText(/deterministic capital allocation/i)).toBeInTheDocument()
  })

  it("renders primary CTA linking to dashboard", () => {
    render(<HeroSection pick={null} />)
    const cta = screen.getByRole("link", { name: /open the dashboard/i })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders secondary CTA linking to methodology", () => {
    render(<HeroSection pick={null} />)
    const cta = screen.getByRole("link", { name: /see the methodology/i })
    expect(cta).toHaveAttribute("href", "/methodology")
  })

  it("renders candidate panel", () => {
    render(<HeroSection pick={null} />)
    // Mock fallback should show AAPL
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })
})
