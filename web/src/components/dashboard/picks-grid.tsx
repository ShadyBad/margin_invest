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
}

export function PicksGrid({ picks, className = "" }: PicksGridProps) {
  const sorted = [...picks].sort(
    (a, b) => b.composite_percentile - a.composite_percentile,
  )

  if (sorted.length === 0) {
    return (
      <EmptyState
        title="No picks yet"
        description="Scored stocks with exceptional or high conviction will appear here."
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
        >
          <StockCard pick={pick} />
        </motion.div>
      ))}
    </div>
  )
}
