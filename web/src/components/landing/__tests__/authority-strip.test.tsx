import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
      scrollTrigger: null,
    })),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { AuthorityStrip } from "../authority-strip"

describe("AuthorityStrip", () => {
  it("renders the section", () => {
    const { container } = render(<AuthorityStrip />)
    const section = container.querySelector("section")
    expect(section).toBeInTheDocument()
  })

  it("renders the three fact texts", () => {
    render(<AuthorityStrip />)
    expect(screen.getByText("SEC EDGAR filings")).toBeInTheDocument()
    expect(screen.getByText("11 GICS sectors")).toBeInTheDocument()
    expect(screen.getByText("Scored daily")).toBeInTheDocument()
  })

  it("renders the horizontal rule", () => {
    const { container } = render(<AuthorityStrip />)
    const rule = container.querySelector(".border-t")
    expect(rule).toBeInTheDocument()
  })

  it("does not render old column labels", () => {
    render(<AuthorityStrip />)
    expect(screen.queryByText("Data Sources")).not.toBeInTheDocument()
    expect(screen.queryByText("Coverage")).not.toBeInTheDocument()
    expect(screen.queryByText("Engine")).not.toBeInTheDocument()
  })

  it("facts start with opacity 0 for GSAP animation", () => {
    render(<AuthorityStrip />)
    const fact = screen.getByText("SEC EDGAR filings")
    expect(fact).toHaveStyle({ opacity: "0" })
  })
})
