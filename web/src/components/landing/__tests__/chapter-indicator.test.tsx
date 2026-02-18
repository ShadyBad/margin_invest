import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, act } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ChapterIndicator } from "../chapter-indicator"

// Mock IntersectionObserver
let observerCallback: IntersectionObserverCallback
const mockObserve = vi.fn()
const mockDisconnect = vi.fn()

beforeEach(() => {
  mockObserve.mockClear()
  mockDisconnect.mockClear()

  class MockIntersectionObserver {
    constructor(callback: IntersectionObserverCallback) {
      observerCallback = callback
    }
    observe = mockObserve
    disconnect = mockDisconnect
    unobserve = vi.fn()
  }

  vi.stubGlobal("IntersectionObserver", MockIntersectionObserver)

  // Create section elements in the DOM
  for (const id of ["signal", "engine", "path"]) {
    const el = document.createElement("section")
    el.id = id
    document.body.appendChild(el)
  }
})

afterEach(() => {
  for (const id of ["signal", "engine", "path"]) {
    document.getElementById(id)?.remove()
  }
  vi.unstubAllGlobals()
})

describe("ChapterIndicator", () => {
  it("renders 3 dots", () => {
    const { container } = render(<ChapterIndicator />)
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots).toHaveLength(3)
  })

  it("highlights first dot by default", () => {
    const { container } = render(<ChapterIndicator />)
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots[0].getAttribute("data-active")).toBe("true")
    expect(dots[1].getAttribute("data-active")).toBe("false")
    expect(dots[2].getAttribute("data-active")).toBe("false")
  })

  it("has correct aria labels", () => {
    const { container } = render(<ChapterIndicator />)
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots[0].getAttribute("aria-label")).toBe("The Signal")
    expect(dots[1].getAttribute("aria-label")).toBe("The Engine")
    expect(dots[2].getAttribute("aria-label")).toBe("The Path")
  })

  it("has nav with aria-label", () => {
    const { container } = render(<ChapterIndicator />)
    const nav = container.querySelector("nav")
    expect(nav?.getAttribute("aria-label")).toBe("Page chapters")
  })

  it("observes all three sections", () => {
    render(<ChapterIndicator />)
    expect(mockObserve).toHaveBeenCalledTimes(3)
  })

  it("updates active dot when section intersects", () => {
    const { container } = render(<ChapterIndicator />)

    // Simulate engine section becoming visible
    act(() => {
      observerCallback(
        [{ isIntersecting: true, target: document.getElementById("engine")! }] as any,
        {} as any,
      )
    })

    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots[1].getAttribute("data-active")).toBe("true")
  })

  it("scrolls to section on click", async () => {
    const u = userEvent.setup()
    const mockScrollIntoView = vi.fn()
    document.getElementById("engine")!.scrollIntoView = mockScrollIntoView

    const { container } = render(<ChapterIndicator />)
    const dots = container.querySelectorAll("[data-chapter-dot]")

    await u.click(dots[1])
    expect(mockScrollIntoView).toHaveBeenCalledWith({ behavior: "smooth" })
  })

  it("disconnects observer on unmount", () => {
    const { unmount } = render(<ChapterIndicator />)
    unmount()
    expect(mockDisconnect).toHaveBeenCalled()
  })
})
