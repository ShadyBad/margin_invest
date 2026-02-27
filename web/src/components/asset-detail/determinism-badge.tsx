"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

export function DeterminismBadge() {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div className="relative inline-flex">
      <div
        data-testid="determinism-badge"
        className="inline-flex items-center px-3 py-1.5 rounded border border-white/[0.06] bg-white/[0.02] cursor-help text-[10px] font-mono text-text-tertiary"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        ⬡ Deterministic — same inputs produce this exact output. No human override.
      </div>

      <AnimatePresence>
        {showTooltip && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full mt-1 z-50 w-72 p-2.5 text-[10px] text-text-secondary rounded-lg border border-border-primary shadow-lg"
            style={{ background: "var(--color-bg-elevated)" }}
            role="tooltip"
          >
            This score was computed algorithmically with zero human intervention. The same financial
            data inputs will always produce this exact same score, percentile, and signal.
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
