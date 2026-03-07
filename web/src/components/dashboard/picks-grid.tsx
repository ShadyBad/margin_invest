"use client"

import { motion } from "framer-motion"
import { StockCard } from "./stock-card"
import { EmptyState } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

const cardVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] as const },
  }),
}

interface PicksGridProps {
  picks: PickSummary[]
  className?: string
  totalScored?: number
  universeSize?: number
}

export function PicksGrid({ picks, className = "", totalScored, universeSize }: PicksGridProps) {
  const sorted = [...picks].sort(
    (a, b) => b.composite_percentile - a.composite_percentile,
  )

  if (sorted.length === 0) {
    const hasStats = totalScored != null && universeSize != null && universeSize > 0
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

  return (
    <div
      className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 ${className}`}
      data-testid="picks-grid"
    >
      {sorted.map((pick, index) => (
        <motion.div
          key={pick.ticker}
          custom={index}
          initial="hidden"
          animate="visible"
          variants={cardVariants}
          className={index === 0 && sorted.length > 3 ? "md:col-span-2 lg:col-span-1" : ""}
        >
          <StockCard pick={pick} rank={index + 1} />
        </motion.div>
      ))}
    </div>
  )
}
