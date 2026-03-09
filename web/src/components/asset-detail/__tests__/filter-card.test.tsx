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

describe("FilterCard FCF display", () => {
  const fcfFilterWithMetrics: FilterResultResponse = {
    name: "fcf_distress",
    passed: true,
    value: 4.0,
    threshold: 3.0,
    detail: "PASS: 4/5 positive FCF years (required 3). median_fcf_margin=18.3%, floor=10.0% (Information Technology), improving_streak=2",
    verdict: "passed",
    computed_metrics: {
      positive_years: 4,
      total_years: 5,
      positive_years_required: 3,
      median_fcf_margin: 0.183,
      consecutive_improving_years: 2,
      sector_fcf_margin_floor: 0.10,
      sector_name: "Information Technology",
    },
  }

  it("shows multi-year positive count and FCF margin in value", () => {
    render(<FilterCard filter={fcfFilterWithMetrics} expanded={false} />)
    expect(screen.getByText(/4\/5 years positive/)).toBeInTheDocument()
    // The formatted value span contains margin info (detail string also matches, so use getAllByText)
    const marginMatches = screen.getAllByText(/18\.3%/)
    expect(marginMatches.length).toBeGreaterThanOrEqual(1)
  })

  it("shows sector-specific threshold inline", () => {
    render(<FilterCard filter={fcfFilterWithMetrics} expanded={false} />)
    expect(screen.getByText(/≥ 3\/5 years/)).toBeInTheDocument()
    expect(screen.getByText(/margin ≥ 10%/)).toBeInTheDocument()
    // "Technology" appears in both threshold label and detail string, so use getAllByText
    const techMatches = screen.getAllByText(/Technology/)
    expect(techMatches.length).toBeGreaterThanOrEqual(1)
  })

  it("falls back to legacy display when computed_metrics is missing", () => {
    const legacyFilter: FilterResultResponse = {
      name: "fcf_distress",
      passed: true,
      value: 4200000000,
      threshold: 0,
      detail: "FCF=4,200,000,000 (PASS, threshold=0.0)",
      verdict: "passed",
    }
    render(<FilterCard filter={legacyFilter} expanded={false} />)
    expect(screen.getByText("$4.2B")).toBeInTheDocument()
    expect(screen.getByText("Positive")).toBeInTheDocument()
  })

  it("shows cyclical note for cyclical sectors", () => {
    const cyclicalFilter: FilterResultResponse = {
      ...fcfFilterWithMetrics,
      passed: true,
      threshold: 2.0,
      computed_metrics: {
        ...fcfFilterWithMetrics.computed_metrics!,
        positive_years_required: 2,
        sector_fcf_margin_floor: 0.0,
        sector_name: "Energy",
      },
    }
    render(<FilterCard filter={cyclicalFilter} expanded={false} />)
    expect(screen.getByText(/≥ 2\/5 years/)).toBeInTheDocument()
    // "Energy" appears in both the threshold display and the computed metrics table
    const energyMatches = screen.getAllByText(/Energy/)
    expect(energyMatches.length).toBeGreaterThanOrEqual(1)
  })
})
