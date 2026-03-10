import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock GSAP to prevent animation side effects in tests
vi.mock("gsap", () => ({
  default: {
    set: vi.fn(),
    to: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))

import { FactorSignature } from "../factor-signature"

const FULL_FACTORS = {
  quality: 95,
  value: 68,
  momentum: 84,
  sentiment: 79,
  growth: 88,
}

const NULL_SENTIMENT = {
  quality: 95,
  value: 68,
  momentum: 84,
  sentiment: null,
  growth: 88,
}

const ALL_NULL = {
  quality: null,
  value: null,
  momentum: null,
  sentiment: null,
  growth: null,
}

describe("FactorSignature", () => {
  describe("full variant", () => {
    it("renders 5 track lines", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" />
      )
      const tracks = container.querySelectorAll("[data-track]")
      expect(tracks).toHaveLength(5)
    })

    it("renders full factor labels", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="full" />)
      expect(screen.getByText("QUALITY")).toBeInTheDocument()
      expect(screen.getByText("VALUE")).toBeInTheDocument()
      expect(screen.getByText("MOMENTUM")).toBeInTheDocument()
      expect(screen.getByText("SENTIMENT")).toBeInTheDocument()
      expect(screen.getByText("GROWTH")).toBeInTheDocument()
    })

    it("renders percentile values", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="full" />)
      expect(screen.getByText("95")).toBeInTheDocument()
      expect(screen.getByText("68")).toBeInTheDocument()
    })

    it("renders marker dots for non-null factors", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" />
      )
      const dots = container.querySelectorAll("[data-marker-dot]")
      expect(dots).toHaveLength(5)
    })

    it("renders fill bars for non-null factors", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" />
      )
      const fills = container.querySelectorAll("[data-fill-bar]")
      expect(fills).toHaveLength(5)
    })

    it("renders connecting polyline", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" />
      )
      const polyline = container.querySelector("[data-connecting-line]")
      expect(polyline).toBeInTheDocument()
    })
  })

  describe("compact variant", () => {
    it("renders abbreviated labels", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="compact" />)
      expect(screen.getByText("Q")).toBeInTheDocument()
      expect(screen.getByText("V")).toBeInTheDocument()
      expect(screen.getByText("M")).toBeInTheDocument()
      expect(screen.getByText("S")).toBeInTheDocument()
      expect(screen.getByText("G")).toBeInTheDocument()
    })
  })

  describe("mini variant", () => {
    it("does not render labels", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="mini" />)
      expect(screen.queryByText("QUALITY")).not.toBeInTheDocument()
      expect(screen.queryByText("Q")).not.toBeInTheDocument()
    })

    it("does not render percentile values", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="mini" />)
      expect(screen.queryByText("95")).not.toBeInTheDocument()
    })

    it("still renders fill bars", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="mini" />
      )
      const fills = container.querySelectorAll("[data-fill-bar]")
      expect(fills).toHaveLength(5)
    })
  })

  describe("inline variant", () => {
    it("renders only dots, no labels or values", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="inline" />
      )
      expect(screen.queryByText("QUALITY")).not.toBeInTheDocument()
      expect(screen.queryByText("95")).not.toBeInTheDocument()
      const dots = container.querySelectorAll("[data-marker-dot]")
      expect(dots).toHaveLength(5)
    })
  })

  describe("null factor handling", () => {
    it("omits marker dot for null factors", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="full" />
      )
      const dots = container.querySelectorAll("[data-marker-dot]")
      expect(dots).toHaveLength(4) // sentiment is null
    })

    it("omits fill bar for null factors", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="full" />
      )
      const fills = container.querySelectorAll("[data-fill-bar]")
      expect(fills).toHaveLength(4)
    })

    it("still renders 5 tracks even with null factors", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="full" />
      )
      const tracks = container.querySelectorAll("[data-track]")
      expect(tracks).toHaveLength(5)
    })

    it("renders polyline with only non-null dots", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="full" />
      )
      const polyline = container.querySelector("[data-connecting-line]")
      expect(polyline).toBeInTheDocument()
    })

    it("renders dimmed ring for null factors in inline variant", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="inline" />
      )
      const nullDots = container.querySelectorAll("[data-null-dot]")
      expect(nullDots).toHaveLength(1)
    })

    it("handles all-null factors gracefully", () => {
      const { container } = render(
        <FactorSignature factors={ALL_NULL} variant="full" />
      )
      const tracks = container.querySelectorAll("[data-track]")
      expect(tracks).toHaveLength(5)
      const dots = container.querySelectorAll("[data-marker-dot]")
      expect(dots).toHaveLength(0)
      const polyline = container.querySelector("[data-connecting-line]")
      expect(polyline).not.toBeInTheDocument() // no dots to connect
    })
  })

  describe("edge cases", () => {
    it("clamps values at 0", () => {
      const factors = { quality: -5, value: 0, momentum: 0, sentiment: 0, growth: 0 }
      const { container } = render(
        <FactorSignature factors={factors} variant="full" />
      )
      expect(container.querySelector("svg")).toBeInTheDocument()
    })

    it("clamps values at 100", () => {
      const factors = { quality: 150, value: 100, momentum: 100, sentiment: 100, growth: 100 }
      const { container } = render(
        <FactorSignature factors={factors} variant="full" />
      )
      expect(container.querySelector("svg")).toBeInTheDocument()
    })

    it("applies custom className", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" className="my-custom" />
      )
      expect(container.firstChild).toHaveClass("my-custom")
    })
  })
})
