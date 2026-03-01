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

  it("renders error state on failed fetch", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 502 })
    render(<ProofSelectivityFunnel />)
    expect(await screen.findByTestId("funnel-error")).toBeInTheDocument()
    expect(screen.getByText(/selectivity data unavailable/i)).toBeInTheDocument()
  })

  it("renders error state on network error", async () => {
    mockFetch.mockRejectedValue(new Error("Network error"))
    render(<ProofSelectivityFunnel />)
    expect(await screen.findByTestId("funnel-error")).toBeInTheDocument()
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

  it("renders labels outside narrow bars", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_FUNNEL,
    })
    render(<ProofSelectivityFunnel />)
    // Exceptional bar = 12/3200 = 0.375% → clamped to 4% → labels external
    const label = await screen.findByText(/12 Exceptional/)
    // External label should NOT have truncate class
    expect(label.className).not.toContain("truncate")
    // External label should be a sibling of the bar, not a child
    const bar = label.closest("[data-testid='funnel-row-exceptional_count']")
    expect(bar).toBeInTheDocument()
    const coloredBar = bar!.querySelector("[data-testid='funnel-bar']")
    expect(coloredBar).toBeInTheDocument()
    expect(coloredBar!.contains(label)).toBe(false)
  })

  it("renders labels inside wide bars", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_FUNNEL,
    })
    render(<ProofSelectivityFunnel />)
    // Universe bar = 100% → labels internal
    const label = await screen.findByText(/3,200 equities screened/)
    const bar = label.closest("[data-testid='funnel-row-universe_size']")
    const coloredBar = bar!.querySelector("[data-testid='funnel-bar']")
    expect(coloredBar!.contains(label)).toBe(true)
  })
})
