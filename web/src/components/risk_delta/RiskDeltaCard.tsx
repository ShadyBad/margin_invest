"use client"

import { useState, useEffect } from "react"
import { getRiskFactorAnalysis } from "@/lib/api/risk_diffing"
import type { RiskFactorAnalysis } from "@/lib/api/risk_diffing"
import { ChangeRow } from "./ChangeRow"

interface RiskDeltaCardProps {
  ticker: string
}

export function RiskDeltaCard({ ticker }: RiskDeltaCardProps) {
  const [data, setData] = useState<RiskFactorAnalysis | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      setLoading(true)
      const result = await getRiskFactorAnalysis(ticker)
      if (!cancelled) {
        setData(result)
        setLoading(false)
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [ticker])

  // Loading state
  if (loading) {
    return (
      <section
        data-testid="filing_delta_loading"
        className="terminal-card animate-pulse"
        style={{ minHeight: "6rem" }}
      >
        <div
          style={{
            height: "1rem",
            width: "12rem",
            borderRadius: "0.25rem",
            background: "var(--color-surface-container)",
            marginBottom: "0.75rem",
          }}
        />
        <div
          style={{
            height: "3rem",
            borderRadius: "0.5rem",
            background: "var(--color-surface-container)",
          }}
        />
      </section>
    )
  }

  // No data / null state
  if (!data) {
    return (
      <section data-testid="filing_delta_empty" className="terminal-card">
        <p
          style={{
            fontSize: "0.875rem",
            color: "var(--color-on-surface-variant)",
            textAlign: "center",
            padding: "1.5rem 0",
          }}
        >
          Insufficient data
        </p>
      </section>
    )
  }

  // Sort material changes by severity descending
  const sortedChanges = [...data.material_changes].sort(
    (a, b) => b.severity - a.severity,
  )

  const deltaScore = data.overall_risk_delta_score
  const deltaColor =
    deltaScore <= 2 ? "var(--color-bullish)" : deltaScore >= 2 ? "var(--color-bearish)" : "var(--color-on-surface)"

  return (
    <section data-testid="filing_delta_card" className="terminal-card">
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "0.5rem",
          marginBottom: "0.75rem",
        }}
      >
        <h2
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            color: "var(--color-on-surface-variant)",
          }}
        >
          Risk Factor Changes
        </h2>

        <span
          style={{
            fontSize: "0.75rem",
            color: "var(--color-on-surface-variant)",
          }}
        >
          {data.prior_period} &rarr; {data.current_period}
        </span>
      </div>

      {/* Delta score */}
      <div style={{ marginBottom: "1rem" }}>
        <span
          style={{
            fontSize: "0.75rem",
            color: "var(--color-on-surface-variant)",
            display: "block",
            marginBottom: "0.25rem",
          }}
        >
          RISK DELTA SCORE
        </span>
        <span
          data-testid="delta_score"
          style={{
            fontSize: "1.5rem",
            fontWeight: 700,
            fontFamily: "var(--font-data)",
            color: deltaColor,
          }}
        >
          {deltaScore > 0 ? "+" : ""}
          {deltaScore.toFixed(1)}
        </span>
      </div>

      {/* Changes list */}
      {sortedChanges.length === 0 ? (
        <p
          style={{
            fontSize: "0.875rem",
            color: "var(--color-on-surface-variant)",
          }}
        >
          No material changes
        </p>
      ) : (
        <div>
          {sortedChanges.map((change, idx) => (
            <ChangeRow key={`${change.change_type}_${change.topic}_${idx}`} change={change} />
          ))}
        </div>
      )}
    </section>
  )
}
