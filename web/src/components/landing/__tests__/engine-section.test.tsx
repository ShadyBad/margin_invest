import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn() },
  gsap: { registerPlugin: vi.fn(), to: vi.fn() },
}))

vi.mock("gsap/ScrollTrigger", () => ({
  default: {},
  ScrollTrigger: {},
}))

import { EngineSection } from "../engine-section"

describe("EngineSection", () => {
  it("renders pipeline diagram with all stages", () => {
    render(<EngineSection />)
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()
  })

  it("renders all 10 engine cards", () => {
    render(<EngineSection />)
    // Cards appear in both desktop and mobile layouts, so use getAllByText
    expect(screen.getAllByText("Raw Market Signal").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Elimination Filters").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Multi-Factor Ranking").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Portfolio Correlation Mapping").length).toBeGreaterThanOrEqual(1)
  })

  it("renders two card rows on desktop", () => {
    const { container } = render(<EngineSection />)
    const rows = container.querySelectorAll("[data-card-row]")
    expect(rows.length).toBeGreaterThanOrEqual(2)
  })
})
