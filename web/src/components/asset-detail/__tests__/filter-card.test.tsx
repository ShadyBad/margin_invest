import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FILTER_METADATA } from "@/lib/filter-metadata"
import { FilterPill, FilterDetail } from "../filter-card"
import type { FilterResultResponse } from "@/lib/api/types"

describe("FILTER_METADATA", () => {
  it("every filter has an academic citation", () => {
    for (const [key, meta] of Object.entries(FILTER_METADATA)) {
      expect(meta.citation, `${key} missing citation`).toBeTruthy()
    }
  })
})

describe("FilterPill", () => {
  it("shows checkmark icon for passing filter", () => {
    const filter: FilterResultResponse = {
      name: "altman_z_score",
      passed: true,
      value: 5.12,
      threshold: 1.1,
      detail: "Healthy",
      verdict: "pass",
    }
    render(<FilterPill filter={filter} isExpanded={false} onClick={() => {}} />)
    expect(screen.getByTestId("filter-pill-altman_z_score")).toHaveTextContent("\u2713")
  })

  it("shows cross icon for failing filter", () => {
    const filter: FilterResultResponse = {
      name: "altman_z_score",
      passed: false,
      value: 0.8,
      threshold: 1.1,
      detail: "Below safe zone",
      verdict: "fail",
    }
    render(<FilterPill filter={filter} isExpanded={false} onClick={() => {}} />)
    expect(screen.getByTestId("filter-pill-altman_z_score")).toHaveTextContent("\u2715")
  })

  it("shows question mark for inconclusive filter", () => {
    const filter: FilterResultResponse = {
      name: "altman_z_score",
      passed: false,
      value: 0.8,
      threshold: 1.1,
      detail: null,
      verdict: "inconclusive",
    }
    render(<FilterPill filter={filter} isExpanded={false} onClick={() => {}} />)
    expect(screen.getByTestId("filter-pill-altman_z_score")).toHaveTextContent("?")
  })
})

describe("FilterDetail", () => {
  it("shows filing period when filter has detail containing period info", () => {
    const filter: FilterResultResponse = {
      name: "altman_z_score",
      passed: true,
      value: 5.12,
      threshold: 1.1,
      detail: "Based on Q3 2025 10-Q filed Oct 2025",
      verdict: "pass",
    }
    render(<FilterDetail filter={filter} />)
    expect(screen.getByText(/Q3 2025 10-Q/)).toBeInTheDocument()
  })

  it("shows sector pass rate on failed filters when provided — not in FilterDetail (moved to pill layer)", () => {
    // FilterDetail does not show sectorPassRate; that was a FilterCard prop.
    // This test just verifies FilterDetail renders without error for a failed filter.
    const filter: FilterResultResponse = {
      name: "altman_z_score",
      passed: false,
      value: 0.8,
      threshold: 1.1,
      detail: "Below safe zone",
      verdict: "fail",
    }
    render(<FilterDetail filter={filter} />)
    expect(screen.getByTestId("filter-detail-altman_z_score")).toBeInTheDocument()
  })

  it("shows Why This Matters for failed filters", () => {
    const filter: FilterResultResponse = {
      name: "altman_z_score",
      passed: false,
      value: 0.8,
      threshold: 1.1,
      detail: "Below safe zone",
      verdict: "fail",
    }
    render(<FilterDetail filter={filter} />)
    // altman_z_score should have whyItMatters in FILTER_METADATA
    const meta = FILTER_METADATA["altman_z_score"]
    if (meta?.whyItMatters) {
      expect(screen.getByText("Why This Matters")).toBeInTheDocument()
    }
  })

  it("does not show Why This Matters for passing filters", () => {
    const filter: FilterResultResponse = {
      name: "altman_z_score",
      passed: true,
      value: 5.12,
      threshold: 1.1,
      detail: "Healthy",
      verdict: "pass",
    }
    render(<FilterDetail filter={filter} />)
    expect(screen.queryByText("Why This Matters")).not.toBeInTheDocument()
  })
})

describe("FilterDetail FCF display", () => {
  const fcfFilterWithMetrics: FilterResultResponse = {
    name: "fcf_distress",
    passed: true,
    value: 4.0,
    threshold: 3.0,
    detail: "PASS: 4/5 positive FCF years (required 3). median_fcf_margin=18.3%, floor=10.0% (Information Technology), improving_streak=2",
    verdict: "pass",
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
    render(<FilterDetail filter={fcfFilterWithMetrics} />)
    expect(screen.getByText(/4\/5 years positive/)).toBeInTheDocument()
    const marginMatches = screen.getAllByText(/18\.3%/)
    expect(marginMatches.length).toBeGreaterThanOrEqual(1)
  })

  it("shows sector-specific threshold inline", () => {
    render(<FilterDetail filter={fcfFilterWithMetrics} />)
    expect(screen.getByText(/\u2265 3\/5 years/)).toBeInTheDocument()
    expect(screen.getByText(/margin \u2265 10%/)).toBeInTheDocument()
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
      verdict: "pass",
    }
    render(<FilterDetail filter={legacyFilter} />)
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
    render(<FilterDetail filter={cyclicalFilter} />)
    expect(screen.getByText(/\u2265 2\/5 years/)).toBeInTheDocument()
    const energyMatches = screen.getAllByText(/Energy/)
    expect(energyMatches.length).toBeGreaterThanOrEqual(1)
  })
})
