"use client"

import Link from "next/link"
import { FactorSignature } from "@/components/visualizations/factor-signature"
import { ConvictionBadge } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"
import { formatScore } from "@/lib/format"

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
      className="flex items-center gap-4 px-4 py-3 rounded-lg transition-colors duration-150"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
      }}
      data-testid={`pick-compact-${pick.ticker}`}
    >
      <span
        className="text-[17px] font-bold w-12 text-right tabular-nums shrink-0"
        style={{ color: getTierColor(pick.composite_tier), fontFamily: "var(--font-data)" }}
      >
        {formatScore(pick.score)}
      </span>
      <span className="font-bold w-20 shrink-0" style={{ color: "var(--color-on-surface)" }}>{pick.ticker}</span>
      <span className="text-sm truncate flex-1 min-w-0" style={{ color: "var(--color-on-surface-variant)" }}>
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
