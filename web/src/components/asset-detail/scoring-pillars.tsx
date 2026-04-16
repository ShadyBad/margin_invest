import { PillarCard } from "./pillar-card"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface ScoringPillarsProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  growthStage?: string | null
}

function formatGrowthStage(stage: string): string {
  return stage.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

function getWeightLabel(q: number, v: number, m: number): string {
  return `Q:${Math.round(q * 100)}% \u00B7 V:${Math.round(v * 100)}% \u00B7 M:${Math.round(m * 100)}%`
}

export function ScoringPillars({
  quality,
  value,
  momentum,
  growthStage,
}: ScoringPillarsProps) {
  const weightLabel = getWeightLabel(quality.weight, value.weight, momentum.weight)

  return (
    <section data-testid="scoring-pillars" className="space-y-4">
      <div>
        <h2
          className="text-label-sm"
          style={{ color: "var(--color-on-surface-variant)" }}
        >
          SCORING BREAKDOWN
        </h2>
        <p
          className="text-body-md mt-1"
          style={{ color: "var(--color-on-surface-variant)" }}
        >
          Weighted by growth stage:{" "}
          {growthStage ? formatGrowthStage(growthStage) : "Default"} ({weightLabel})
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <PillarCard pillar={quality} />
        <PillarCard pillar={value} />
        <PillarCard pillar={momentum} />
      </div>
    </section>
  )
}
