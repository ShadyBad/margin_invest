import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  useInView: () => true,
}))

import { HeroCandidatePanel } from "../hero-candidate-panel"

const mockPick = {
  ticker: "AAPL",
  name: "Apple Inc.",
  actual_price: 173.22,
  buy_price: 214.9,
  margin_of_safety: 0.194,
  composite_percentile: 83,
  quality_percentile: 85,
  value_percentile: 62,
  momentum_percentile: 71,
  scored_at: "2026-02-17T04:02:00Z",
  sector: "Technology",
}

describe("HeroCandidatePanel", () => {
  it("renders ticker and price", () => {
    render(<HeroCandidatePanel pick={mockPick} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText(/173\.22/)).toBeInTheDocument()
  })

  it("renders conviction score", () => {
    render(<HeroCandidatePanel pick={mockPick} />)
    expect(screen.getByText(/83/)).toBeInTheDocument()
  })

  it("renders factor bars", () => {
    render(<HeroCandidatePanel pick={mockPick} />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Value")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
  })

  it("renders timestamp", () => {
    render(<HeroCandidatePanel pick={mockPick} />)
    expect(screen.getByText(/last recalculated/i)).toBeInTheDocument()
  })

  it("renders with mock data when no pick provided", () => {
    render(<HeroCandidatePanel pick={null} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })
})
