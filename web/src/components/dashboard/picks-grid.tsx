"use client"

import { TieredPicksList } from "./tiered-picks-list"
import type { PickSummary } from "@/lib/api/types"

interface PicksGridProps {
  picks: PickSummary[]
  className?: string
  totalScored?: number
  universeSize?: number
}

export function PicksGrid({ picks, className, totalScored, universeSize }: PicksGridProps) {
  return (
    <TieredPicksList
      picks={picks}
      className={className}
      totalScored={totalScored}
      universeSize={universeSize}
    />
  )
}
