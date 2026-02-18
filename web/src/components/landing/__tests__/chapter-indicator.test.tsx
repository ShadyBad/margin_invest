import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { ChapterIndicator } from "../chapter-indicator"

describe("ChapterIndicator", () => {
  it("renders dots for each chapter", () => {
    const { container } = render(
      <ChapterIndicator chapters={4} activeChapter={0} />,
    )
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots).toHaveLength(4)
  })

  it("highlights the active chapter", () => {
    const { container } = render(
      <ChapterIndicator chapters={4} activeChapter={2} />,
    )
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots[2].getAttribute("data-active")).toBe("true")
  })

  it("has correct aria labels", () => {
    const { container } = render(
      <ChapterIndicator
        chapters={4}
        activeChapter={1}
        labels={["The Signal", "The Engine", "The Proof", "The Path"]}
      />,
    )
    const nav = container.querySelector("nav")
    expect(nav?.getAttribute("aria-label")).toBe("Page chapters")
  })

  it("works with 3 chapters for new layout", () => {
    const { container } = render(
      <ChapterIndicator
        chapters={3}
        activeChapter={0}
        labels={["The Signal", "The Engine", "The Path"]}
      />,
    )
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots).toHaveLength(3)
  })
})
