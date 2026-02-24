interface FilterMeta {
  displayName: string
  technicalName: string
  formula: string | null
  whyItMatters: string
  citation: string
}

export const FILTER_METADATA: Record<string, FilterMeta> = {
  liquidity: {
    displayName: "Liquidity",
    technicalName: "Market Cap & Position Sizing",
    formula: null,
    whyItMatters:
      "Illiquid stocks cannot be traded efficiently. Small market caps mean wide spreads, high slippage, and difficulty exiting positions.",
    citation: "Amihud (2002), Illiquidity and Stock Returns",
  },
  beneish_m_score: {
    displayName: "Earnings Quality",
    technicalName: "Beneish M-Score",
    formula: "8-variable composite (DSRI, GMI, AQI, SGI, DEPI, SGAI, accruals, leverage)",
    whyItMatters:
      "The Beneish M-Score detects earnings manipulation. Companies with scores above -2.22 have a high probability of manipulating reported earnings.",
    citation: "Beneish (1999), The Detection of Earnings Manipulation",
  },
  altman_z_score: {
    displayName: "Financial Distress",
    technicalName: "Altman Z-Score",
    formula: "6.56(WC/TA) + 3.26(RE/TA) + 6.72(EBIT/TA) + 1.05(Equity/TL)",
    whyItMatters:
      "The Altman Z-Score predicts bankruptcy probability. Scores below 1.1 indicate a company in the financial distress zone.",
    citation: "Altman (1968), Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy",
  },
  current_ratio: {
    displayName: "Short-Term Liquidity",
    technicalName: "Current Ratio",
    formula: "Current Assets / Current Liabilities",
    whyItMatters:
      "A low current ratio means the company may struggle to pay short-term obligations. Thresholds are sector-adjusted to account for capital-intensive industries.",
    citation: "Beaver (1966), Financial Ratios As Predictors of Failure",
  },
  fcf_distress: {
    displayName: "Cash Flow Health",
    technicalName: "Free Cash Flow Distress",
    formula: null,
    whyItMatters:
      "Persistent negative free cash flow means the company is burning cash. This increases dilution risk and limits capital return to shareholders.",
    citation: "Richardson et al. (2005), Accrual Reliability, Earnings Persistence and Stock Prices",
  },
  interest_coverage: {
    displayName: "Debt Service",
    technicalName: "Interest Coverage Ratio",
    formula: "EBIT / Interest Expense",
    whyItMatters:
      "Low interest coverage means the company barely earns enough to service its debt. This increases default risk, especially during economic downturns.",
    citation: "Ohlson (1980), Financial Ratios and the Probabilistic Prediction of Bankruptcy",
  },
}
