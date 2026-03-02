"use client"

import { useState, useMemo } from "react"
import { SignalBadge } from "@/components/ui"
import { getPercentileColor } from "./utils"

export interface ScoreHistoryRow {
  date: string
  score: number
  delta: number
  signal: string
  conviction: string
  keyChange: string
}

interface ScoreHistoryTableProps {
  history: ScoreHistoryRow[]
  status?: "loading" | "loaded" | "error"
}

type SortKey = "date" | "score"

export function ScoreHistoryTable({ history, status = "loaded" }: ScoreHistoryTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("date")
  const [sortAsc, setSortAsc] = useState(false)

  const sorted = useMemo(() => {
    const copy = [...history]
    copy.sort((a, b) => {
      let cmp: number
      if (sortKey === "date") {
        cmp = new Date(a.date).getTime() - new Date(b.date).getTime()
      } else {
        cmp = a.score - b.score
      }
      return sortAsc ? cmp : -cmp
    })
    return copy
  }, [history, sortKey, sortAsc])

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  if (status === "loading") {
    return (
      <div className="px-6 pt-4 pb-6" data-testid="score-history-loading">
        <div className="flex items-center justify-between mb-3">
          <div className="h-5 w-32 bg-white/[0.04] rounded animate-pulse" />
          <div className="h-4 w-16 bg-white/[0.04] rounded animate-pulse" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-[44px] bg-white/[0.02] rounded animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (status === "error") {
    return (
      <div className="px-6 py-8 text-center" data-testid="score-history-error">
        <p className="text-[13px] text-[#C74B50]">Unable to load score history</p>
      </div>
    )
  }

  if (history.length === 0) {
    return (
      <div className="px-6 py-8 text-center" data-testid="score-history-table">
        <p className="text-[13px] text-[#5C5955]">No scoring history yet</p>
      </div>
    )
  }

  function formatDate(iso: string): string {
    // Strip time component if present, then parse as local date to avoid UTC timezone shift
    const dateOnly = iso.split("T")[0]
    const [y, m, d] = dateOnly.split("-").map(Number)
    const date = new Date(y, m - 1, d)
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  }

  const chevron = sortAsc ? " \u25B2" : " \u25BC"

  return (
    <div className="px-6 pt-4 pb-6" data-testid="score-history-table">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[16px] font-semibold text-[#E8E6E3]">Score History</h3>
        <span className="text-[12px] text-[#5C5955]">{history.length} runs</span>
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-white/[0.06]">
            <th
              className="text-left text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2 cursor-pointer select-none"
              onClick={() => handleSort("date")}
            >
              Date{sortKey === "date" ? chevron : ""}
            </th>
            <th
              className="text-right text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2 cursor-pointer select-none"
              onClick={() => handleSort("score")}
            >
              Score{sortKey === "score" ? chevron : ""}
            </th>
            <th className="text-right text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2">Delta</th>
            <th className="text-center text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2">Signal</th>
            <th className="text-left text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2">Tier</th>
            <th className="text-left text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2">Key Change</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr
              key={row.date + i}
              className="border-b border-white/[0.03] h-[44px] hover:bg-white/[0.03] transition-colors duration-150"
            >
              <td className="text-[12px] font-mono text-[#9A9590]">{formatDate(row.date)}</td>
              <td className="text-right">
                <span
                  className="text-[16px] font-display"
                  style={{ color: getPercentileColor(row.score) }}
                >
                  {Math.round(row.score)}
                </span>
              </td>
              <td className="text-right">
                <span
                  data-testid="score-delta"
                  className={`text-[12px] font-mono ${
                    row.delta > 0 ? "text-[#1A7A5A]" : row.delta < 0 ? "text-[#C74B50]" : "text-[#5C5955]"
                  }`}
                >
                  {row.delta > 0 ? `+${row.delta}` : row.delta === 0 ? "\u2014" : row.delta}
                  {row.delta > 0 ? " \u25B2" : row.delta < 0 ? " \u25BC" : ""}
                </span>
              </td>
              <td className="text-center">
                <SignalBadge signal={row.signal} />
              </td>
              <td className="text-[12px]" style={{ color: getPercentileColor(row.score) }}>
                {row.conviction}
              </td>
              <td className="text-[12px] text-[#5C5955]">{row.keyChange}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
