import { PercentileBar } from "@/components/ui"
import { formatAttributeLabel } from "@/lib/format"
import { getFactorInterpretation } from "@/lib/score-interpretation"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface FactorBreakdownProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  capitalAllocation?: FactorBreakdownResponse | null
  catalyst?: FactorBreakdownResponse | null
  winningTrack?: string | null
  showAllFactors?: boolean
  className?: string
}

interface FactorSectionProps {
  factor: FactorBreakdownResponse
}

function FactorSection({ factor }: FactorSectionProps) {
  return (
    <div
      className="pb-6 border-b border-border-primary/30 last:border-b-0 last:pb-0"
      data-testid={`factor-section-${factor.factor_name.toLowerCase()}`}
    >
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-text-primary">
          {factor.factor_name.charAt(0).toUpperCase() + factor.factor_name.slice(1).replace("_", " ")}
        </h4>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-text-tertiary">
            {(factor.weight * 100).toFixed(0)}%
          </span>
          <span className="text-lg font-mono font-bold text-accent">
            {factor.average_percentile.toFixed(0)}
          </span>
        </div>
      </div>
      <p className="text-xs text-text-tertiary leading-relaxed mb-3">
        {getFactorInterpretation(factor.factor_name, factor.average_percentile)}
      </p>
      <div className="space-y-2.5">
        {factor.sub_scores.map((sub) => (
          <PercentileBar
            key={sub.name}
            value={sub.percentile_rank}
            label={formatAttributeLabel(sub.name)}
            showValue
          />
        ))}
      </div>
    </div>
  )
}

export function FactorBreakdown({
  quality, value, momentum,
  capitalAllocation, catalyst,
  winningTrack, showAllFactors = false,
  className = "",
}: FactorBreakdownProps) {
  let factors: FactorBreakdownResponse[]

  if (showAllFactors || !winningTrack) {
    // Data view or v1: show all
    factors = [quality, value, momentum]
    if (capitalAllocation) factors.push(capitalAllocation)
    if (catalyst) factors.push(catalyst)
  } else if (winningTrack === "compounder") {
    factors = [quality, value]
    if (capitalAllocation) factors.push(capitalAllocation)
  } else {
    // mispricing
    factors = [value, quality]
    if (catalyst) factors.push(catalyst)
  }

  return (
    <div className={`space-y-5 ${className}`} data-testid="factor-breakdown">
      <h3 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary">
        Factor Breakdown
        {winningTrack && !showAllFactors && (
          <span className="text-xs font-normal text-text-secondary ml-2">
            ({winningTrack === "compounder" ? "Compounder" : "Mispricing"} Track)
          </span>
        )}
      </h3>
      <div className="space-y-5">
        {factors.map((factor) => (
          <FactorSection key={factor.factor_name} factor={factor} />
        ))}
      </div>
    </div>
  )
}
