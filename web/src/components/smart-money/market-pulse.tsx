import type { MarketPulseResponse } from "@/lib/api/thirteenf"

interface MarketPulseProps {
  data: MarketPulseResponse
}

const DIRECTION_ARROWS: Record<string, string> = {
  up: "\u2191",
  down: "\u2193",
  flat: "\u2192",
}

function directionColor(direction: string): string {
  if (direction === "up") return "var(--color-bullish)"
  if (direction === "down") return "var(--color-bearish)"
  return "var(--color-text-tertiary)"
}

export function MarketPulse({ data }: MarketPulseProps) {
  return (
    <div
      data-testid="market-pulse"
      className="rounded-lg p-5 mb-6"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
          MARKET PULSE
        </h3>
        <span className="text-xs" style={{ fontFamily: "var(--font-data)", color: "var(--color-text-tertiary)" }}>
          {data.as_of_quarter}
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Institutional Breadth */}
        <div>
          <span className="text-xs block mb-1" style={{ color: "var(--color-text-tertiary)" }}>
            Institutional Breadth
          </span>
          <div className="flex items-baseline gap-1.5">
            <span
              data-testid="breadth-value"
              className="text-lg font-semibold"
              style={{
                fontFamily: "var(--font-data)",
                color: data.breadth_pct > 50 ? "var(--color-bullish)" : "var(--color-bearish)",
              }}
            >
              {data.breadth_pct}%
            </span>
            <span style={{ color: directionColor(data.breadth_direction), fontSize: 14 }}>
              {DIRECTION_ARROWS[data.breadth_direction]}
            </span>
          </div>
          <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
            Accumulating
          </span>
        </div>

        {/* Sector Rotation */}
        <div>
          <span className="text-xs block mb-1" style={{ color: "var(--color-text-tertiary)" }}>
            Sector Rotation
          </span>
          <div className="flex flex-wrap gap-1">
            {data.sector_flows.slice(0, 6).map((sf) => (
              <span
                key={sf.sector}
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  fontFamily: "var(--font-data)",
                  color: directionColor(sf.direction),
                  background: `color-mix(in srgb, ${directionColor(sf.direction)} 10%, transparent)`,
                }}
                title={`${sf.sector}: ${sf.net_shares.toLocaleString()} net shares`}
              >
                {sf.sector}
              </span>
            ))}
          </div>
        </div>

        {/* Smart Money Consensus */}
        <div>
          <span className="text-xs block mb-1" style={{ color: "var(--color-text-tertiary)" }}>
            Consensus Picks
          </span>
          <div className="space-y-0.5">
            {data.consensus_picks.slice(0, 3).map((cp) => (
              <div key={cp.ticker} className="flex items-center justify-between text-xs">
                <span style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
                  {cp.ticker}
                </span>
                <span style={{ fontFamily: "var(--font-data)", color: "var(--color-text-tertiary)" }}>
                  {cp.agreement_pct}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Flow Trend */}
        <div>
          <span className="text-xs block mb-1" style={{ color: "var(--color-text-tertiary)" }}>
            Flow Trend
          </span>
          <div className="flex items-baseline gap-1.5">
            <span style={{ color: directionColor(data.flow_trend_direction), fontSize: 14 }}>
              {DIRECTION_ARROWS[data.flow_trend_direction]}
            </span>
            <span
              data-testid="flow-trend-value"
              className="text-lg font-semibold"
              style={{
                fontFamily: "var(--font-data)",
                color: directionColor(data.flow_trend_direction),
              }}
            >
              {Math.abs(data.flow_trend_pct)}%
            </span>
          </div>
          <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
            vs last quarter
          </span>
        </div>
      </div>
    </div>
  )
}
