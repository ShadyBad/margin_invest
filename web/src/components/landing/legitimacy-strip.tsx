const markers = [
  "Data Sources: SEC Filings, Earnings Transcripts, Market Feeds",
  "Updated Daily",
  "Encrypted Key Storage",
  "Audit-Friendly Scoring",
  "No Hidden Heuristics",
]

export function LegitimacyStrip() {
  return (
    <div className="border-y border-border-subtle py-6">
      <div className="max-w-6xl mx-auto px-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
        {markers.map((marker, i) => (
          <span key={marker} className="font-mono text-[10px] uppercase tracking-wider text-text-tertiary">
            {marker}
            {i < markers.length - 1 && (
              <span className="ml-6 text-border-subtle hidden md:inline">|</span>
            )}
          </span>
        ))}
      </div>
    </div>
  )
}
