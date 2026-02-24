import { formatAttributeLabel } from "@/lib/format"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface InstitutionalAccumulation {
  percentile: number
  newPositions: number
  topFunds: string[]
}

interface ConvictionEngineProps {
  opportunityType: string | null
  winningTrack: string | null
  asymmetryRatio: number | null
  maxPositionPct: number | null
  timingSignal: string | null
  capitalAllocation: FactorBreakdownResponse | null
  catalyst: FactorBreakdownResponse | null
  institutionalAccumulation?: InstitutionalAccumulation | null
  mlOverride?: string | null
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

function TrackBar({ label, percentile }: { label: string; percentile: number }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="text-text-secondary w-40 truncate">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/[0.06]">
        <div
          className="h-full rounded-full bg-accent/60 transition-all"
          style={{ width: `${percentile}%` }}
        />
      </div>
      <span className="font-mono text-text-tertiary w-10 text-right">
        {Math.round(percentile)}th
      </span>
    </div>
  )
}

export function ConvictionEngine({
  opportunityType,
  winningTrack,
  asymmetryRatio,
  maxPositionPct,
  timingSignal,
  capitalAllocation,
  catalyst,
  institutionalAccumulation,
  mlOverride,
}: ConvictionEngineProps) {
  if (!opportunityType) return null

  const timing = timingSignal ? TIMING_LABELS[timingSignal] : null

  return (
    <section data-testid="conviction-engine" className="space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold text-text-primary">Conviction Engine</h2>
        {mlOverride === "promoted" && (
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-bullish/10 text-bullish">
            ML-promoted
          </span>
        )}
        {mlOverride === "demoted" && (
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-bearish/10 text-bearish">
            ML-demoted
          </span>
        )}
      </div>

      {/* Opportunity type banner */}
      <div className="terminal-card p-4 space-y-1">
        <span className="text-base font-semibold text-accent uppercase">
          {opportunityType.toUpperCase()}
        </span>
        <p className="text-sm text-text-secondary">
          {OPPORTUNITY_DESCRIPTIONS[opportunityType] ?? ""}
        </p>
      </div>

      {/* Three metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {asymmetryRatio != null && (
          <div className="terminal-card p-4 space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
              Asymmetry Ratio
            </span>
            <span className="text-2xl font-display text-text-primary block">
              {asymmetryRatio.toFixed(1)}x
            </span>
            <span className="text-xs text-text-tertiary">
              Upside is {asymmetryRatio.toFixed(1)}x the downside
            </span>
          </div>
        )}

        {maxPositionPct != null && (
          <div className="terminal-card p-4 space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
              Max Position
            </span>
            <span className="text-2xl font-display text-text-primary block">
              {maxPositionPct.toFixed(1)}%
            </span>
            <span className="text-xs text-text-tertiary">of portfolio</span>
          </div>
        )}

        {timing && (
          <div className="terminal-card p-4 space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
              Timing
            </span>
            <span className="text-base font-semibold text-text-primary block">{timing.label}</span>
            <span className="text-xs text-text-tertiary">{timing.description}</span>
          </div>
        )}
      </div>

      {/* Conviction tracks */}
      {(capitalAllocation || catalyst) && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-text-secondary">Conviction Tracks</h3>

          {capitalAllocation && (
            <div
              className={`terminal-card p-4 space-y-2 ${
                winningTrack === "compounder" ? "border-accent/30" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-text-primary uppercase">
                  Compounder Track
                </span>
                {winningTrack === "compounder" && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-medium">
                    winning
                  </span>
                )}
              </div>
              <div className="space-y-1.5">
                {capitalAllocation.sub_scores.map((s) => (
                  <TrackBar
                    key={s.name}
                    label={formatAttributeLabel(s.name)}
                    percentile={s.percentile_rank}
                  />
                ))}
              </div>
            </div>
          )}

          {catalyst && (
            <div
              className={`terminal-card p-4 space-y-2 ${
                winningTrack === "mispricing" ? "border-purple-500/30" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-text-primary uppercase">
                  Mispricing Track
                </span>
                {winningTrack === "mispricing" && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 font-medium">
                    winning
                  </span>
                )}
              </div>
              <div className="space-y-1.5">
                {catalyst.sub_scores.map((s) => (
                  <TrackBar
                    key={s.name}
                    label={formatAttributeLabel(s.name)}
                    percentile={s.percentile_rank}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Smart Money Alignment */}
      {institutionalAccumulation && institutionalAccumulation.topFunds.length > 0 && (
        <div className="terminal-card p-4 space-y-2" data-testid="smart-money-alignment">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            Smart Money Alignment
          </h3>
          <p className="text-xs text-text-tertiary">
            {institutionalAccumulation.newPositions} curated institutional investor
            {institutionalAccumulation.newPositions !== 1 ? "s" : ""}{" "}
            independently initiated or increased positions in the most recent 13F filing period.
          </p>
          <div className="flex flex-wrap gap-2">
            {institutionalAccumulation.topFunds.map((fund) => (
              <span
                key={fund}
                className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20"
              >
                {fund}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
