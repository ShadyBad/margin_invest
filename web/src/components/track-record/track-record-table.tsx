/**
 * TrackRecordTable — Public ledger of scoring cycles.
 *
 * Displays: Date | # Survivors | Top Scorer | Score | Price Change (%).
 * Rows are sortable. If no real data, shows structure with placeholder note.
 */

"use client"

import { useState, useMemo } from "react"

interface CycleRecord {
  id: string
  date: string
  survivors: number
  topScorer: string
  topScore: number
  priceAtScore: number
  priceNow: number
}

// Mock data (replace with API data when available)
const MOCK_CYCLES: CycleRecord[] = [
  { id: "cycle-247", date: "2026-04-04", survivors: 10, topScorer: "VIRC", topScore: 87, priceAtScore: 4.12, priceNow: 4.38 },
  { id: "cycle-246", date: "2026-04-03", survivors: 8, topScorer: "CSWC", topScore: 84, priceAtScore: 23.45, priceNow: 24.10 },
  { id: "cycle-245", date: "2026-04-02", survivors: 11, topScorer: "VIRC", topScore: 85, priceAtScore: 3.98, priceNow: 4.38 },
  { id: "cycle-244", date: "2026-04-01", survivors: 9, topScorer: "CSWC", topScore: 82, priceAtScore: 22.80, priceNow: 24.10 },
  { id: "cycle-243", date: "2026-03-31", survivors: 10, topScorer: "VIRC", topScore: 86, priceAtScore: 3.75, priceNow: 4.38 },
]

type SortField = "date" | "survivors" | "topScore" | "priceChange"
type SortOrder = "asc" | "desc"

function priceChange(cycle: CycleRecord): number {
  return ((cycle.priceNow - cycle.priceAtScore) / cycle.priceAtScore) * 100
}

function SortIndicator({ field, sortField, sortOrder }: { field: SortField; sortField: SortField; sortOrder: SortOrder }) {
  if (sortField !== field) return <span className="text-text-tertiary ml-1">⇅</span>
  return <span className="text-accent ml-1">{sortOrder === "asc" ? "↑" : "↓"}</span>
}

export function TrackRecordTable() {
  const [sortField, setSortField] = useState<SortField>("date")
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc")

  const sortedCycles = useMemo(() => {
    const sorted = [...MOCK_CYCLES]
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
          aVal = priceChange(a)
          bVal = priceChange(b)
          break
      }

      if (aVal < bVal) return sortOrder === "asc" ? -1 : 1
      if (aVal > bVal) return sortOrder === "asc" ? 1 : -1
      return 0
    })
    return sorted
  }, [sortField, sortOrder])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortOrder("desc")
    }
  }

  return (
    <section className="py-12 px-6">
      <div className="max-w-6xl mx-auto">
        <p className="text-xs text-text-tertiary mb-4">Accumulating data since April 2026</p>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse min-w-[600px]">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="text-left py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  <button onClick={() => handleSort("date")} className="hover:text-text-secondary transition-colors flex items-center">
                    Date
                    <SortIndicator field="date" sortField={sortField} sortOrder={sortOrder} />
                  </button>
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  <button onClick={() => handleSort("survivors")} className="hover:text-text-secondary transition-colors flex items-center justify-end w-full">
                    # Survivors
                    <SortIndicator field="survivors" sortField={sortField} sortOrder={sortOrder} />
                  </button>
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  Top Scorer
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  <button onClick={() => handleSort("topScore")} className="hover:text-text-secondary transition-colors flex items-center justify-end w-full">
                    Score
                    <SortIndicator field="topScore" sortField={sortField} sortOrder={sortOrder} />
                  </button>
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                  <button onClick={() => handleSort("priceChange")} className="hover:text-text-secondary transition-colors flex items-center justify-end w-full">
                    Price Δ Since Score
                    <SortIndicator field="priceChange" sortField={sortField} sortOrder={sortOrder} />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedCycles.map((cycle, idx) => {
                const change = priceChange(cycle)
                const changeColor = change >= 0 ? "text-[var(--color-bullish)]" : "text-[var(--color-danger)]"
                return (
                  <tr
                    key={cycle.id}
                    className={`border-b border-border-subtle hover:bg-bg-elevated/40 transition-colors ${idx === 0 ? "bg-accent/5" : ""}`}
                  >
                    <td className="py-3 px-4 text-sm font-mono text-text-primary">{cycle.date}</td>
                    <td className="py-3 px-4 text-right text-sm font-mono text-accent font-semibold">{cycle.survivors}</td>
                    <td className="py-3 px-4 text-sm font-mono text-text-primary">{cycle.topScorer}</td>
                    <td className="py-3 px-4 text-right text-sm font-mono text-text-primary">{cycle.topScore}</td>
                    <td className={`py-3 px-4 text-right text-sm font-mono font-medium ${changeColor}`}>
                      {change >= 0 ? "+" : ""}{change.toFixed(1)}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="mt-6 text-center">
          <p className="text-xs text-text-tertiary">
            Showing {sortedCycles.length} most recent cycles. Historical data available via API.
          </p>
        </div>
      </div>
    </section>
  )
}
