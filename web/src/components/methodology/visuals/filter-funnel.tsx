"use client"

const filters = [
  { label: "Earnings Quality", pass: "~6,500" },
  { label: "Financial Distress", pass: "~6,100" },
  { label: "Short-Term Liquidity", pass: "~5,700" },
  { label: "Debt Service", pass: "~5,200" },
  { label: "Cash Flow Health", pass: "~4,800" },
  { label: "Market Cap & Volume", pass: "~4,200" },
]

export function FilterFunnel() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      {/* Funnel header */}
      <div className="flex items-center gap-4 mb-4">
        <div
          className="h-8 rounded-sm flex items-center px-3"
          style={{
            width: "100%",
            backgroundColor: "var(--color-border-primary)",
          }}
        >
          <span className="text-[12px] font-mono text-text-primary whitespace-nowrap">
            ~7,000
          </span>
        </div>
        <span className="text-[12px] text-text-secondary whitespace-nowrap">
          Universe
        </span>
      </div>

      {/* Individual filters */}
      <div className="space-y-2">
        {filters.map((filter, i) => {
          const widthPct = 90 - i * 10
          return (
            <div key={filter.label} className="flex items-center gap-4">
              <div
                className="h-7 rounded-sm flex items-center px-3"
                style={{
                  width: `${widthPct}%`,
                  backgroundColor: "rgba(74, 158, 126, 0.25)",
                  borderLeft: "2px solid var(--color-primary-muted)",
                }}
              >
                <span className="text-xs font-mono text-text-primary whitespace-nowrap">
                  {filter.pass}
                </span>
              </div>
              <span className="text-[12px] text-text-secondary whitespace-nowrap">
                {filter.label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Funnel result */}
      <div className="flex items-center gap-4 mt-4">
        <div
          className="h-8 rounded-sm flex items-center px-3"
          style={{
            width: "25%",
            backgroundColor: "rgba(14, 79, 58, 0.25)",
          }}
        >
          <span className="text-[12px] font-mono text-text-primary whitespace-nowrap">
            ~150
          </span>
        </div>
        <span className="text-[12px] text-text-secondary whitespace-nowrap">
          High conviction
        </span>
      </div>
    </div>
  )
}
