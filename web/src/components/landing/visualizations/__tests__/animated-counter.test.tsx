import { render, screen, act } from "@testing-library/react"
import { describe, expect, test, vi, beforeEach, afterEach } from "vitest"
import { AnimatedCounter } from "../animated-counter"

describe("AnimatedCounter", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // Mock requestAnimationFrame to use setTimeout so fake timers control it
    let rafId = 0
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      rafId += 1
      const id = rafId
      setTimeout(() => cb(performance.now()), 16)
      return id
    })
    vi.stubGlobal("cancelAnimationFrame", (id: number) => {
      clearTimeout(id)
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  test("renders target value after animation completes", () => {
    render(<AnimatedCounter target={3056} />)
    // Advance past the default 1000ms duration
    act(() => {
      vi.advanceTimersByTime(1200)
    })
    expect(screen.getByText("3,056")).toBeInTheDocument()
  })

  test("renders 0 when target is 0", () => {
    render(<AnimatedCounter target={0} />)
    expect(screen.getByText("0")).toBeInTheDocument()
  })

  test("starts animation from 0", () => {
    render(<AnimatedCounter target={1000} />)
    // Before any timers fire, should show 0
    expect(screen.getByText("0")).toBeInTheDocument()
  })

  test("applies className to span", () => {
    const { container } = render(
      <AnimatedCounter target={100} className="text-xl font-bold" />
    )
    const span = container.querySelector("span")
    expect(span).toBeInTheDocument()
    expect(span?.classList.contains("text-xl")).toBe(true)
    expect(span?.classList.contains("font-bold")).toBe(true)
  })

  test("formats number with locale separator", () => {
    render(<AnimatedCounter target={1000000} />)
    act(() => {
      vi.advanceTimersByTime(1200)
    })
    // Should have comma separators (locale-dependent, but en-US uses commas)
    expect(screen.getByText("1,000,000")).toBeInTheDocument()
  })

  test("renders as a span element", () => {
    const { container } = render(<AnimatedCounter target={42} />)
    const span = container.querySelector("span")
    expect(span).toBeInTheDocument()
  })
})
