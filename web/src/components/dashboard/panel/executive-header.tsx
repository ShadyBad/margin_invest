"use client"

import { ConvictionBadge, ActionPill, AnimatedScore } from "@/components/ui"
import { TimeRangeSelector, type TimeRange } from "./time-range-selector"

interface ExecutiveHeaderProps {
  ticker: string
  companyName: string
  compositeScore: number
  scoreDelta: number
  conviction: string
  signal: string
  opportunityType: "compounder" | "mispricing"
  buyPrice?: number | null
  sellPrice?: number | null
  actualPrice?: number | null
  timeRange: TimeRange
  onTimeRangeChange: (range: TimeRange) => void
  onClose: () => void
}

export function ExecutiveHeader({
  ticker,
  companyName,
  compositeScore,
  scoreDelta,
  conviction,
  signal,
  buyPrice,
  sellPrice,
  actualPrice,
  timeRange,
  onTimeRangeChange,
  onClose,
}: ExecutiveHeaderProps) {
  return (
    <div
      className="sticky top-0 z-10 flex items-center gap-4 h-[72px] px-6 bg-bg-primary border-b border-border-subtle"
      data-testid="executive-header"
    >
      <button
        onClick={onClose}
        className="w-10 h-10 flex items-center justify-center rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-overlay transition-colors"
        data-testid="panel-close-btn"
        aria-label="Close panel"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M4 4l8 8M12 4l-8 8" />
        </svg>
      </button>

      <div className="flex items-center gap-2 min-w-0">
        <span className="text-xl font-semibold text-text-primary font-sans shrink-0">{ticker}</span>
        <span className="text-[13px] text-text-tertiary truncate">{companyName}</span>
        <ConvictionBadge level={conviction} />
      </div>

      <div className="flex items-center gap-3 ml-auto">
        <AnimatedScore
          value={compositeScore}
          className="text-[32px] font-display text-accent leading-none tracking-[-0.04em]"
        />
        <span
          data-testid="score-delta"
          className={`text-[13px] font-mono ${scoreDelta >= 0 ? "text-bullish" : "text-bearish"}`}
        >
          {scoreDelta >= 0 ? `+${scoreDelta}` : scoreDelta}
          {scoreDelta > 0 ? " ▲" : scoreDelta < 0 ? " ▼" : ""}
        </span>
        <ActionPill
          signal={signal}
          buyPrice={buyPrice}
          sellPrice={sellPrice}
          actualPrice={actualPrice}
        />
      </div>

      <TimeRangeSelector value={timeRange} onChange={onTimeRangeChange} />
    </div>
  )
}
