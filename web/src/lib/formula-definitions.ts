/**
 * Static map of all metric formulas used across the platform.
 * Used by FormulaTooltip to display formula, source, and interpretation on hover.
 */
export interface FormulaDefinition {
  name: string
  formula: string
  source: string
  interpretation: string
}

export const FORMULA_DEFINITIONS: Record<string, FormulaDefinition> = {
  // Filters
  beneish_m_score: {
    name: "Beneish M-Score",
    formula:
      "-4.84 + 0.92\u00B7DSRI + 0.528\u00B7GMI + 0.404\u00B7AQI + 0.892\u00B7SGI + 0.115\u00B7DEPI \u2212 0.172\u00B7SGAI + 4.679\u00B7TATA \u2212 0.327\u00B7LVGI",
    source: "Beneish (1999)",
    interpretation: "Above \u22121.78 signals elevated earnings manipulation risk.",
  },
  altman_z_score: {
    name: "Altman Z-Score",
    formula:
      "1.2\u00B7(WC/TA) + 1.4\u00B7(RE/TA) + 3.3\u00B7(EBIT/TA) + 0.6\u00B7(MVE/TL) + 1.0\u00B7(Sales/TA)",
    source: "Altman (1968)",
    interpretation: "Below 1.81 = distress zone. Above 2.99 = safe zone.",
  },
  fcf_distress: {
    name: "Free Cash Flow",
    formula: "CFO \u2212 CapEx",
    source: "Standard cash flow analysis",
    interpretation: "Negative FCF means the company is burning cash. Increases dilution risk.",
  },
  interest_coverage: {
    name: "Interest Coverage Ratio",
    formula: "EBIT / Interest Expense",
    source: "Standard credit analysis",
    interpretation: "Higher is better. Below 1.5\u00D7 signals debt service risk.",
  },
  current_ratio: {
    name: "Current Ratio",
    formula: "Current Assets / Current Liabilities",
    source: "Standard liquidity analysis",
    interpretation: "Above 1.0 means short-term obligations are covered.",
  },
  liquidity: {
    name: "Liquidity Filter",
    formula: "Market Cap \u2265 $300M AND Avg Daily Volume \u2265 $1M AND History \u2265 5 years",
    source: "Standard institutional thresholds",
    interpretation: "Ensures adequate trading liquidity and data history.",
  },
  // Quality sub-factors
  gross_profitability: {
    name: "Gross Profitability",
    formula: "(Revenue \u2212 COGS) / Total Assets",
    source: "Novy-Marx (2013)",
    interpretation: "Higher is better. Measures asset efficiency of gross profit generation.",
  },
  roic_wacc_spread: {
    name: "ROIC\u2013WACC Spread",
    formula: "ROIC \u2212 WACC",
    source: "Mauboussin & Callahan (2014)",
    interpretation: "Positive = creating shareholder value. Wider spread = stronger moat.",
  },
  earnings_quality: {
    name: "Sloan Accrual Ratio",
    formula: "(Net Income \u2212 CFO \u2212 CFI) / Total Assets",
    source: "Sloan (1996)",
    interpretation: "Lower is better. Negative = cash earnings exceed reported earnings.",
  },
  piotroski_f_score: {
    name: "Piotroski F-Score",
    formula: "Sum of 9 binary signals (profitability, leverage, operating efficiency)",
    source: "Piotroski (2000)",
    interpretation: "Score 0\u20139. Higher signals stronger financial health. \u22657 is strong.",
  },
  // Value sub-factors
  ev_fcf: {
    name: "EV/FCF",
    formula: "Enterprise Value / Free Cash Flow",
    source: "Standard valuation metric",
    interpretation: "Lower is better. Measures how cheaply you buy each dollar of cash flow.",
  },
  shareholder_yield: {
    name: "Shareholder Yield",
    formula: "Dividend Yield + Buyback Yield \u2212 Net Debt Issuance Yield",
    source: "Mebane Faber (2013)",
    interpretation: "Higher is better. Total cash return to shareholders.",
  },
  dcf_margin_of_safety: {
    name: "DCF Margin of Safety",
    formula: "(Intrinsic Value \u2212 Current Price) / Intrinsic Value",
    source: "Graham & Dodd (1934)",
    interpretation: "Higher is better. Buffer between price paid and estimated fair value.",
  },
  acquirers_multiple: {
    name: "Acquirer\u2019s Multiple",
    formula: "Enterprise Value / Operating Earnings",
    source: "Tobias Carlisle (2014)",
    interpretation: "Lower is better. Finds statistically cheap stocks an acquirer would buy.",
  },
  // Momentum sub-factors
  price_momentum: {
    name: "12-1 Month Price Momentum",
    formula: "(Price\u2081\u2082 \u2212 Price\u2081) / Price\u2081, excluding most recent month",
    source: "Jegadeesh & Titman (1993)",
    interpretation: "Higher is better. Captures intermediate-term trend strength.",
  },
  earnings_momentum: {
    name: "Standardized Unexpected Earnings (SUE)",
    formula: "(EPS_actual \u2212 EPS_estimate) / Std Dev of surprises",
    source: "Latan\u00E9 & Jones (1977)",
    interpretation: "Higher is better. Measures magnitude of earnings surprise.",
  },
  insider_cluster_buying: {
    name: "Insider Cluster Buying",
    formula: "\u22653 unique insiders buying within 30 days",
    source: "Lakonishok & Lee (2001)",
    interpretation: "Cluster buying is a stronger signal than individual insider trades.",
  },
  institutional_accumulation: {
    name: "Institutional Accumulation",
    formula: "Net shares added by curated 13F filers / Shares outstanding",
    source: "13F filing analysis",
    interpretation: "Positive accumulation by top funds signals institutional confidence.",
  },
  // Conviction Engine
  asymmetry_ratio: {
    name: "Asymmetry Ratio",
    formula: "Upside to Intrinsic Value / Downside to Stop Loss",
    source: "Kelly Criterion adaptation",
    interpretation: "Higher is better. \u22653:1 is favorable risk-reward.",
  },
  max_position_pct: {
    name: "Max Position %",
    formula: "f* = (p\u00B7b \u2212 q) / b, capped at Kelly fraction",
    source: "Kelly (1956)",
    interpretation: "Suggested max allocation. Higher conviction = larger position allowed.",
  },
  // Valuation methods
  dcf_valuation: {
    name: "DCF Valuation",
    formula: "Sum of discounted future FCFs + Terminal Value",
    source: "Standard DCF model",
    interpretation:
      "Most comprehensive but sensitive to growth and discount rate assumptions.",
  },
  ev_fcf_valuation: {
    name: "EV/FCF Implied Value",
    formula: "FCF \u00D7 Sector Median EV/FCF Multiple",
    source: "Relative valuation",
    interpretation: "What the stock would be worth at sector-average multiples.",
  },
  ev_ebit_valuation: {
    name: "EV/EBIT Implied Value",
    formula: "EBIT \u00D7 Sector Median EV/EBIT Multiple",
    source: "Relative valuation",
    interpretation: "Operating earnings-based valuation, less sensitive to capex policy.",
  },
  shareholder_yield_valuation: {
    name: "Shareholder Yield Implied Value",
    formula: "Total Shareholder Yield / Sector Median Yield",
    source: "Yield-based valuation",
    interpretation: "Prices the stock relative to sector cash return expectations.",
  },
}
