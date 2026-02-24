/**
 * Maps sub-factor API names to their formulas and academic sources.
 * Used by PillarCard to show inline formulas for verification.
 */
export const SUB_FACTOR_FORMULAS: Record<string, { formula: string; source: string }> = {
  // Quality
  gross_profitability: {
    formula: "(Revenue - COGS) / Total Assets",
    source: "Novy-Marx (2013)",
  },
  roic_wacc_spread: {
    formula: "NOPAT / Invested Capital - WACC",
    source: "Mauboussin (2014)",
  },
  earnings_quality: {
    formula: "(Net Income - CFO) / Total Assets",
    source: "Sloan (1996)",
  },
  piotroski_f_score: {
    formula: "9-signal composite (ROA, CFO, leverage, liquidity, margin, turnover)",
    source: "Piotroski (2000)",
  },
  // Value
  ev_fcf: {
    formula: "(Market Cap + Debt - Cash) / (CFO - CapEx)",
    source: "Greenblatt (2006)",
  },
  shareholder_yield: {
    formula: "(Dividends + Net Buybacks) / Market Cap",
    source: "Faber (2013)",
  },
  dcf_margin_of_safety: {
    formula: "(Intrinsic Value - Price) / Intrinsic Value",
    source: "Klarman (1991)",
  },
  acquirers_multiple: {
    formula: "Enterprise Value / EBIT",
    source: "Carlisle (2014)",
  },
  // Momentum
  price_momentum: {
    formula: "(Price_now / Price_12mo_ago) - 1, skip last month",
    source: "Jegadeesh & Titman (1993)",
  },
  earnings_momentum: {
    formula: "(Actual EPS - Expected EPS) / StdDev(surprises)",
    source: "Foster, Olsen & Shevlin (1984)",
  },
  insider_cluster_buying: {
    formula: "3+ distinct insiders buying within 90 days, weighted by role",
    source: "Lakonishok & Lee (2001)",
  },
  institutional_accumulation: {
    formula: "Net new positions from curated 13F filers",
    source: "Cohen, Polk & Silli (2010)",
  },
}
