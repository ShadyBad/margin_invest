import { ConvictionBadge, SignalBadge } from "@/components/ui"
import { formatAttributeLabel } from "@/lib/format"
import { FactorBreakdown } from "./factor-breakdown"
import { FilterList } from "./filter-list"
import type { ScoreResponse } from "@/lib/api/types"

interface AssetDetailProps {
  score: ScoreResponse
  className?: string
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

function formatScoredAt(isoString: string): string {
  const d = new Date(isoString)
  const month = MONTHS[d.getMonth()]
  const day = d.getDate()
  const year = d.getFullYear()
  const h = d.getHours()
  const hour = h === 0 ? 12 : h > 12 ? h - 12 : h
  const min = String(d.getMinutes()).padStart(2, "0")
  const ampm = h >= 12 ? "PM" : "AM"
  return `${month} ${day}, ${year}, ${hour}:${min} ${ampm}`
}

export function AssetDetail({ score, className = "" }: AssetDetailProps) {
  return (
    <div
      className={`border-t border-border-primary pt-6 mt-4 ${className}`}
      data-testid={`asset-detail-${score.ticker}`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <h3 className="text-xl font-bold text-text-primary">{score.ticker}</h3>
        <span className="text-sm text-text-secondary">{score.name}</span>
        <span className="text-lg font-bold text-accent ml-auto">
          {score.composite_percentile.toFixed(0)}
        </span>
        <ConvictionBadge level={score.conviction_level} />
        <SignalBadge signal={score.signal} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left column: Factor Breakdown */}
        <FactorBreakdown
          quality={score.quality}
          value={score.value}
          momentum={score.momentum}
        />

        {/* Right column: Filters + Metadata */}
        <div className="space-y-6">
          {score.filters_passed.length > 0 && (
            <FilterList filters={score.filters_passed} />
          )}

          {/* Metadata */}
          <div data-testid="asset-metadata">
            <h3 className="text-base font-semibold text-text-primary mb-3">
              Metadata
            </h3>
            <dl className="space-y-2 text-sm">
              {score.growth_stage && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Growth Stage</dt>
                  <dd className="text-text-primary">
                    {formatAttributeLabel(score.growth_stage)}
                  </dd>
                </div>
              )}
              {score.data_coverage !== undefined && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Data Coverage</dt>
                  <dd className="text-text-primary">
                    {(score.data_coverage * 100).toFixed(0)}%
                  </dd>
                </div>
              )}
              {score.scored_at && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Scored At</dt>
                  <dd className="text-text-primary">
                    {formatScoredAt(score.scored_at)}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}
