// web/src/components/landing/__tests__/pricing-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
  useInView: () => true,
}))

import { PricingSection } from "../pricing-section"

describe("PricingSection", () => {
  it("renders all three renamed tiers", () => {
    render(<PricingSection />)
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
    expect(screen.getByText("Institutional")).toBeInTheDocument()
  })

  it("renders pricing header line", () => {
    render(<PricingSection />)
    expect(screen.getByText(/system scales with your responsibility/i)).toBeInTheDocument()
  })

  it("renders prices", () => {
    render(<PricingSection />)
    expect(screen.getByText("Free")).toBeInTheDocument()
    expect(screen.getByText("$29")).toBeInTheDocument()
    expect(screen.getByText("$79")).toBeInTheDocument()
  })

  it("renders CTA linking to dashboard", () => {
    render(<PricingSection />)
    const cta = screen.getByRole("link", { name: /start building conviction/i })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders fine print with Analyst tier mention", () => {
    render(<PricingSection />)
    expect(screen.getByText(/no credit card required for analyst tier/i)).toBeInTheDocument()
  })
})
