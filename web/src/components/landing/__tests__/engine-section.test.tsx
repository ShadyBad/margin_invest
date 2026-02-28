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
    })),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { EngineSection } from "../engine-section"

describe("EngineSection", () => {
  const noop = vi.fn()

  it("renders top row card titles", () => {
    render(<EngineSection onStageChange={noop} />)
    // Cards appear in both desktop and mobile layouts
    expect(screen.getAllByText("Raw Market Signal").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Elimination Filters").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Liquidity Thresholding").length).toBeGreaterThanOrEqual(1)
  })

  it("renders bottom row card titles", () => {
    render(<EngineSection onStageChange={noop} />)
    // Cards appear in both desktop and mobile layouts
    expect(screen.getAllByText("Multi-Factor Ranking").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Composite Score Synthesis").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Portfolio Correlation Mapping").length).toBeGreaterThanOrEqual(1)
  })
})
