const factors = [
  { label: "Valuation", value: 62 },
  { label: "Quality", value: 85 },
  { label: "Momentum", value: 71 },
  { label: "Sentiment", value: 68 },
  { label: "Growth", value: 74 },
]

export function ProofFactorBars() {
  return (
    <div className="space-y-3">
      {factors.map((f) => (
        <div key={f.label} className="flex items-center gap-3">
          <span className="text-xs text-text-tertiary w-20">{f.label}</span>
          <div className="relative flex-1 h-2 bg-bg-subtle rounded-full overflow-hidden">
            {/* Guide marks at 25%, 50%, 75% */}
            <div
              className="absolute top-0 bottom-0 w-px bg-border-subtle"
              style={{ left: "25%" }}
            />
            <div
              className="absolute top-0 bottom-0 w-px bg-border-subtle"
              style={{ left: "50%" }}
            />
            <div
              className="absolute top-0 bottom-0 w-px bg-border-subtle"
              style={{ left: "75%" }}
            />
            <div
              className="h-full bg-accent rounded-full"
              style={{ width: `${f.value}%` }}
            />
          </div>
          <span className="font-mono text-xs w-8 text-right text-text-secondary">
            {f.value}
          </span>
        </div>
      ))}
    </div>
  )
}
