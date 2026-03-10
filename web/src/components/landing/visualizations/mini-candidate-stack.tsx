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

  return (
    <div className={className}>
      <div className="flex flex-col gap-3">
        {cards.map((card, i) => (
          <div
            key={card.ticker}
            data-candidate-card={card.ticker}
            className="border border-border-subtle rounded-lg bg-bg-elevated p-4 transition-all duration-200 hover:border-accent/40 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(26,122,90,0.1)]"
            style={{
              marginLeft: `${i * 12}px`,
              opacity: i === 0 ? 1 : 0.85 - i * 0.1,
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
        ))}
      </div>
    </div>
  )
}
