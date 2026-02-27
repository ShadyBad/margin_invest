import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

import { GuideCard } from "../guide-card"

const guide = {
  slug: "scoring-factors",
  title: "Scoring Factors",
  description: "The five scoring pillars and how they combine.",
  order: 2,
  updatedAt: "2026-02-26",
  readingTime: 12,
  category: "Concepts",
}

describe("GuideCard", () => {
  it("renders title and description", () => {
    render(<GuideCard guide={guide} index={0} />)
    expect(screen.getByText("Scoring Factors")).toBeInTheDocument()
    expect(screen.getByText("The five scoring pillars and how they combine.")).toBeInTheDocument()
  })

  it("renders reading time", () => {
    render(<GuideCard guide={guide} index={0} />)
    expect(screen.getByText("12 min read")).toBeInTheDocument()
  })

  it("links to the correct guide page", () => {
    render(<GuideCard guide={guide} index={0} />)
    const link = screen.getByRole("link")
    expect(link).toHaveAttribute("href", "/guides/scoring-factors")
  })
})
