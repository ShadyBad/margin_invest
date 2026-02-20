"use client"

import type { UniverseSummary, Warning } from "@/lib/api/types"

interface IngestionBannerProps {
  universe: UniverseSummary
  warnings?: Warning[]
}

export function IngestionBanner({ universe }: IngestionBannerProps) {
  if (universe.is_complete) return null

  const coverage = Math.round(universe.scoring_coverage * 100)

  return (
    <div
      className="rounded-sm px-4 py-3 mb-6 text-sm bg-warning/10 border border-warning/30 text-warning"
      role="status"
    >
      {coverage > 0
        ? `Scoring in progress — ${coverage}% of universe scored. Rankings may shift as more data arrives.`
        : "Scoring in progress. Results will appear as data is processed."}
    </div>
  )
}
