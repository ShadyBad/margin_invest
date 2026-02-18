import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, style, ...props }: any) => (
      <div style={style} {...props}>{children}</div>
    ),
  },
  useScroll: () => ({ scrollYProgress: { get: () => 0.5 } }),
  useTransform: (_: any, inputOrFn: number[] | Function, output?: any[]) => {
    if (typeof inputOrFn === "function") return inputOrFn(0)
    return output![Math.floor(output!.length / 2)]
  },
  useReducedMotion: () => false,
}))

import { ChapterCards } from "../chapter-cards"

describe("ChapterCards", () => {
  it("renders the section with data-chapter-cards attribute", () => {
    const { container } = render(<ChapterCards />)
    expect(container.querySelector("[data-chapter-cards]")).toBeInTheDocument()
  })

  it("renders engine row cards", () => {
    render(<ChapterCards />)
    // getAllByText because desktop + mobile both render (CSS hides one in real browser)
    expect(screen.getAllByText("Raw Signal").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Elimination Filters").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Factor Analysis").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Sector Normalization").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Conviction Output").length).toBeGreaterThanOrEqual(1)
  })

  it("renders proof row cards", () => {
    render(<ChapterCards />)
    expect(screen.getAllByText("Sample Score").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Factor Breakdown").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Growth vs Value").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Portfolio View").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Historical Accuracy").length).toBeGreaterThanOrEqual(1)
  })

  it("renders two row containers on desktop", () => {
    const { container } = render(<ChapterCards />)
    const rows = container.querySelectorAll("[data-card-row]")
    expect(rows).toHaveLength(2)
  })

  it("renders 10 total flow cards", () => {
    // Desktop renders 10 cards in rows, mobile renders 10 interleaved.
    // jsdom does not apply CSS media queries, so both layouts are present.
    // The desktop rows produce 10, mobile column produces 10 = 20 total in jsdom.
    const { container } = render(<ChapterCards />)
    const cards = container.querySelectorAll("[data-flow-card]")
    expect(cards).toHaveLength(20)
  })
})
