"use client"

import type { UniverseSummary, Warning } from "@/lib/api/types"

interface IngestionBannerProps {
  universe: UniverseSummary
  warnings?: Warning[]
}

export function IngestionBanner({ universe }: IngestionBannerProps) {
  if (universe.is_complete) return null

  const coverage = Math.round(universe.scoring_coverage * 100)
  const isLow = universe.scoring_coverage < 0.5

  return (
    <div
      className={`rounded-sm px-4 py-3 mb-6 text-sm ${
        isLow
          ? "bg-danger/10 border border-danger/30 text-danger"
          : "bg-warning/10 border border-warning/30 text-warning"
      }`}
      role="alert"
    >
      {isLow
        ? "Universe coverage too low for reliable rankings. Ingestion in progress."
        : `Data ingestion in progress — ${coverage}% of universe scored. Rankings may shift.`}
    </div>
  )
}
