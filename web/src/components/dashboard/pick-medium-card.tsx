"use client"

import Link from "next/link"
import { FactorSignature } from "@/components/visualizations/factor-signature"
import { ConvictionBadge } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

function getTierColor(tier: string): string {
  switch (tier) {
    case "exceptional":
      return "var(--color-percentile-exceptional)"
    case "high":
      return "var(--color-percentile-strong)"
    case "medium":
      return "var(--color-percentile-average)"
    case "low":
    case "below":
      return "var(--color-percentile-below)"
    default:
      return "var(--color-text-primary)"
  }
}

interface PickMediumCardProps {
  pick: PickSummary
  rank: number
}

export function PickMediumCard({ pick, rank }: PickMediumCardProps) {
  return (
    <Link
      href={`/asset/${pick.ticker}`}
      className="block bg-bg-elevated rounded-xl p-5 transition-all duration-200 hover:border-[var(--color-accent-medium)]"
      style={{ border: "1px solid rgba(237,233,227,0.06)" }}
      data-testid={`pick-medium-${pick.ticker}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-tertiary font-mono">#{rank}</span>
          <h3 className="text-lg font-bold text-text-primary">{pick.ticker}</h3>
        </div>
        <ConvictionBadge level={pick.composite_tier} />
      </div>
      <div className="mb-3">
        <span
          className="font-mono text-[28px] font-bold leading-none tracking-tight"
          style={{ color: getTierColor(pick.composite_tier) }}
        >
          {Math.round(pick.score)}
        </span>
      </div>
      <FactorSignature
        factors={{
          quality: pick.quality_percentile,
          value: pick.value_percentile,
          momentum: pick.momentum_percentile,
          sentiment: pick.sentiment_percentile ?? null,
          growth: pick.growth_percentile ?? null,
        }}
        variant="mini"
      />
    </Link>
  )
}
