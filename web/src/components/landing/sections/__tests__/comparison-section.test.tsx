import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen } from "@testing-library/react"

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    })),
  })
})

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    set: vi.fn(),
    fromTo: vi.fn(),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { ComparisonSection } from "../comparison-section"

describe("ComparisonSection", () => {
  it("renders the section heading", () => {
    render(<ComparisonSection />)
    expect(screen.getByText(/how we compare/i)).toBeInTheDocument()
  })

  it("renders all three competitor columns", () => {
    render(<ComparisonSection />)
    // Desktop table uses uppercased header labels
    expect(screen.getAllByText("MARGIN INVEST").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("SCREENERS").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("BLACK BOX").length).toBeGreaterThanOrEqual(1)
  })

  it("renders comparison rows", () => {
    render(<ComparisonSection />)
    expect(screen.getByText("Scoring")).toBeInTheDocument()
    expect(screen.getByText("Transparency")).toBeInTheDocument()
    expect(screen.getByText("Auditability")).toBeInTheDocument()
  })

  it("uses semantic table markup with caption", () => {
    render(<ComparisonSection />)
    const table = screen.getByRole("table")
    expect(table).toBeInTheDocument()
  })
})
