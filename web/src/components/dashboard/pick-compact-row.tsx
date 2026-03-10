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

interface PickCompactRowProps {
  pick: PickSummary
  rank: number
}

export function PickCompactRow({ pick }: PickCompactRowProps) {
  return (
    <Link
      href={`/asset/${pick.ticker}`}
      className="flex items-center gap-4 px-4 py-3 rounded-lg bg-bg-elevated transition-colors duration-150 hover:bg-bg-subtle"
      style={{ border: "1px solid rgba(237,233,227,0.04)" }}
      data-testid={`pick-compact-${pick.ticker}`}
    >
      <span
        className="font-mono text-[20px] font-bold w-10 text-right tabular-nums"
        style={{ color: getTierColor(pick.composite_tier) }}
      >
        {Math.round(pick.score)}
      </span>
      <span className="font-bold text-text-primary w-16">{pick.ticker}</span>
      <span className="text-sm text-text-secondary truncate flex-1 min-w-0">
        {pick.name}
      </span>
      <FactorSignature
        factors={{
          quality: pick.quality_percentile,
          value: pick.value_percentile,
          momentum: pick.momentum_percentile,
          sentiment: pick.sentiment_percentile ?? null,
          growth: pick.growth_percentile ?? null,
        }}
        variant="inline"
      />
      <ConvictionBadge level={pick.composite_tier} />
    </Link>
  )
}
