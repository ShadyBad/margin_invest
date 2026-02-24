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

import { EliminationVignette } from "../elimination-vignette"

describe("EliminationVignette", () => {
  it("renders the elimination narrative", () => {
    render(<EliminationVignette eliminatedPct={72} />)
    expect(screen.getByText(/72%/)).toBeInTheDocument()
    expect(screen.getByText(/eliminated/i)).toBeInTheDocument()
  })

  it("renders with fallback when no data", () => {
    render(<EliminationVignette />)
    expect(screen.getByText(/eliminated/i)).toBeInTheDocument()
  })
})
