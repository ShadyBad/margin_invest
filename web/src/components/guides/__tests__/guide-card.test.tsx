import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

import { GuideCard } from "../guide-card"

const guide = {
  slug: "how-scoring-works",
  title: "How Scoring Works",
  description: "Understand the dual-track scoring engine.",
  order: 1,
  updatedAt: "2026-02-19",
  readingTime: 8,
  category: "Core Concepts",
}

describe("GuideCard", () => {
  it("renders title and description", () => {
    render(<GuideCard guide={guide} index={0} />)
    expect(screen.getByText("How Scoring Works")).toBeInTheDocument()
    expect(screen.getByText("Understand the dual-track scoring engine.")).toBeInTheDocument()
  })

  it("renders reading time", () => {
    render(<GuideCard guide={guide} index={0} />)
    expect(screen.getByText("8 min read")).toBeInTheDocument()
  })

  it("links to the correct guide page", () => {
    render(<GuideCard guide={guide} index={0} />)
    const link = screen.getByRole("link")
    expect(link).toHaveAttribute("href", "/guides/how-scoring-works")
  })
})
