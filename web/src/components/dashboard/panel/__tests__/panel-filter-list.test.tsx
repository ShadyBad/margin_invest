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
  { name: "liquidity", passed: false, value: 5376, threshold: 300000, detail: "market_cap=$5,376", verdict: "FAIL" },
  { name: "beneish_m_score", passed: true, value: null, threshold: null, detail: "Insufficient data", verdict: "PASS" },
  { name: "altman_z_score", passed: true, value: 6.48, threshold: 1.1, detail: "Z=6.4817", verdict: "PASS" },
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
})
