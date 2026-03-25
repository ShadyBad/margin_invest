"use client"

import { motion } from "framer-motion"
import { PickHeroCard } from "./pick-hero-card"
import { PickMediumCard } from "./pick-medium-card"
import { PickCompactRow } from "./pick-compact-row"
import { EmptyState } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

const cardVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      delay: i * 0.06,
      ease: [0.22, 1, 0.36, 1] as const,
    },
  }),
}

interface TieredPicksListProps {
  picks: PickSummary[]
  className?: string
  totalScored?: number
  universeSize?: number
}

export function TieredPicksList({
  picks,
  className = "",
  totalScored,
  universeSize,
}: TieredPicksListProps) {
  const sorted = [...picks].sort(
    (a, b) => b.score - a.score,
  )

  if (sorted.length === 0) {
    const hasStats =
      totalScored != null && universeSize != null && universeSize > 0
    return (
      <EmptyState
        title="The system is working"
        description={
          hasStats
            ? `${totalScored.toLocaleString()} of ${universeSize.toLocaleString()} equities were scored. None met the scoring threshold. When high-scoring opportunities emerge, they'll appear here.`
            : "It found nothing worth your capital right now. When high-scoring opportunities emerge, they'll appear here."
        }
        className={className}
      />
    )
  }

  const heroPick = sorted[0]
  const mediumPicks = sorted.slice(1, 3)
  const compactPicks = sorted.slice(3)

  return (
    <div className={`space-y-4 ${className}`} data-testid="tiered-picks-list">
      {/* Tier 1: Hero */}
      <motion.div
        custom={0}
        initial="hidden"
        animate="visible"
        variants={cardVariants}
      >
        <PickHeroCard pick={heroPick} rank={1} />
      </motion.div>

      {/* Tier 2: Medium cards */}
      {mediumPicks.length > 0 && (
        <div
          className={
            mediumPicks.length === 1
              ? "max-w-lg"
              : "grid grid-cols-1 md:grid-cols-2 gap-4"
          }
        >
          {mediumPicks.map((pick, i) => (
            <motion.div
              key={pick.ticker}
              custom={i + 1}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <PickMediumCard pick={pick} rank={i + 2} />
            </motion.div>
          ))}
        </div>
      )}

      {/* Tier 3: Compact rows */}
      {compactPicks.length > 0 && (
        <div className="space-y-0.5">
          {compactPicks.map((pick, i) => (
            <motion.div
              key={pick.ticker}
              custom={i + 3}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <PickCompactRow pick={pick} rank={i + 4} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
