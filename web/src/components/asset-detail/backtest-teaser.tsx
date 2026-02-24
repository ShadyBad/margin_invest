"use client"

import Link from "next/link"

interface BacktestTeaserProps {
  modelReturn: number // e.g. 3.87 for 387%
  benchmarkReturn: number // e.g. 2.14 for 214%
  maxDrawdown: number // e.g. 0.31 for 31%
  benchmarkMaxDrawdown: number
  startYear: number
}

export function BacktestTeaser({
  modelReturn,
  benchmarkReturn,
  maxDrawdown,
  benchmarkMaxDrawdown,
  startYear,
}: BacktestTeaserProps) {
  const modelPct = `+${Math.round(modelReturn * 100)}%`
  const benchPct = `+${Math.round(benchmarkReturn * 100)}%`
  const drawdownPct = `-${Math.round(maxDrawdown * 100)}%`
  const benchDrawdownPct = `-${Math.round(benchmarkMaxDrawdown * 100)}%`

  return (
    <div className="terminal-card p-6 mt-6" data-testid="backtest-teaser">
      <h3 className="text-sm font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider mb-4">
        Historical Performance
      </h3>

      <div className="space-y-3">
        {/* Headline return */}
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-[var(--color-text-secondary)]">
            Model cumulative return since {startYear}
          </span>
          <span className="font-[family-name:var(--font-display)] text-2xl text-[var(--color-bullish)]">
            {modelPct}
          </span>
        </div>

        {/* Benchmark comparison */}
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-[var(--color-text-secondary)]">
            S&amp;P 500 over same period
          </span>
          <span className="font-[family-name:var(--font-mono)] text-lg text-[var(--color-text-tertiary)]">
            {benchPct}
          </span>
        </div>

        {/* Drawdown comparison */}
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-[var(--color-text-secondary)]">
            Max drawdown during 2008 crisis
          </span>
          <span className="font-[family-name:var(--font-mono)] text-lg">
            <span className="text-[var(--color-bearish)]">{drawdownPct}</span>
            <span className="text-[var(--color-text-tertiary)] mx-1">vs</span>
            <span className="text-[var(--color-text-tertiary)]">{benchDrawdownPct}</span>
          </span>
        </div>
      </div>

      {/* CTA */}
      <Link
        href="/backtest"
        className="mt-5 block w-full text-center py-3 px-4 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] transition-colors"
      >
        See every decision the model made &rarr;
      </Link>
    </div>
  )
}
