import { FactorRow } from "./factor-row"
import { getFactorInterpretation } from "@/lib/score-interpretation"
import { formatAttributeLabel } from "@/lib/format"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface PanelFactorBreakdownProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  capitalAllocation?: FactorBreakdownResponse | null
  catalyst?: FactorBreakdownResponse | null
  winningTrack?: string | null
}

export function PanelFactorBreakdown({
  quality,
  value,
  momentum,
  capitalAllocation,
  catalyst,
  winningTrack,
}: PanelFactorBreakdownProps) {
  let factors: FactorBreakdownResponse[] = [quality, value, momentum]
  if (capitalAllocation) factors.push(capitalAllocation)
  if (catalyst) factors.push(catalyst)

  // Sort by weight descending
  factors = [...factors].sort((a, b) => b.weight - a.weight)

  const trackLabel = winningTrack === "compounder"
    ? "Compounder"
    : winningTrack === "mispricing"
      ? "Mispricing"
      : null

  return (
    <div data-testid="panel-factor-breakdown">
      <div className="flex items-center justify-between px-6 py-3">
        <h3 className="text-[16px] font-semibold text-[#E8E6E3]">Factor Breakdown</h3>
        {trackLabel && (
          <span
            className={`text-xs px-2 py-0.5 rounded font-medium ${
              winningTrack === "compounder"
                ? "bg-[#1A7A5A]/10 text-[#1A7A5A]"
                : "bg-purple-500/10 text-purple-400"
            }`}
          >
            {trackLabel}
          </span>
        )}
      </div>
      <div>
        {factors.map((factor) => (
          <FactorRow
            key={factor.factor_name}
            name={factor.factor_name.charAt(0).toUpperCase() + factor.factor_name.slice(1).replace(/_/g, " ")}
            weight={Math.round(factor.weight * 100)}
            score={factor.average_percentile}
            interpretation={getFactorInterpretation(factor.factor_name, factor.average_percentile)}
            subScores={factor.sub_scores.map((s) => ({
              label: formatAttributeLabel(s.name),
              value: s.percentile_rank,
            }))}
          />
        ))}
      </div>
    </div>
  )
}
