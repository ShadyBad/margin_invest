const FACTOR_DESCRIPTORS: Record<string, { high: string; low: string }> = {
  quality: { high: "Strong ROE, consistent margins, low debt", low: "Weak profitability or high leverage" },
  value: { high: "Undervalued vs sector peers on FCF and earnings", low: "Trading at premium valuation" },
  momentum: { high: "Strong uptrend across multiple timeframes", low: "Weak or declining price action" },
  capital_allocation: { high: "Efficient capital deployment", low: "Suboptimal capital allocation" },
  catalyst: { high: "Strong catalysts identified", low: "Limited near-term catalysts" },
}

export function getFactorInterpretation(
  factorName: string,
  percentile: number,
  sector?: string,
): string {
  const descriptor = FACTOR_DESCRIPTORS[factorName.toLowerCase()]
  const sectorLabel = sector ? ` in ${sector}` : ""
  const rank = 100 - Math.round(percentile)

  if (percentile >= 90) {
    return `Top ${rank}%${sectorLabel}. ${descriptor?.high ?? "Exceptional across metrics."}`
  }
  if (percentile >= 70) {
    return `Top ${rank}%${sectorLabel}. ${descriptor?.high ?? "Strong performance."}`
  }
  if (percentile >= 50) {
    return `Middle of the pack${sectorLabel}. Room for improvement.`
  }
  if (percentile >= 30) {
    return `Below average${sectorLabel}. ${descriptor?.low ?? "Underperforming peers."}`
  }
  return `Bottom ${Math.round(percentile)}%${sectorLabel}. ${descriptor?.low ?? "Significant weakness."}`
}
