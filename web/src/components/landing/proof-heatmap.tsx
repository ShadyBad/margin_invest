import { Fragment } from "react"

const labels = ["AAPL", "MSFT", "JNJ", "COST", "V"]

// Correlation matrix (symmetric, diagonal = 1.0)
const matrix = [
  [1.0, 0.82, 0.15, 0.28, 0.45],
  [0.82, 1.0, 0.12, 0.31, 0.51],
  [0.15, 0.12, 1.0, 0.62, 0.22],
  [0.28, 0.31, 0.62, 1.0, 0.35],
  [0.45, 0.51, 0.22, 0.35, 1.0],
]

// Cells to annotate with numeric values
const annotated: Record<string, boolean> = {
  "0-1": true, // AAPL-MSFT
  "2-3": true, // JNJ-COST
  "1-4": true, // MSFT-V
}

function cellColor(value: number): string {
  if (value >= 0.6) return "color-mix(in srgb, var(--color-accent) 30%, transparent)"
  if (value >= 0.3) return "color-mix(in srgb, var(--color-text-tertiary) 30%, transparent)"
  return "color-mix(in srgb, var(--color-danger) 30%, transparent)"
}

export function ProofHeatmap() {
  return (
    <div>
      <div className="grid grid-cols-6 gap-px">
        {/* Empty top-left corner */}
        <div />
        {/* Column headers */}
        {labels.map((label) => (
          <div
            key={`col-${label}`}
            className="text-[9px] font-mono text-text-tertiary text-center py-1"
          >
            {label}
          </div>
        ))}
        {/* Rows */}
        {matrix.map((row, i) => (
          <Fragment key={`row-${labels[i]}`}>
            {/* Row label */}
            <div className="text-[9px] font-mono text-text-tertiary flex items-center justify-end pr-1">
              {labels[i]}
            </div>
            {/* Cells */}
            {row.map((value, j) => {
              const cellKey = `${i}-${j}`
              const isAnnotated = annotated[cellKey]
              return (
                <div
                  key={cellKey}
                  className="aspect-square flex items-center justify-center rounded-sm"
                  style={{ background: cellColor(value) }}
                >
                  {isAnnotated && (
                    <span className="text-[8px] font-mono text-text-secondary">
                      {value.toFixed(2)}
                    </span>
                  )}
                </div>
              )
            })}
          </Fragment>
        ))}
      </div>
      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-4">
        <div className="flex items-center gap-1">
          <div
            className="w-3 h-3 rounded-sm"
            style={{ background: "color-mix(in srgb, var(--color-danger) 30%, transparent)" }}
          />
          <span className="text-[9px] text-text-tertiary">-1.0</span>
        </div>
        <div className="flex items-center gap-1">
          <div
            className="w-3 h-3 rounded-sm"
            style={{
              background: "color-mix(in srgb, var(--color-text-tertiary) 30%, transparent)",
            }}
          />
          <span className="text-[9px] text-text-tertiary">0.0</span>
        </div>
        <div className="flex items-center gap-1">
          <div
            className="w-3 h-3 rounded-sm"
            style={{ background: "color-mix(in srgb, var(--color-accent) 30%, transparent)" }}
          />
          <span className="text-[9px] text-text-tertiary">+1.0</span>
        </div>
      </div>
    </div>
  )
}
