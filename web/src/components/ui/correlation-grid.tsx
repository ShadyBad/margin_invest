"use client"

import { Fragment, useState } from "react"

interface CorrelationGridProps {
  tickers: string[]
  matrix: (number | null)[][]
  sampleSizes?: number[][]
  showTooltip?: boolean
  className?: string
}

function cellBackground(value: number | null): string {
  if (value === null) return "var(--color-bg-primary)"
  const abs = Math.abs(value)
  if (value >= 0) {
    if (abs >= 0.6)
      return `color-mix(in srgb, var(--color-accent) ${Math.round(15 + abs * 25)}%, transparent)`
    if (abs >= 0.3)
      return `color-mix(in srgb, var(--color-accent) ${Math.round(abs * 25)}%, transparent)`
    return "transparent"
  }
  if (abs >= 0.6)
    return `color-mix(in srgb, var(--color-danger) ${Math.round(15 + abs * 25)}%, transparent)`
  if (abs >= 0.3)
    return `color-mix(in srgb, var(--color-danger) ${Math.round(abs * 25)}%, transparent)`
  return "transparent"
}

function textClass(value: number | null, isDiagonal: boolean): string {
  if (value === null) return "text-text-tertiary"
  if (isDiagonal) return "text-text-tertiary"
  return Math.abs(value) >= 0.5 ? "text-text-primary" : "text-text-secondary"
}

function formatValue(value: number | null): string {
  if (value === null) return "\u2014"
  return value.toFixed(2)
}

export function CorrelationGrid({
  tickers,
  matrix,
  sampleSizes,
  showTooltip = false,
  className = "",
}: CorrelationGridProps) {
  const [hover, setHover] = useState<{ i: number; j: number } | null>(null)
  const n = tickers.length

  return (
    <div className={className}>
      <div
        className="grid gap-px"
        style={{ gridTemplateColumns: `auto repeat(${n}, 1fr)` }}
      >
        {/* Empty top-left corner */}
        <div />
        {/* Column headers */}
        {tickers.map((ticker) => (
          <div
            key={`col-${ticker}`}
            className="text-[9px] font-mono text-text-tertiary text-center py-1"
          >
            {ticker}
          </div>
        ))}
        {/* Rows */}
        {matrix.map((row, i) => (
          <Fragment key={`row-${tickers[i]}`}>
            {/* Row label */}
            <div className="text-[9px] font-mono text-text-tertiary flex items-center justify-end pr-2">
              {tickers[i]}
            </div>
            {/* Cells */}
            {row.map((value, j) => {
              const isDiag = i === j
              return (
                <div
                  key={`${i}-${j}`}
                  className="aspect-square flex items-center justify-center rounded-sm relative cursor-default"
                  style={{ background: cellBackground(value) }}
                  onMouseEnter={() => showTooltip && setHover({ i, j })}
                  onMouseLeave={() => setHover(null)}
                >
                  <span className={`text-xs font-mono ${textClass(value, isDiag)}`}>
                    {formatValue(value)}
                  </span>
                  {/* Tooltip */}
                  {showTooltip && hover?.i === i && hover?.j === j && !isDiag && (
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-10 bg-bg-elevated border border-border-primary rounded px-2 py-1 shadow-card whitespace-nowrap pointer-events-none">
                      <div className="text-xs font-mono text-text-primary">
                        {tickers[i]} &times; {tickers[j]}
                      </div>
                      <div className="text-xs font-mono text-text-secondary">
                        &rho; = {formatValue(value)}
                      </div>
                      {sampleSizes && (
                        <div className="text-xs font-mono text-text-tertiary">
                          N = {sampleSizes[i][j]} days
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </Fragment>
        ))}
      </div>
      {/* Legend */}
      <div className="flex items-center justify-center gap-2 mt-4">
        <span className="text-[9px] text-text-tertiary">-1.0</span>
        <div
          className="h-2 w-32 rounded-full"
          style={{
            background:
              "linear-gradient(to right, color-mix(in srgb, var(--color-danger) 40%, transparent), transparent 50%, color-mix(in srgb, var(--color-accent) 40%, transparent))",
          }}
        />
        <span className="text-[9px] text-text-tertiary">+1.0</span>
      </div>
    </div>
  )
}
