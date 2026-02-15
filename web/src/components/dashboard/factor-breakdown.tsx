import { PercentileBar } from "@/components/ui"
import { formatAttributeLabel } from "@/lib/format"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface FactorBreakdownProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  className?: string
}

interface FactorSectionProps {
  factor: FactorBreakdownResponse
}

function FactorSection({ factor }: FactorSectionProps) {
  return (
    <div data-testid={`factor-section-${factor.factor_name.toLowerCase()}`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-text-primary capitalize">
          {factor.factor_name}
        </h4>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-secondary">
            Weight: {(factor.weight * 100).toFixed(0)}%
          </span>
          <span className="text-sm font-mono font-bold text-accent">
            {factor.average_percentile.toFixed(0)}
          </span>
        </div>
      </div>
      <div className="space-y-1.5">
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

export function FactorBreakdown({ quality, value, momentum, className = "" }: FactorBreakdownProps) {
  const factors = [quality, value, momentum]

  return (
    <div className={`space-y-4 ${className}`} data-testid="factor-breakdown">
      <h3 className="text-base font-semibold text-text-primary">
        Factor Breakdown
      </h3>
      <div className="space-y-5">
        {factors.map((factor) => (
          <FactorSection key={factor.factor_name} factor={factor} />
        ))}
      </div>
    </div>
  )
}
