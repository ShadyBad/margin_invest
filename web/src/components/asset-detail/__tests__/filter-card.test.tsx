import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FILTER_METADATA } from "@/lib/filter-metadata"
import { FilterCard } from "../filter-card"
import type { FilterResultResponse } from "@/lib/api/types"

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
    render(<FilterCard filter={filter as FilterResultResponse} expanded={true} />)
    expect(screen.getByText(/Q3 2025 10-Q/)).toBeInTheDocument()
  })

  it("shows sector pass rate on failed filters when provided", () => {
    const filter = {
      name: "altman_z_score",
      passed: false,
      value: 0.8,
      threshold: 1.1,
      detail: "Below safe zone",
      verdict: "failed",
    }
    render(
      <FilterCard
        filter={filter as FilterResultResponse}
        expanded={true}
        sectorPassRate={0.68}
        sectorName="Consumer Discretionary"
      />
    )
    expect(
      screen.getByText("68% of Consumer Discretionary stocks pass this filter.")
    ).toBeInTheDocument()
  })

  it("does not show sector pass rate on passing filters", () => {
    const filter = {
      name: "altman_z_score",
      passed: true,
      value: 5.12,
      threshold: 1.1,
      detail: "Healthy",
      verdict: "passed",
    }
    render(
      <FilterCard
        filter={filter as FilterResultResponse}
        expanded={true}
        sectorPassRate={0.68}
        sectorName="Consumer Discretionary"
      />
    )
    expect(screen.queryByText(/68%/)).not.toBeInTheDocument()
  })

  it("does not show sector pass rate when not provided", () => {
    const filter = {
      name: "altman_z_score",
      passed: false,
      value: 0.8,
      threshold: 1.1,
      detail: "Below safe zone",
      verdict: "failed",
    }
    render(<FilterCard filter={filter as FilterResultResponse} expanded={true} />)
    expect(
      screen.queryByText(/stocks pass this filter/)
    ).not.toBeInTheDocument()
  })
})
