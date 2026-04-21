import { PillarCard } from "./pillar-card"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface ScoringPillarsProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
}

export function ScoringPillars({
  quality,
  value,
  momentum,
}: ScoringPillarsProps) {
  return (
    <section data-testid="scoring-pillars" className="space-y-4">
      <h2
        className="text-label-sm"
        style={{ color: "var(--color-on-surface-variant)" }}
      >
        SCORING BREAKDOWN
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <PillarCard pillar={quality} />
        <PillarCard pillar={value} />
        <PillarCard pillar={momentum} />
      </div>
    </section>
  )
}
