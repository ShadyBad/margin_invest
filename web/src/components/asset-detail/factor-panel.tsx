/**
 * FactorPanel — Combined factor bars and radar chart display.
 *
 * Shows all 5 factor percentile bars (FactorBars) with a RadarChart below,
 * both imported from the landing visualizations directory.
 */

import { FactorBars } from "@/components/landing/visualizations/factor-bars"
import { RadarChart } from "@/components/landing/visualizations/radar-chart"

export interface FactorPanelFactors {
  quality: number
  value: number
  momentum: number
  sentiment: number | null
  growth: number | null
}

interface FactorPanelProps {
  factors: FactorPanelFactors
}

export function FactorPanel({ factors }: FactorPanelProps) {
  return (
    <div data-testid="factor-panel" className="terminal-card p-6 space-y-6">
      <h3 className="text-xs font-mono text-text-tertiary uppercase tracking-wider">
        Factor Profile
      </h3>

      {/* Factor bars */}
      <FactorBars factors={factors} />

      {/* Radar chart */}
      <div className="flex justify-center">
        <RadarChart factors={factors} size={220} />
      </div>
    </div>
  )
}
