"use client"

import Link from "next/link"
import { FactorSignature } from "@/components/visualizations/factor-signature"
import { ConvictionBadge } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"
import { formatScore, formatRelativeTime } from "@/lib/format"

function getTierColor(tier: string): string {
  switch (tier) {
    case "exceptional":
      return "var(--color-percentile-exceptional)"
    case "high":
      return "var(--color-percentile-strong)"
    case "medium":
      return "var(--color-percentile-average)"
    case "low":
    case "below":
      return "var(--color-percentile-below)"
    default:
      return "var(--color-text-primary)"
  }
}

function FreshnessIndicator({ freshness }: { freshness: string }) {
  const dotClass =
    freshness === "fresh"
      ? "bg-emerald-500"
      : freshness === "stale"
        ? "bg-amber-500"
        : "bg-red-500"
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-text-tertiary" data-testid="freshness-indicator">
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${dotClass}`} />
      {freshness}
    </span>
  )
}

interface PickHeroCardProps {
  pick: PickSummary
  rank: number
}

export function PickHeroCard({ pick, rank }: PickHeroCardProps) {
  return (
    <div
      className="relative bg-bg-elevated rounded-xl p-6"
      style={{
        border: "1px solid rgba(26,122,90,0.2)",
        boxShadow: "0 0 30px rgba(26,122,90,0.06)",
      }}
      data-testid={`pick-hero-${pick.ticker}`}
    >
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-6 items-center">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span
              className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-bold"
              style={{
                background: "var(--color-accent)",
                color: "var(--color-bg-primary)",
              }}
            >
              #{rank}
            </span>
            <h3 className="text-xl font-bold text-text-primary">
              {pick.ticker}
            </h3>
            <ConvictionBadge level={pick.composite_tier} />
          </div>
          <p className="text-sm text-text-secondary mb-1 truncate" data-testid="pick-name">{pick.name}</p>
          {pick.sector && (
            <span className="text-caption text-text-tertiary">
              {pick.sector}
            </span>
          )}
          <div className="mt-4">
            <span
              className="font-mono text-[36px] font-bold leading-none tracking-tight"
              style={{ color: getTierColor(pick.composite_tier) }}
            >
              {formatScore(pick.score)}
            </span>
          </div>
          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-3 mt-3">
            {pick.margin_of_safety != null && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 font-mono">
                MoS {Math.round(pick.margin_of_safety * 100)}%
              </span>
            )}
            {pick.price_upside != null && (
              <span className={`text-xs font-mono font-medium ${
                pick.price_upside >= 0 ? "text-emerald-400" : "text-red-400"
              }`}>
                {pick.price_upside >= 0 ? "+" : ""}{(pick.price_upside * 100).toFixed(1)}%
              </span>
            )}
            {pick.opportunity_type && (
              <span className="text-xs text-text-tertiary">{pick.opportunity_type}</span>
            )}
            {pick.data_freshness && <FreshnessIndicator freshness={pick.data_freshness} />}
            {pick.scored_at && (
              <span className="text-xs text-text-tertiary font-mono">
                {formatRelativeTime(pick.scored_at)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 mt-3 text-sm">
            {pick.actual_price != null && (
              <span className="text-text-secondary">
                Price:{" "}
                <span className="text-text-primary font-medium">
                  ${pick.actual_price.toFixed(2)}
                </span>
              </span>
            )}
            <Link
              href={`/asset/${pick.ticker}`}
              className="text-xs text-accent hover:text-accent/80 transition-colors"
            >
              Full report &rarr;
            </Link>
          </div>
        </div>
        <div className="flex-shrink-0">
          <FactorSignature
            factors={{
              quality: pick.quality_percentile,
              value: pick.value_percentile,
              momentum: pick.momentum_percentile,
              sentiment: pick.sentiment_percentile ?? null,
              growth: pick.growth_percentile ?? null,
            }}
            variant="compact"
          />
        </div>
      </div>
    </div>
  )
}
