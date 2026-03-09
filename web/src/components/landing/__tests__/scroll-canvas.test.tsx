import { describe, it, expect, vi } from "vitest"
import { render, screen, renderHook } from "@testing-library/react"

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
vi.mock("gsap/ScrollSmoother", () => ({
  default: { create: vi.fn(() => ({ kill: vi.fn() })) },
}))
vi.mock("@/hooks/use-media-query", () => ({
  useMediaQuery: vi.fn(() => false),
  useIsMobile: vi.fn(() => false),
}))

import { ScrollCanvas, useScrollCanvas } from "../scroll-canvas"

describe("ScrollCanvas", () => {
  it("renders its children", () => {
    render(
      <ScrollCanvas>
        <div data-testid="child">Hello</div>
      </ScrollCanvas>
    )
    expect(screen.getByTestId("child")).toBeInTheDocument()
    expect(screen.getByText("Hello")).toBeInTheDocument()
  })

  it("renders gradient layer", () => {
    render(
      <ScrollCanvas>
        <div>content</div>
      </ScrollCanvas>
    )
    expect(screen.getByTestId("canvas-gradient")).toBeInTheDocument()
  })

  it("renders grid layer", () => {
    render(
      <ScrollCanvas>
        <div>content</div>
      </ScrollCanvas>
    )
    expect(screen.getByTestId("canvas-grid")).toBeInTheDocument()
  })

  it("renders noise layer", () => {
    render(
      <ScrollCanvas>
        <div>content</div>
      </ScrollCanvas>
    )
    expect(screen.getByTestId("canvas-noise")).toBeInTheDocument()
  })

  it("renders smooth-wrapper and smooth-content divs", () => {
    const { container } = render(
      <ScrollCanvas>
        <div>content</div>
      </ScrollCanvas>
    )
    const wrapper = container.querySelector("#smooth-wrapper")
    const content = container.querySelector("#smooth-content")
    expect(wrapper).toBeInTheDocument()
    expect(content).toBeInTheDocument()
  })

  it("places children inside #smooth-content", () => {
    render(
      <ScrollCanvas>
        <div data-testid="nested-child">nested</div>
      </ScrollCanvas>
    )
    const content = document.querySelector("#smooth-content")
    expect(content).toBeInTheDocument()
    const child = screen.getByTestId("nested-child")
    expect(content!.contains(child)).toBe(true)
  })

  it("places background layers outside #smooth-content", () => {
    render(
      <ScrollCanvas>
        <div>content</div>
      </ScrollCanvas>
    )
    const content = document.querySelector("#smooth-content")
    const gradient = screen.getByTestId("canvas-gradient")
    const grid = screen.getByTestId("canvas-grid")
    const noise = screen.getByTestId("canvas-noise")

    expect(content!.contains(gradient)).toBe(false)
    expect(content!.contains(grid)).toBe(false)
    expect(content!.contains(noise)).toBe(false)
  })
})

describe("useScrollCanvas", () => {
  it("returns default values (ready: false, isSmoothScrolling: false) outside provider", () => {
    const { result } = renderHook(() => useScrollCanvas())
    expect(result.current.ready).toBe(false)
    expect(result.current.isSmoothScrolling).toBe(false)
  })
})
