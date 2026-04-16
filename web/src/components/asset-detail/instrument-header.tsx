/**
 * InstrumentHeader — Full-width verdict strip at the top of the forensic report.
 *
 * Shows ticker, company name, sector/stage/style chips, composite score (tier-colored),
 * tier badge, signal, scored timestamp, and determinism lock icon.
 */

import Link from "next/link"
import { formatScoredAt } from "@/lib/format"

interface InstrumentHeaderProps {
  ticker: string
  name: string
  sector: string | null
  growthStage: string | null
  style: string | null
  score: number
  tier: string
  signal: string | null
  scoredAt: string | null
  eliminated: boolean
  eliminationReason?: string | null
  universePercentile: number
}

function getTierColor(tier: string): string {
  const colors: Record<string, string> = {
    exceptional: "var(--color-percentile-exceptional)",
    high: "var(--color-percentile-strong)",
    medium: "var(--color-percentile-average)",
    watchlist: "var(--color-percentile-below)",
    none: "var(--color-percentile-weak)",
  }
  return colors[tier] ?? "var(--color-on-surface-variant)"
}

export function InstrumentHeader({
  ticker,
  name,
  sector,
  growthStage,
  style,
  score,
  tier,
  signal,
  scoredAt,
  eliminated,
  eliminationReason,
  universePercentile,
}: InstrumentHeaderProps) {
  const tierColor = getTierColor(tier)
  const chips = [sector, growthStage, style].filter(Boolean) as string[]

  return (
    <div
      data-testid="instrument-header"
      className="rounded-lg p-6 md:p-8"
      style={{ background: "var(--color-surface-container-low)" }}
    >
      {/* Breadcrumb */}
      <nav className="text-label-sm mb-4" style={{ color: "var(--color-text-tertiary)" }}>
        <Link href="/explore" className="hover:underline" style={{ color: "var(--color-text-tertiary)" }}>
          Explore
        </Link>
        <span className="mx-1">/</span>
        <span style={{ color: "var(--color-on-surface-variant)" }}>{ticker.toUpperCase()}</span>
      </nav>

      {/* Main content row */}
      <div className="flex items-start justify-between flex-wrap gap-6">
        {/* Left zone — identity */}
        <div className="min-w-0">
          <h1 className="text-headline-md uppercase" style={{ color: "var(--color-on-surface)" }}>
            {ticker.toUpperCase()}
          </h1>
          <p className="text-body-md mt-1" style={{ color: "var(--color-on-surface-variant)" }}>
            {name}
          </p>
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {chips.map((chip) => (
                <span
                  key={chip}
                  className="text-label-sm rounded-sm px-2 py-0.5"
                  style={{
                    color: "var(--color-on-surface-variant)",
                    background: "var(--color-surface-container)",
                  }}
                >
                  {chip.toUpperCase()}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Center zone — score + tier + signal */}
        <div className="text-center flex-shrink-0">
          <div
            className="tabular-nums font-bold"
            style={{
              fontFamily: "var(--font-data)",
              fontSize: 56,
              lineHeight: 1,
              color: tierColor,
              opacity: eliminated ? 0.4 : 1,
            }}
            data-testid="score-value"
          >
            {Math.round(score)}
          </div>
          <div className="mt-2">
            {eliminated ? (
              <span
                className="text-label-sm rounded-sm px-2 py-0.5 inline-block"
                style={{
                  color: "var(--color-bearish)",
                  background: "rgba(212, 90, 95, 0.12)",
                }}
              >
                ELIMINATED
              </span>
            ) : (
              <span
                className="text-label-sm rounded-sm px-2 py-0.5 inline-block"
                style={{
                  color: tierColor,
                  background: `color-mix(in srgb, ${tierColor} 12%, transparent)`,
                }}
                data-testid="tier-badge"
              >
                {tier.toUpperCase()}
              </span>
            )}
          </div>
          <p className="text-label-sm mt-2" style={{ color: "var(--color-text-tertiary)" }}>
            {eliminated
              ? eliminationReason ?? "Failed elimination filters"
              : signal
                ? signal.toUpperCase()
                : "\u2014"}
          </p>
        </div>

        {/* Right zone — timestamp + determinism */}
        <div className="text-right flex-shrink-0">
          {scoredAt && (
            <p className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>
              {formatScoredAt(scoredAt)}
            </p>
          )}
          <div className="flex items-center justify-end gap-1.5 mt-2" title="Zero human discretion">
            <svg
              width={16}
              height={16}
              viewBox="0 0 16 16"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M8 1C5.79 1 4 2.79 4 5v2H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V8a1 1 0 0 0-1-1h-1V5c0-2.21-1.79-4-4-4Zm2 6H6V5a2 2 0 1 1 4 0v2Z"
                fill="var(--color-text-tertiary)"
              />
            </svg>
            <span className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>
              DETERMINISTIC
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
