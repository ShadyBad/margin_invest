import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { EliminationGauntlet } from "../elimination-gauntlet"

vi.mock("@/components/ui/formula-tooltip", () => ({
  FormulaTooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock("@/lib/filter-metadata", () => ({
  FILTER_METADATA: {
    beneish: { displayName: "Beneish M-Score", technicalName: "M-Score" },
    altman: { displayName: "Altman Z-Score", technicalName: "Z-Score" },
    liquidity: { displayName: "Liquidity", technicalName: "Market Cap" },
  },
}))

const passedFilter = {
  name: "beneish",
  passed: true,
  value: -2.4,
  threshold: -2.22,
  verdict: "pass",
  detail: null,
  computed_metrics: null,
}

const failedFilter = {
  name: "liquidity",
  passed: false,
  value: 12_000_000,
  threshold: 50_000_000,
  verdict: "fail",
  detail: null,
  computed_metrics: null,
}

describe("EliminationGauntlet", () => {
  it("renders filter pills instead of full cards", () => {
    render(
      <EliminationGauntlet
        filters={[passedFilter, failedFilter]}
        eliminated={false}
        totalScored={1000}
        filtersSurvivedCount={600}
      />
    )
    expect(screen.getAllByTestId(/^filter-pill-/)).toHaveLength(2)
  })

  it("shows pass/fail icons on pills", () => {
    render(
      <EliminationGauntlet
        filters={[passedFilter, failedFilter]}
        eliminated={false}
      />
    )
    const pills = screen.getAllByTestId(/^filter-pill-/)
    expect(pills[0]).toHaveTextContent("\u2713")
    expect(pills[1]).toHaveTextContent("\u2715")
  })

  it("expands detail when pill is clicked", async () => {
    const user = userEvent.setup()
    render(
      <EliminationGauntlet
        filters={[passedFilter]}
        eliminated={false}
      />
    )
    expect(screen.queryByTestId("filter-detail-beneish")).not.toBeInTheDocument()
    await user.click(screen.getByTestId("filter-pill-beneish"))
    expect(screen.getByTestId("filter-detail-beneish")).toBeInTheDocument()
  })
})
