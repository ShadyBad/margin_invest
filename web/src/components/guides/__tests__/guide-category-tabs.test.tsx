import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: Record<string, unknown> & { children?: React.ReactNode }) => <div {...props as React.HTMLAttributes<HTMLDivElement>}>{children}</div>,
  },
}))

import { GuideCategoryTabs } from "../guide-category-tabs"
import type { GuideMetadata } from "@/lib/guides"

function makeGuide(overrides: Partial<GuideMetadata> & { slug: string }): GuideMetadata {
  return {
    title: overrides.slug,
    description: "desc",
    order: 1,
    updatedAt: "2026-02-26",
    readingTime: 5,
    category: "Concepts",
    ...overrides,
  }
}

const grouped = {
  Concepts: [
    makeGuide({ slug: "scoring", title: "How Scoring Works" }),
    makeGuide({ slug: "conviction", title: "Conviction Levels" }),
  ],
  Workflows: [makeGuide({ slug: "getting-started", title: "Getting Started" })],
  Reference: [makeGuide({ slug: "glossary", title: "Glossary" })],
}

describe("GuideCategoryTabs", () => {
  it("renders all three category tabs", () => {
    render(<GuideCategoryTabs grouped={grouped} />)
    expect(screen.getByRole("tab", { name: /Concepts/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Workflows/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Reference/i })).toBeInTheDocument()
  })

  it("shows counts per category", () => {
    render(<GuideCategoryTabs grouped={grouped} />)
    expect(screen.getByRole("tab", { name: /Concepts \(2\)/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Workflows \(1\)/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /Reference \(1\)/i })).toBeInTheDocument()
  })

  it("shows Concepts guides by default", () => {
    render(<GuideCategoryTabs grouped={grouped} />)
    expect(screen.getByText("How Scoring Works")).toBeInTheDocument()
    expect(screen.getByText("Conviction Levels")).toBeInTheDocument()
    expect(screen.queryByText("Getting Started")).not.toBeInTheDocument()
    expect(screen.queryByText("Glossary")).not.toBeInTheDocument()
  })

  it("switches to Workflows tab when clicked", () => {
    render(<GuideCategoryTabs grouped={grouped} />)
    fireEvent.click(screen.getByRole("tab", { name: /Workflows/i }))
    expect(screen.getByText("Getting Started")).toBeInTheDocument()
    expect(screen.queryByText("How Scoring Works")).not.toBeInTheDocument()
  })

  it("sets aria-selected correctly on active tab", () => {
    render(<GuideCategoryTabs grouped={grouped} />)
    expect(screen.getByRole("tab", { name: /Concepts/i })).toHaveAttribute(
      "aria-selected",
      "true"
    )
    expect(screen.getByRole("tab", { name: /Workflows/i })).toHaveAttribute(
      "aria-selected",
      "false"
    )

    fireEvent.click(screen.getByRole("tab", { name: /Reference/i }))
    expect(screen.getByRole("tab", { name: /Reference/i })).toHaveAttribute(
      "aria-selected",
      "true"
    )
    expect(screen.getByRole("tab", { name: /Concepts/i })).toHaveAttribute(
      "aria-selected",
      "false"
    )
  })
})
