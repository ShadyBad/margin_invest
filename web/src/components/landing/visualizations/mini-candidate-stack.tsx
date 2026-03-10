/**
 * MiniCandidateStack -- 3 stacked mini candidate cards with depth offset.
 *
 * Shows top 3 candidates as terminal-style cards, each offset 8px right
 * and 8px down from the previous, creating a visual stack/depth effect.
 *
 * Used in: Pipeline section (Step 10).
 */

import type { CandidateCard } from "../shared/types"

interface MiniCandidateStackProps {
  candidates: CandidateCard[]
  className?: string
}

export function MiniCandidateStack({ candidates, className }: MiniCandidateStackProps) {
  const cards = candidates.slice(0, 3)

  if (cards.length === 0) {
    return (
      <div className={className}>
        <div className="flex items-center justify-center h-full min-h-[120px]">
          <span className="font-mono text-xs text-text-tertiary">
            loads after scoring cycle
          </span>
        </div>
      </div>
    )
  }

  // Render back-to-front: last card first in DOM, first card last (highest z via later DOM order).
  // Cards offset 8px right and 8px down from each other to create depth.
  const reversed = [...cards].reverse()

  return (
    <div className={className}>
      <div className="relative" style={{ minHeight: `${120 + (cards.length - 1) * 8}px` }}>
        {reversed.map((card, i) => {
          // i=0 is the back-most card, i=reversed.length-1 is the front card
          const zIndex = i + 1
          // Back cards have higher offset (peeking out behind), front card at 0
          const offset = (reversed.length - 1 - i) * 8

          return (
            <div
              key={card.ticker}
              data-candidate-card={card.ticker}
              className="absolute border border-border-subtle rounded-lg bg-bg-elevated p-4 w-full max-w-[240px]"
              style={{
                top: `${offset}px`,
                left: `${offset}px`,
                zIndex,
                opacity: i === reversed.length - 1 ? 1 : 0.7 + i * 0.1,
              }}
            >
              <div className="flex items-baseline justify-between mb-2">
                <span className="font-mono text-sm font-bold text-text-primary">
                  {card.ticker}
                </span>
                <span className="font-mono text-sm text-accent">
                  {card.score.toFixed(1)}
                </span>
              </div>
              <span className="inline-block text-[10px] font-mono uppercase tracking-wider text-text-tertiary bg-bg-subtle px-2 py-0.5 rounded">
                {card.sector}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
