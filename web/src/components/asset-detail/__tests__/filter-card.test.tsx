import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FILTER_METADATA } from "@/lib/filter-metadata"
import { FilterCard } from "../filter-card"

describe("FILTER_METADATA", () => {
  it("every filter has an academic citation", () => {
    for (const [key, meta] of Object.entries(FILTER_METADATA)) {
      expect(meta.citation, `${key} missing citation`).toBeTruthy()
    }
  })
})

describe("FilterCard", () => {
  it("shows filing period when filter has detail containing period info", () => {
    const filter = {
      name: "altman_z_score",
      passed: true,
      value: 5.12,
      threshold: 1.1,
      detail: "Based on Q3 2025 10-Q filed Oct 2025",
      verdict: "passed",
    }
    render(<FilterCard filter={filter as any} expanded={true} />)
    expect(screen.getByText(/Q3 2025 10-Q/)).toBeInTheDocument()
  })
})
