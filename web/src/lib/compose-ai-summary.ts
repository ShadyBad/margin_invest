import type { ScoreResponse } from "@/lib/api/types"

export interface AiSummaryResult {
  summary: string
  confidence: number
}

function factorStrength(percentile: number): string {
  if (percentile >= 80) return "strong"
  if (percentile >= 60) return "above-average"
  if (percentile >= 40) return "moderate"
  return "weak"
}

export function composeAiSummary(score: ScoreResponse): AiSummaryResult {
  const factors = [
    { name: "quality", p: score.quality.average_percentile },
    { name: "value", p: score.value.average_percentile },
    { name: "momentum", p: score.momentum.average_percentile },
  ]

  const sorted = [...factors].sort((a, b) => b.p - a.p)
  const strongest = sorted[0]
  const weakest = sorted[sorted.length - 1]

  const parts: string[] = []

  if (score.winning_track) {
    const track = score.winning_track === "compounder" ? "compounder" : "mispricing"
    parts.push(
      `${score.ticker} scores as a ${track} candidate with ${factorStrength(strongest.p)} ${strongest.name}.`,
    )
  } else {
    parts.push(
      `${score.ticker} demonstrates ${factorStrength(strongest.p)} ${strongest.name} characteristics.`,
    )
  }

  if (weakest.p < 50) {
    parts.push(
      `${weakest.name.charAt(0).toUpperCase() + weakest.name.slice(1)} is a relative weak point at the ${Math.round(weakest.p)}th percentile.`,
    )
  } else {
    parts.push(`All core factors rank above median, indicating broad strength.`)
  }

  const avg = factors.reduce((s, f) => s + f.p, 0) / factors.length
  const spread = Math.max(...factors.map((f) => f.p)) - Math.min(...factors.map((f) => f.p))
  const confidence = Math.round(Math.min(100, Math.max(0, avg * 0.7 + (100 - spread) * 0.3)))

  return {
    summary: parts.join(" "),
    confidence,
  }
}
