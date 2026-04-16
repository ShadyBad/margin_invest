import { FormulaTooltip } from "@/components/ui/formula-tooltip"

interface ConvictionEngineProps {
  opportunityType: string | null
  asymmetryRatio: number | null
  maxPositionPct: number | null
  timingSignal: string | null
}

const OPPORTUNITY_DESCRIPTIONS: Record<string, string> = {
  compounder:
    "This stock exhibits durable competitive advantages and consistent reinvestment returns.",
  mispricing: "The market is undervaluing this stock relative to its fundamentals.",
  both: "This stock exhibits both compounding qualities and current mispricing.",
  neither: "This stock does not clearly fit either opportunity pattern.",
}

const TIMING_LABELS: Record<string, { label: string; description: string }> = {
  buy_now: { label: "BUY NOW", description: "Current price represents a good entry point." },
  add_on_pullback: {
    label: "ADD ON PULLBACK",
    description: "Wait for a 5-10% dip from current levels.",
  },
  wait_for_catalyst: {
    label: "WAIT FOR CATALYST",
    description: "Hold until a specific catalyst materializes.",
  },
}

export function ConvictionEngine({
  opportunityType,
  asymmetryRatio,
  maxPositionPct,
  timingSignal,
}: ConvictionEngineProps) {
  if (!opportunityType) return null

  const timing = timingSignal ? TIMING_LABELS[timingSignal] : null

  return (
    <section
      data-testid="conviction-engine"
      className="rounded-lg p-6"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
      }}
    >
      {/* Top zone: opportunity type + rationale */}
      <div className="mb-6">
        <h2 className="text-headline-md uppercase" style={{ color: "var(--color-on-surface)" }}>
          {opportunityType.toUpperCase()}
        </h2>
        <p className="text-body-md mt-1" style={{ color: "var(--color-on-surface-variant)" }}>
          {OPPORTUNITY_DESCRIPTIONS[opportunityType] ?? ""}
        </p>
      </div>

      {/* Bottom zone: 3 metrics inline */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        {asymmetryRatio != null && (
          <div>
            <FormulaTooltip metricKey="asymmetry_ratio">
              <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                ASYMMETRY RATIO
              </span>
            </FormulaTooltip>
            <span
              className="text-mono-data block mt-1"
              style={{
                color: asymmetryRatio > 2 ? "var(--color-bullish)" : "var(--color-on-surface)",
              }}
            >
              {asymmetryRatio.toFixed(1)}x
            </span>
            <span className="text-label-sm mt-1 block" style={{ color: "var(--color-text-tertiary)" }}>
              Upside vs downside
            </span>
          </div>
        )}

        {maxPositionPct != null && (
          <div>
            <FormulaTooltip metricKey="max_position_pct">
              <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                MAX POSITION
              </span>
            </FormulaTooltip>
            <span
              className="text-mono-data block mt-1"
              style={{ color: "var(--color-on-surface)" }}
            >
              {maxPositionPct.toFixed(1)}%
            </span>
            <span className="text-label-sm mt-1 block" style={{ color: "var(--color-text-tertiary)" }}>
              Kelly-optimal sizing
            </span>
          </div>
        )}

        {timing && (
          <div>
            <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
              TIMING SIGNAL
            </span>
            <span
              className="text-mono-data block mt-1"
              style={{ color: "var(--color-on-surface)" }}
            >
              {timing.label}
            </span>
            <span className="text-label-sm mt-1 block" style={{ color: "var(--color-text-tertiary)" }}>
              {timing.description}
            </span>
          </div>
        )}
      </div>
    </section>
  )
}
