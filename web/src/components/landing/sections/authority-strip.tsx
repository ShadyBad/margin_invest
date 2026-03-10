const COLUMNS = [
  {
    label: "Data Sources",
    items: ["SEC EDGAR Filings", "Earnings Transcripts", "Daily Market Data"],
  },
  {
    label: "Coverage",
    items: ["3,056 equities", "11 GICS sectors", "6 elimination filters"],
  },
  {
    label: "Engine",
    items: ["v1.3.2", "Scored daily"],
  },
]

export function AuthorityStrip() {
  return (
    <section className="px-6 py-8">
      <div className="max-w-5xl mx-auto">
        <div className="bg-bg-elevated border border-border-subtle rounded-xl p-6 md:p-8">
          <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-text-tertiary mb-4 flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent/50" />
            SYSTEM PROFILE
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
            {COLUMNS.map((col) => (
              <div key={col.label}>
                <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">
                  {col.label}
                </div>
                <div className="space-y-1">
                  {col.items.map((item) => (
                    <div
                      key={item}
                      className="font-mono text-xs text-text-secondary"
                    >
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
