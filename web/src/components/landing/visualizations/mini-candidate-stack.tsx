/**
 * MiniCandidateStack -- Vertical bar chart showing candidates sorted by score.
 *
 * Bars scale by composite score, sorted ascending (lowest → highest).
 * Ticker label below each bar, score above. Uses accent color with
 * terminal-card design language.
 *
 * Used in: Pipeline section (Step 10).
 */

import type { CandidateCard } from "../shared/types"
import { formatScore } from "@/lib/format"

interface MiniCandidateStackProps {
  candidates: CandidateCard[]
  className?: string
}

const MAX_BAR_HEIGHT = 140

export function MiniCandidateStack({ candidates, className }: MiniCandidateStackProps) {
  const sorted = [...candidates].sort((a, b) => a.score - b.score)

  if (sorted.length === 0) {
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

  const maxScore = Math.max(...sorted.map((c) => c.score), 1)

  return (
    <div className={className}>
      <div
        className="flex items-end justify-center gap-3"
        style={{ height: MAX_BAR_HEIGHT + 48 }}
      >
        {sorted.map((card) => {
          const barHeight = Math.max(16, (card.score / maxScore) * MAX_BAR_HEIGHT)
          const opacity = 0.4 + (card.score / maxScore) * 0.6

          return (
            <div
              key={card.ticker}
              className="flex flex-col items-center gap-1.5"
              data-candidate-card={card.ticker}
            >
              {/* Score above bar */}
              <span className="font-mono text-[11px] font-semibold text-accent tabular-nums">
                {formatScore(card.score)}
              </span>

              {/* Bar */}
              <div
                className="w-10 rounded-t transition-all duration-500 ease-out"
                style={{
                  height: barHeight,
                  background: `linear-gradient(to top, var(--color-accent) 0%, color-mix(in srgb, var(--color-accent) 60%, transparent) 100%)`,
                  opacity,
                }}
              />

              {/* Ticker below bar */}
              <span className="font-mono text-[10px] font-bold text-text-secondary tracking-wider">
                {card.ticker}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
