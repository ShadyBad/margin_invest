import { formatScoredAt } from "@/lib/format"

interface HeroHeaderProps {
  ticker: string
  name: string
  sector?: string | null
  growthStage?: string | null
  actualPrice?: number | null
  priceChange?: number | null
  priceChangePercent?: number | null
  compositeScore: number
  universePercentile: number
  universeSize?: number
  convictionLevel: string
  signal: string
  dataCoverage: number
  scoredAt?: string | null
  dataFreshness?: string | null
  priceSource?: string | null
  scoreHistory?: number[]
}

function formatGrowthStage(stage: string): string {
  return stage
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ")
}

function MiniSparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null
  const w = 80
  const h = 24
  const pad = 2
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const points = values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (w - pad * 2)
      const y = h - pad - ((v - min) / range) * (h - pad * 2)
      return `${x},${y}`
    })
    .join(" ")

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="inline-block ml-2 align-middle">
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="text-accent"
      />
    </svg>
  )
}

export function HeroHeader({
  ticker,
  name,
  sector,
  growthStage,
  actualPrice,
  priceChange,
  priceChangePercent,
  compositeScore,
  universePercentile,
  universeSize,
  convictionLevel,
  signal,
  dataCoverage,
  scoredAt,
  dataFreshness,
  priceSource,
  scoreHistory,
}: HeroHeaderProps) {
  const topPercent = Math.max(1, Math.round(100 - universePercentile))
  const coveragePct = Math.round(dataCoverage * 100)
  const pricePositive = (priceChange ?? 0) >= 0

  const convictionColors: Record<string, string> = {
    exceptional: "text-accent",
    high: "text-accent",
    medium: "text-amber-500",
    watchlist: "text-amber-500",
    none: "text-text-secondary",
  }

  const signalColors: Record<string, string> = {
    buy: "text-bullish",
    hold: "text-accent",
    sell: "text-bearish",
    watch: "text-text-secondary",
    "urgent sell": "text-bearish",
  }

  return (
    <section data-testid="hero-header" className="space-y-4">
      {/* Ticker + Name + Sector row */}
      <div className="flex items-baseline justify-between flex-wrap gap-2">
        <div className="flex items-baseline gap-3">
          <h1 className="text-3xl font-display font-bold text-text-primary">{ticker}</h1>
          <span className="text-lg text-text-secondary">{name}</span>
        </div>
        {(sector || growthStage) && (
          <div className="flex items-center gap-2 text-sm text-text-tertiary">
            {sector && <span>{sector}</span>}
            {sector && growthStage && <span>·</span>}
            {growthStage && <span>{formatGrowthStage(growthStage)}</span>}
          </div>
        )}
      </div>

      {/* Price line */}
      {actualPrice != null && (
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-mono font-semibold text-text-primary">
            ${actualPrice.toFixed(2)}
          </span>
          {priceChange != null && priceChangePercent != null && (
            <span
              className={`text-sm font-mono ${pricePositive ? "text-bullish" : "text-bearish"}`}
            >
              {pricePositive ? "+" : ""}
              {priceChange.toFixed(2)} ({pricePositive ? "+" : ""}
              {priceChangePercent.toFixed(2)}%)
            </span>
          )}
        </div>
      )}

      {/* 4 Metric cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div data-testid="metric-score" className="terminal-card p-3">
          <div className="text-xs text-text-tertiary uppercase tracking-wide mb-1">Score</div>
          <div className="text-xl font-mono font-semibold text-text-primary">
            {compositeScore.toFixed(1)}
            {scoreHistory && scoreHistory.length >= 2 && <MiniSparkline values={scoreHistory} />}
          </div>
        </div>

        <div data-testid="metric-percentile" className="terminal-card p-3">
          <div className="text-xs text-text-tertiary uppercase tracking-wide mb-1">Percentile</div>
          <div className="text-xl font-mono font-semibold text-text-primary">
            Top {topPercent}%
          </div>
          {universeSize != null && (
            <div className="text-xs text-text-tertiary mt-0.5">of {universeSize} stocks</div>
          )}
        </div>

        <div data-testid="metric-conviction" className="terminal-card p-3">
          <div className="text-xs text-text-tertiary uppercase tracking-wide mb-1">Conviction</div>
          <div
            className={`text-xl font-mono font-semibold ${convictionColors[convictionLevel] || "text-text-secondary"}`}
          >
            {convictionLevel.toUpperCase()}
          </div>
        </div>

        <div data-testid="metric-signal" className="terminal-card p-3">
          <div className="text-xs text-text-tertiary uppercase tracking-wide mb-1">Signal</div>
          <div
            className={`text-xl font-mono font-semibold ${signalColors[signal.toLowerCase()] || "text-text-secondary"}`}
          >
            {signal.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Metadata ribbon */}
      <div
        data-testid="metadata-ribbon"
        className="text-xs text-text-tertiary flex items-center gap-1 flex-wrap"
      >
        <span>Data coverage: {coveragePct}%</span>
        <span>·</span>
        <span>Scored: {scoredAt ? formatScoredAt(scoredAt) : "N/A"}</span>
        <span>·</span>
        <span>
          Price: {priceSource === "live" ? "Live" : priceSource === "daily_close" ? "Daily close" : dataFreshness ?? "N/A"}
        </span>
      </div>
    </section>
  )
}
