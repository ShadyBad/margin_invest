/**
 * TrackRecordTable — Public ledger of scoring cycles.
 *
 * Displays: Date | # Survivors | Top Scorer | Score | Price Change (%).
 * Rows are sortable. Accepts live cycle data from the API.
 * When no data is available, shows an honest "accumulating" message.
 */

"use client"

import { useState, useMemo } from "react"

export interface CycleRecord {
  id: string
  date: string
  survivors: number
  topScorer: string
  topScore: number
  priceChange: number | null
}

interface TrackRecordTableProps {
  cycles?: CycleRecord[]
}

type SortField = "date" | "survivors" | "topScore" | "priceChange"
type SortOrder = "asc" | "desc"

function SortIndicator({
  field,
  sortField,
  sortOrder,
}: {
  field: SortField
  sortField: SortField
  sortOrder: SortOrder
}) {
  if (sortField !== field) return <span className="text-text-tertiary ml-1">⇅</span>
  return <span className="text-accent ml-1">{sortOrder === "asc" ? "↑" : "↓"}</span>
}

export function TrackRecordTable({ cycles = [] }: TrackRecordTableProps) {
  const [sortField, setSortField] = useState<SortField>("date")
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc")

  const sortedCycles = useMemo(() => {
    const sorted = [...cycles]
    sorted.sort((a, b) => {
      let aVal: number
      let bVal: number

      switch (sortField) {
        case "date":
          aVal = new Date(a.date).getTime()
          bVal = new Date(b.date).getTime()
          break
        case "survivors":
          aVal = a.survivors
          bVal = b.survivors
          break
        case "topScore":
          aVal = a.topScore
          bVal = b.topScore
          break
        case "priceChange":
          aVal = a.priceChange ?? 0
          bVal = b.priceChange ?? 0
          break
      }

      if (aVal < bVal) return sortOrder === "asc" ? -1 : 1
      if (aVal > bVal) return sortOrder === "asc" ? 1 : -1
      return 0
    })
    return sorted
  }, [cycles, sortField, sortOrder])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortOrder("desc")
    }
  }

  if (cycles.length === 0) {
    return (
      <section className="py-12 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="terminal-card p-8 text-center">
            <div className="flex items-center justify-center gap-2 mb-3">
              <span className="inline-block w-2 h-2 rounded-full bg-accent animate-pulse" />
              <span className="font-mono text-xs uppercase tracking-[0.14em] text-text-tertiary">
                Accumulating Data
              </span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed max-w-md mx-auto">
              The ledger populates automatically after each scoring cycle completes. Cycle data is
              timestamped and immutable once logged. Check back after the next market close.
            </p>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="py-12 px-6">
      <div className="max-w-6xl mx-auto">
        <p className="text-xs text-text-tertiary mb-4">
          Showing {sortedCycles.length} most recent cycles. Accumulating data since April 2026.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse min-w-[600px]">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="text-left py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  <button
                    onClick={() => handleSort("date")}
                    className="hover:text-text-secondary transition-colors flex items-center"
                  >
                    Date
                    <SortIndicator field="date" sortField={sortField} sortOrder={sortOrder} />
                  </button>
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  <button
                    onClick={() => handleSort("survivors")}
                    className="hover:text-text-secondary transition-colors flex items-center justify-end w-full"
                  >
                    # Survivors
                    <SortIndicator
                      field="survivors"
                      sortField={sortField}
                      sortOrder={sortOrder}
                    />
                  </button>
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  Top Scorer
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  <button
                    onClick={() => handleSort("topScore")}
                    className="hover:text-text-secondary transition-colors flex items-center justify-end w-full"
                  >
                    Score
                    <SortIndicator
                      field="topScore"
                      sortField={sortField}
                      sortOrder={sortOrder}
                    />
                  </button>
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  <button
                    onClick={() => handleSort("priceChange")}
                    className="hover:text-text-secondary transition-colors flex items-center justify-end w-full"
                  >
                    Price Δ Since Score
                    <SortIndicator
                      field="priceChange"
                      sortField={sortField}
                      sortOrder={sortOrder}
                    />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedCycles.map((cycle, idx) => {
                const change = cycle.priceChange
                const changeColor =
                  change === null
                    ? "text-text-tertiary"
                    : change >= 0
                      ? "text-[var(--color-bullish)]"
                      : "text-[var(--color-danger)]"
                return (
                  <tr
                    key={cycle.id}
                    className={`border-b border-border-subtle hover:bg-bg-elevated/40 transition-colors ${idx === 0 ? "bg-accent/5" : ""}`}
                  >
                    <td className="py-3 px-4 text-sm font-mono text-text-primary">{cycle.date}</td>
                    <td className="py-3 px-4 text-right text-sm font-mono text-accent font-semibold">
                      {cycle.survivors}
                    </td>
                    <td className="py-3 px-4 text-sm font-mono text-text-primary">
                      {cycle.topScorer}
                    </td>
                    <td className="py-3 px-4 text-right text-sm font-mono text-text-primary">
                      {cycle.topScore}
                    </td>
                    <td className={`py-3 px-4 text-right text-sm font-mono font-medium ${changeColor}`}>
                      {change === null ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(1)}%`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-6 text-center">
          <p className="text-xs text-text-tertiary">
            Historical data available via API.
          </p>
        </div>
      </div>
    </section>
  )
}
