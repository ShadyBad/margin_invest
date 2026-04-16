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
  if (value === null) return "var(--color-surface-container-lowest)"
  const abs = Math.abs(value)
  if (value >= 0) {
    if (abs >= 0.6)
      return `color-mix(in srgb, var(--color-primary) ${Math.round(15 + abs * 25)}%, transparent)`
    if (abs >= 0.3)
      return `color-mix(in srgb, var(--color-primary) ${Math.round(abs * 25)}%, transparent)`
    return "transparent"
  }
  if (abs >= 0.6)
    return `color-mix(in srgb, var(--color-danger) ${Math.round(15 + abs * 25)}%, transparent)`
  if (abs >= 0.3)
    return `color-mix(in srgb, var(--color-danger) ${Math.round(abs * 25)}%, transparent)`
  return "transparent"
}

function textClass(value: number | null, isDiagonal: boolean): string {
  if (value === null) return "text-[var(--color-text-tertiary)]"
  if (isDiagonal) return "text-[var(--color-text-tertiary)]"
  return Math.abs(value) >= 0.5 ? "text-[var(--color-on-surface)]" : "text-[var(--color-on-surface-variant)]"
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
      <div className="overflow-x-auto">
      <div
        className="grid gap-px min-w-[400px]"
        style={{ gridTemplateColumns: `auto repeat(${n}, 1fr)` }}
      >
        {/* Empty top-left corner */}
        <div />
        {/* Column headers */}
        {tickers.map((ticker) => (
          <div
            key={`col-${ticker}`}
            className="text-[9px] text-[var(--color-text-tertiary)] text-center py-1"
            style={{ fontFamily: "var(--font-data)" }}
          >
            {ticker}
          </div>
        ))}
        {/* Rows */}
        {matrix.map((row, i) => (
          <Fragment key={`row-${tickers[i]}`}>
            {/* Row label */}
            <div className="text-[9px] text-[var(--color-text-tertiary)] flex items-center justify-end pr-2" style={{ fontFamily: "var(--font-data)" }}>
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
                  <span className={`text-xs ${textClass(value, isDiag)}`} style={{ fontFamily: "var(--font-data)" }}>
                    {formatValue(value)}
                  </span>
                  {/* Tooltip */}
                  {showTooltip && hover?.i === i && hover?.j === j && !isDiag && (
                    <div
                      className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-10 rounded-sm px-2 py-1 whitespace-nowrap pointer-events-none"
                      style={{
                        background: "var(--color-surface-container-low)",
                        border: "1px solid var(--color-ghost-border)",
                      }}
                    >
                      <div className="text-xs" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
                        {tickers[i]} &times; {tickers[j]}
                      </div>
                      <div className="text-xs" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}>
                        &rho; = {formatValue(value)}
                      </div>
                      {sampleSizes && (
                        <div className="text-xs text-[var(--color-text-tertiary)]">
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
      </div>{/* end overflow-x-auto */}
      {/* Scroll hint — visible on mobile only */}
      <p className="text-[10px] text-[var(--color-text-tertiary)] text-center mt-2 sm:hidden" aria-hidden="true">
        ← scroll →
      </p>
      {/* Legend */}
      <div className="flex items-center justify-center gap-2 mt-4">
        <span className="text-[9px] text-[var(--color-text-tertiary)]">-1.0</span>
        <div
          className="h-2 w-32 rounded-sm"
          style={{
            background:
              "linear-gradient(to right, color-mix(in srgb, var(--color-danger) 40%, transparent), transparent 50%, color-mix(in srgb, var(--color-primary) 40%, transparent))",
          }}
        />
        <span className="text-[9px] text-[var(--color-text-tertiary)]">+1.0</span>
      </div>
    </div>
  )
}
