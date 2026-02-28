import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: Record<string, unknown> & { children?: React.ReactNode }) => <div {...props as React.HTMLAttributes<HTMLDivElement>}>{children}</div>,
  },
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { ProofSelectivityFunnel } from "../proof-selectivity-funnel"

const MOCK_FUNNEL = {
  universe_size: 3200,
  survived_filters: 280,
  exceptional_count: 12,
  high_count: 35,
  medium_count: 58,
  last_scored_at: "2026-02-26T04:30:00Z",
}

describe("ProofSelectivityFunnel", () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it("renders loading skeleton initially", () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    render(<ProofSelectivityFunnel />)
    expect(screen.getByTestId("funnel-skeleton")).toBeInTheDocument()
  })

  it("renders funnel bars after data loads", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_FUNNEL,
    })
    render(<ProofSelectivityFunnel />)
    expect(await screen.findByText(/3,200 equities screened/)).toBeInTheDocument()
    expect(screen.getByText(/280 survived/)).toBeInTheDocument()
    expect(screen.getByText(/12 Exceptional/)).toBeInTheDocument()
  })

  it("renders subtitle text", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_FUNNEL,
    })
    render(<ProofSelectivityFunnel />)
    expect(await screen.findByText(/most equities are eliminated/i)).toBeInTheDocument()
  })

  it("renders safeguard footnote", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_FUNNEL,
    })
    render(<ProofSelectivityFunnel />)
    expect(
      await screen.findByText(/insufficient data or failing fundamentals/i)
    ).toBeInTheDocument()
  })
})
