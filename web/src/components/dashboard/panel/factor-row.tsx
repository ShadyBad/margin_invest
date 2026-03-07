import { SubScoreChips } from "./sub-score-chips"
import { getPercentileColor } from "./utils"

interface FactorRowProps {
  name: string
  weight: number
  score: number
  interpretation: string
  subScores: { label: string; value: number }[]
}

export function FactorRow({ name, weight, score, interpretation, subScores }: FactorRowProps) {
  const color = getPercentileColor(score)

  return (
    <div
      className="py-4 border-b border-border-subtle last:border-b-0 hover:bg-surface-overlay transition-colors duration-200 px-6"
      data-testid={`factor-row-${name.toLowerCase()}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[14px] font-medium text-text-primary">{name}</span>
        <div className="flex items-center gap-3">
          <span className="text-[12px] font-mono text-text-tertiary">{weight}%</span>
          <span
            className="text-[24px] font-display leading-none"
            style={{ color }}
            data-testid="factor-score"
          >
            {Math.round(score)}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-3 mb-2">
        <div className="flex-1 h-1 rounded-full bg-border-subtle" data-testid="factor-progress-bar">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${score}%`, backgroundColor: color }}
          />
        </div>
        <span className="text-[12px] text-text-tertiary shrink-0 max-w-[200px] truncate">
          {interpretation}
        </span>
      </div>
      <SubScoreChips subScores={subScores} />
    </div>
  )
}
