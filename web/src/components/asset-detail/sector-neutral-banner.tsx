"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

interface SectorNeutralBannerProps {
  sectorName: string
  sectorCode?: string
}

export function SectorNeutralBanner({ sectorName, sectorCode }: SectorNeutralBannerProps) {
  const [showWhy, setShowWhy] = useState(false)

  return (
    <div
      data-testid="sector-neutral-banner"
      className="flex items-start px-3 py-2 rounded border border-white/[0.06] bg-white/[0.02] text-[10px] text-text-secondary"
    >
      <span className="text-accent mr-1.5">○</span>
      <span>
        Sector-neutral scoring: all factors ranked within{" "}
        <span className="text-text-primary font-medium">{sectorName}</span>
        {sectorCode && (
          <>
            {" "}
            <span className="text-text-tertiary font-mono">(GICS {sectorCode})</span>
          </>
        )}{" "}
        before cross-sector combination.{" "}
        <span className="relative inline-block">
          <span
            className="text-accent cursor-help underline decoration-dotted underline-offset-2"
            onMouseEnter={() => setShowWhy(true)}
            onMouseLeave={() => setShowWhy(false)}
          >
            Why?
          </span>
          <AnimatePresence>
            {showWhy && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.15 }}
                className="absolute left-0 top-full mt-1 z-50 w-72 p-2.5 text-[10px] text-text-secondary rounded-lg border border-border-primary shadow-lg"
                style={{ background: "var(--color-bg-elevated)" }}
                role="tooltip"
              >
                Sector-neutral ranking ensures fair comparison within peer groups. Comparing a tech
                company&#39;s ROIC to a utility&#39;s ROIC is meaningless — percentiles are computed
                within each sector first, then combined.
              </motion.div>
            )}
          </AnimatePresence>
        </span>
      </span>
    </div>
  )
}
