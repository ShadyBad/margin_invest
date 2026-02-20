"use client"

const bars = [
  { label: "Quality", percentile: 78, color: "bg-accent" },
  { label: "Value", percentile: 64, color: "bg-bullish" },
  { label: "Momentum", percentile: 88, color: "bg-warning" },
]

const composite = { label: "Composite", percentile: 79, color: "bg-accent" }

export function ScoreBreakdownBars() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <div className="flex items-baseline justify-between mb-6">
        <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase">
          Example: ACME Corp
        </p>
        <span className="text-[11px] font-mono text-text-tertiary">Technology</span>
      </div>

      <div className="space-y-4">
        {bars.map((bar) => (
          <div key={bar.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[13px] font-medium text-text-primary">
                {bar.label}
              </span>
              <span className="text-[12px] font-mono text-text-tertiary">
                {bar.percentile}th
              </span>
            </div>
            <div className="h-2 rounded-full bg-bg-primary">
              <div
                className={`h-2 rounded-full ${bar.color}`}
                style={{ width: `${bar.percentile}%` }}
              />
            </div>
          </div>
        ))}

        <div className="border-t border-border-subtle pt-4 mt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[13px] font-semibold text-text-primary">
              {composite.label}
            </span>
            <span className="text-[12px] font-mono text-text-primary">
              {composite.percentile}th
            </span>
          </div>
          <div className="h-2.5 rounded-full bg-bg-primary">
            <div
              className={`h-2.5 rounded-full ${composite.color}`}
              style={{ width: `${composite.percentile}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
