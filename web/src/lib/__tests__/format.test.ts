import { describe, it, expect } from "vitest"
import { formatAttributeLabel } from "../format"

describe("formatAttributeLabel", () => {
  it("converts snake_case to Title Case", () => {
    expect(formatAttributeLabel("gross_profitability")).toBe("Gross Profitability")
  })

  it("converts single word", () => {
    expect(formatAttributeLabel("sentiment")).toBe("Sentiment")
    expect(formatAttributeLabel("liquidity")).toBe("Liquidity")
  })

  it("handles multi-word snake_case", () => {
    expect(formatAttributeLabel("free_cash_flow")).toBe("Free Cash Flow")
    expect(formatAttributeLabel("price_momentum")).toBe("Price Momentum")
    expect(formatAttributeLabel("shareholder_yield")).toBe("Shareholder Yield")
    expect(formatAttributeLabel("insider_cluster")).toBe("Insider Cluster")
    expect(formatAttributeLabel("institutional_accumulation")).toBe("Institutional Accumulation")
    expect(formatAttributeLabel("acquirers_multiple")).toBe("Acquirers Multiple")
    expect(formatAttributeLabel("interest_coverage")).toBe("Interest Coverage")
    expect(formatAttributeLabel("current_ratio")).toBe("Current Ratio")
  })

  it("preserves known financial acronyms", () => {
    expect(formatAttributeLabel("roic_wacc_spread")).toBe("ROIC WACC Spread")
    expect(formatAttributeLabel("roic_score")).toBe("ROIC Score")
    expect(formatAttributeLabel("ebitda_margin")).toBe("EBITDA Margin")
    expect(formatAttributeLabel("eps_growth")).toBe("EPS Growth")
    expect(formatAttributeLabel("ev_fcf")).toBe("EV FCF")
    expect(formatAttributeLabel("sue")).toBe("SUE")
    expect(formatAttributeLabel("fcf_distress")).toBe("FCF Distress")
  })

  it("handles score-suffixed names", () => {
    expect(formatAttributeLabel("piotroski_f_score")).toBe("Piotroski F-Score")
    expect(formatAttributeLabel("beneish_m_score")).toBe("Beneish M-Score")
    expect(formatAttributeLabel("altman_z_score")).toBe("Altman Z-Score")
    expect(formatAttributeLabel("accrual_ratio")).toBe("Accrual Ratio")
  })

  it("handles growth stage values", () => {
    expect(formatAttributeLabel("high_growth")).toBe("High Growth")
    expect(formatAttributeLabel("steady_growth")).toBe("Steady Growth")
    expect(formatAttributeLabel("mature")).toBe("Mature")
    expect(formatAttributeLabel("cyclical")).toBe("Cyclical")
    expect(formatAttributeLabel("turnaround")).toBe("Turnaround")
  })

  it("returns empty string for empty input", () => {
    expect(formatAttributeLabel("")).toBe("")
  })

  it("handles already-formatted strings", () => {
    expect(formatAttributeLabel("Quality")).toBe("Quality")
    expect(formatAttributeLabel("Value")).toBe("Value")
    expect(formatAttributeLabel("Momentum")).toBe("Momentum")
  })
})
