import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { FilterCard } from "../filter-card"
import { PillarCard } from "../pillar-card"
import { ConvictionEngine } from "../conviction-engine"
import { ValuationSection } from "../valuation-section"
import { FORMULA_DEFINITIONS } from "@/lib/formula-definitions"

// Mock getValuationAudit used by ValuationSection
vi.mock("@/lib/api/scores", () => ({
  getValuationAudit: vi.fn().mockResolvedValue({}),
}))

describe("FormulaTooltip integration", () => {
  describe("FilterCard", () => {
    it("shows formula tooltip trigger for beneish_m_score", () => {
      render(
        <FilterCard
          filter={{
            name: "beneish_m_score",
            passed: false,
            value: -1.42,
            threshold: -1.78,
            detail: "Q3 2025 filing",
            verdict: "fail",
          }}
          expanded={true}
        />
      )
      expect(screen.getByTestId("formula-trigger-beneish_m_score")).toBeInTheDocument()
    })

    it("shows formula on hover of filter metric", async () => {
      render(
        <FilterCard
          filter={{
            name: "beneish_m_score",
            passed: false,
            value: -1.42,
            threshold: -1.78,
            detail: "Q3 2025 filing",
            verdict: "fail",
          }}
          expanded={true}
        />
      )
      fireEvent.mouseEnter(screen.getByTestId("formula-trigger-beneish_m_score"))
      const def = FORMULA_DEFINITIONS.beneish_m_score
      expect(await screen.findByText(def.formula)).toBeInTheDocument()
    })

    it("shows formula tooltip trigger for altman_z_score", () => {
      render(
        <FilterCard
          filter={{
            name: "altman_z_score",
            passed: true,
            value: 5.12,
            threshold: 1.1,
            detail: "Based on Q3 2025 10-Q",
            verdict: "passed",
          }}
          expanded={false}
        />
      )
      expect(screen.getByTestId("formula-trigger-altman_z_score")).toBeInTheDocument()
    })
  })

  describe("PillarCard", () => {
    it("shows formula tooltip trigger for sub-factor names", async () => {
      render(
        <PillarCard
          pillar={{
            factor_name: "quality",
            weight: 0.4,
            average_percentile: 72,
            sub_scores: [
              {
                name: "gross_profitability",
                raw_value: 0.35,
                percentile_rank: 78,
                detail: "Strong",
              },
              {
                name: "roic_wacc_spread",
                raw_value: 0.08,
                percentile_rank: 65,
                detail: "Above avg",
              },
            ],
          }}
        />
      )

      // Expand sub-factors
      fireEvent.click(screen.getByTestId("pillar-quality-toggle"))

      await waitFor(() => {
        expect(screen.getByTestId("formula-trigger-gross_profitability")).toBeInTheDocument()
        expect(screen.getByTestId("formula-trigger-roic_wacc_spread")).toBeInTheDocument()
      })
    })

    it("shows formula tooltip content on hover of sub-factor", async () => {
      render(
        <PillarCard
          pillar={{
            factor_name: "quality",
            weight: 0.4,
            average_percentile: 72,
            sub_scores: [
              {
                name: "gross_profitability",
                raw_value: 0.35,
                percentile_rank: 78,
                detail: "Strong",
              },
            ],
          }}
        />
      )

      // Expand sub-factors
      fireEvent.click(screen.getByTestId("pillar-quality-toggle"))

      await waitFor(() => {
        expect(screen.getByTestId("formula-trigger-gross_profitability")).toBeInTheDocument()
      })

      fireEvent.mouseEnter(screen.getByTestId("formula-trigger-gross_profitability"))
      const def = FORMULA_DEFINITIONS.gross_profitability
      expect(await screen.findByText(def.formula)).toBeInTheDocument()
    })
  })

  describe("ConvictionEngine", () => {
    it("shows formula tooltip trigger for asymmetry_ratio", () => {
      render(
        <ConvictionEngine
          opportunityType="compounder"
          winningTrack="compounder"
          asymmetryRatio={4.2}
          maxPositionPct={5.0}
          timingSignal="buy_now"
          capitalAllocation={null}
          catalyst={null}
        />
      )
      expect(screen.getByTestId("formula-trigger-asymmetry_ratio")).toBeInTheDocument()
    })

    it("shows formula tooltip trigger for max_position_pct", () => {
      render(
        <ConvictionEngine
          opportunityType="compounder"
          winningTrack="compounder"
          asymmetryRatio={4.2}
          maxPositionPct={5.0}
          timingSignal="buy_now"
          capitalAllocation={null}
          catalyst={null}
        />
      )
      expect(screen.getByTestId("formula-trigger-max_position_pct")).toBeInTheDocument()
    })

    it("shows formula content on hover of asymmetry ratio", async () => {
      render(
        <ConvictionEngine
          opportunityType="compounder"
          winningTrack="compounder"
          asymmetryRatio={4.2}
          maxPositionPct={5.0}
          timingSignal="buy_now"
          capitalAllocation={null}
          catalyst={null}
        />
      )
      fireEvent.mouseEnter(screen.getByTestId("formula-trigger-asymmetry_ratio"))
      const def = FORMULA_DEFINITIONS.asymmetry_ratio
      expect(await screen.findByText(def.formula)).toBeInTheDocument()
    })
  })

  describe("ValuationSection", () => {
    it("shows formula tooltip triggers for valuation methods", () => {
      render(
        <ValuationSection
          ticker="AAPL"
          buyPrice={142}
          sellPrice={214}
          intrinsicValue={165}
          currentPrice={187.42}
          priceUpside={-0.119}
          marginOfSafety={-0.136}
          valuationMethods={{
            dcf: 158.2,
            ev_fcf: 172.4,
            acquirers_multiple: 161.8,
            shareholder_yield: 170.5,
          }}
        />
      )
      expect(screen.getByTestId("formula-trigger-dcf_valuation")).toBeInTheDocument()
      expect(screen.getByTestId("formula-trigger-ev_fcf_valuation")).toBeInTheDocument()
      expect(screen.getByTestId("formula-trigger-ev_ebit_valuation")).toBeInTheDocument()
      expect(screen.getByTestId("formula-trigger-shareholder_yield_valuation")).toBeInTheDocument()
    })

    it("shows formula content on hover of DCF method", async () => {
      render(
        <ValuationSection
          ticker="AAPL"
          buyPrice={142}
          sellPrice={214}
          intrinsicValue={165}
          currentPrice={187.42}
          priceUpside={-0.119}
          marginOfSafety={-0.136}
          valuationMethods={{ dcf: 158.2 }}
        />
      )
      fireEvent.mouseEnter(screen.getByTestId("formula-trigger-dcf_valuation"))
      const def = FORMULA_DEFINITIONS.dcf_valuation
      expect(await screen.findByText(def.formula)).toBeInTheDocument()
    })
  })
})
