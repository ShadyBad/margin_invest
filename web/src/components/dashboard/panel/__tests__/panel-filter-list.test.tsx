import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { PanelFilterList } from "../panel-filter-list"
import type { FilterResultResponse } from "@/lib/api/types"

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion")
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      ...(actual as any).motion,
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    },
  }
})

const mockFilters: FilterResultResponse[] = [
  { name: "liquidity", passed: false, value: 5376, threshold: 300000, detail: "market_cap=$5,376", verdict: "fail" },
  { name: "beneish_m_score", passed: true, value: null, threshold: null, detail: "Insufficient data", verdict: "pass" },
  { name: "altman_z_score", passed: true, value: 6.48, threshold: 1.1, detail: "Z=6.4817", verdict: "pass" },
]

const mockFiltersWithInconclusive: FilterResultResponse[] = [
  { name: "liquidity", passed: false, value: 5376, threshold: 300000, detail: "market_cap=$5,376", verdict: "fail" },
  { name: "beneish_m_score", passed: true, value: null, threshold: null, detail: "Insufficient data for multi-year analysis", verdict: "inconclusive", missing_fields: ["receivables", "depreciation"] },
  { name: "altman_z_score", passed: true, value: 6.48, threshold: 1.1, detail: "Z=6.4817", verdict: "pass" },
]

describe("PanelFilterList", () => {
  it("renders filter header with pass count", () => {
    render(<PanelFilterList filters={mockFilters} />)
    expect(screen.getByText("Filters")).toBeInTheDocument()
    expect(screen.getByText("2/3")).toBeInTheDocument()
  })

  it("renders all filter rows", () => {
    render(<PanelFilterList filters={mockFilters} />)
    expect(screen.getByText("Liquidity")).toBeInTheDocument()
    expect(screen.getByText("Beneish M-Score")).toBeInTheDocument()
    expect(screen.getByText("Altman Z-Score")).toBeInTheDocument()
  })

  it("marks failed filters with red background", () => {
    render(<PanelFilterList filters={mockFilters} />)
    const row = screen.getByTestId("panel-filter-liquidity")
    expect(row.className).toContain("bg-")
  })

  it("expands filter detail on click", () => {
    render(<PanelFilterList filters={mockFilters} />)
    fireEvent.click(screen.getByTestId("panel-filter-liquidity"))
    expect(screen.getByText("market_cap=$5,376")).toBeInTheDocument()
  })

  it("renders INCONCLUSIVE badge for inconclusive filters", () => {
    render(<PanelFilterList filters={mockFiltersWithInconclusive} />)
    expect(screen.getByText("INCONCLUSIVE")).toBeInTheDocument()
  })

  it("shows amber icon for inconclusive filters", () => {
    render(<PanelFilterList filters={mockFiltersWithInconclusive} />)
    const row = screen.getByTestId("panel-filter-beneish_m_score")
    const icon = row.querySelector("span")
    expect(icon?.textContent).toBe("?")
    expect(icon?.className).toContain("text-amber-500")
  })

  it("shows amber background for inconclusive filters", () => {
    render(<PanelFilterList filters={mockFiltersWithInconclusive} />)
    const row = screen.getByTestId("panel-filter-beneish_m_score")
    expect(row.className).toContain("bg-[rgba(217,167,50,0.04)]")
  })

  it("shows 'Cannot assess' message when inconclusive filter is expanded", () => {
    render(<PanelFilterList filters={mockFiltersWithInconclusive} />)
    fireEvent.click(screen.getByTestId("panel-filter-beneish_m_score"))
    expect(screen.getByText(/Cannot assess/)).toBeInTheDocument()
  })

  it("shows missing fields when inconclusive filter is expanded", () => {
    render(<PanelFilterList filters={mockFiltersWithInconclusive} />)
    fireEvent.click(screen.getByTestId("panel-filter-beneish_m_score"))
    expect(screen.getByText("Missing: receivables, depreciation")).toBeInTheDocument()
  })

  it("shows inconclusive count indicator when inconclusive filters exist", () => {
    render(<PanelFilterList filters={mockFiltersWithInconclusive} />)
    expect(screen.getByText("1 inconclusive")).toBeInTheDocument()
  })

  it("does not show inconclusive count indicator when no inconclusive filters", () => {
    render(<PanelFilterList filters={mockFilters} />)
    expect(screen.queryByText(/inconclusive/)).not.toBeInTheDocument()
  })

  it("still shows detail text for inconclusive filters when expanded", () => {
    render(<PanelFilterList filters={mockFiltersWithInconclusive} />)
    fireEvent.click(screen.getByTestId("panel-filter-beneish_m_score"))
    expect(screen.getByText("Insufficient data for multi-year analysis")).toBeInTheDocument()
  })
})
