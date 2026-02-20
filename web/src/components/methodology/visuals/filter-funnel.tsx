"use client"

const segments = [
  { label: "Universe", count: "~7,000", width: "100%" },
  { label: "Pass all filters", count: "~4,200", width: "60%" },
  { label: "High conviction", count: "~150", width: "12%" },
]

export function FilterFunnel() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <div className="space-y-3">
        {segments.map((seg, i) => (
          <div key={seg.label} className="flex items-center gap-4">
            <div
              className="h-8 rounded-sm flex items-center px-3 transition-all"
              style={{
                width: seg.width,
                backgroundColor:
                  i === 0
                    ? "var(--color-border-primary)"
                    : i === 1
                      ? "rgba(var(--accent-rgb, 99 102 241) / 0.15)"
                      : "rgba(var(--accent-rgb, 99 102 241) / 0.3)",
              }}
            >
              <span className="text-[12px] font-mono text-text-primary whitespace-nowrap">
                {seg.count}
              </span>
            </div>
            <span className="text-[12px] text-text-secondary whitespace-nowrap">
              {seg.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
