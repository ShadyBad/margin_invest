"use client"

import { useState, type FormEvent } from "react"
import Link from "next/link"
import { apiFetch, ApiError } from "@/lib/api/client"

interface FactorSummary {
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
}

interface PublicScoreResult {
  ticker: string
  company_name: string
  composite_score: number
  composite_tier: string
  signal: string
  factor_summary: FactorSummary
  eliminated: boolean
  elimination_reason: string | null
  scored_at: string
}

type SearchState = "idle" | "loading" | "result" | "error"

const TIER_COLORS: Record<string, string> = {
  exceptional: "text-[var(--color-bullish)]",
  high: "text-[var(--color-bullish)]",
  medium: "text-[var(--color-warning)]",
  none: "text-text-tertiary",
}

const SIGNAL_LABELS: Record<string, string> = {
  strong: "Strong",
  stable: "Stable",
  emerging: "Emerging",
  weak: "Weak",
  failed: "Failed",
  neutral: "Neutral",
}

export function HeroSearch() {
  const [query, setQuery] = useState("")
  const [state, setState] = useState<SearchState>("idle")
  const [result, setResult] = useState<PublicScoreResult | null>(null)
  const [error, setError] = useState("")

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const ticker = query.trim().toUpperCase()
    if (!ticker) return

    setState("loading")
    setError("")
    setResult(null)

    try {
      const data = await apiFetch<PublicScoreResult>(
        `/api/v1/public/score/${ticker}`
      )
      setResult(data)
      setState("result")
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("Ticker not found. Check the symbol and try again.")
      } else {
        setError("Something went wrong. Please try again.")
      }
      setState("error")
    }
  }

  const factors = result
    ? [
        { label: "Quality", value: result.factor_summary.quality_percentile },
        { label: "Value", value: result.factor_summary.value_percentile },
        { label: "Momentum", value: result.factor_summary.momentum_percentile },
      ]
    : []

  return (
    <div data-hero-ctas>
      <form onSubmit={handleSubmit} className="flex gap-2 max-w-md">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onBlur={() => setQuery((q) => q.toUpperCase())}
          placeholder="Search any ticker..."
          className="flex-1 px-4 py-3 bg-bg-subtle border border-border-subtle rounded text-text-primary font-mono text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
          disabled={state === "loading"}
        />
        <button
          type="submit"
          disabled={state === "loading" || !query.trim()}
          aria-label="Search"
          className="px-5 py-3 bg-accent text-bg-primary font-medium text-sm rounded hover:bg-accent/90 transition-colors disabled:opacity-50"
        >
          {state === "loading" ? (
            <span data-testid="hero-search-loading" className="inline-block w-4 h-4 border-2 border-bg-primary border-t-transparent rounded-full animate-spin" />
          ) : (
            "Search"
          )}
        </button>
      </form>

      {/* Result card */}
      {state === "result" && result && (
        <div className="terminal-card p-5 mt-4 max-w-md animate-in fade-in duration-200">
          {/* Header: ticker + name */}
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="font-mono text-lg font-bold text-text-primary">
                {result.ticker}
              </span>
              <span className="text-sm text-text-secondary ml-2">
                {result.company_name}
              </span>
            </div>
            {result.eliminated && (
              <span className="text-xs font-mono uppercase tracking-wider text-[var(--color-bearish)] bg-[var(--color-bearish)]/10 px-2 py-0.5 rounded">
                Eliminated
              </span>
            )}
          </div>

          {/* Elimination reason */}
          {result.eliminated && result.elimination_reason && (
            <p className="text-xs text-[var(--color-bearish)] mb-3 font-mono">
              Failed: {result.elimination_reason}
            </p>
          )}

          {/* Score + tier + signal */}
          <div className="flex items-end gap-3 mb-4">
            <span className={`font-mono text-4xl font-bold ${TIER_COLORS[result.composite_tier] || "text-text-primary"}`}>
              {Math.round(result.composite_score)}
            </span>
            <div className="pb-1">
              <span className="text-xs uppercase tracking-wider text-text-tertiary">
                {result.composite_tier}
              </span>
              <span className="text-xs text-text-tertiary mx-1.5">&middot;</span>
              <span className="text-xs text-text-secondary">
                {SIGNAL_LABELS[result.signal] || result.signal}
              </span>
            </div>
          </div>

          {/* Factor bars */}
          <div className="space-y-2 mb-4">
            {factors.map((factor) => (
              <div key={factor.label} className="flex items-center gap-2">
                <span className="text-xs text-text-secondary w-20 shrink-0">
                  {factor.label}
                </span>
                <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500"
                    style={{ width: `${factor.value}%` }}
                  />
                </div>
                <span className="font-mono text-xs text-text-secondary w-8 text-right">
                  {Math.round(factor.value)}
                </span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <Link
            href="/onboarding"
            className="text-sm text-accent hover:text-accent/80 transition-colors"
          >
            See the full forensic report &rarr;
          </Link>
        </div>
      )}

      {/* Error state */}
      {state === "error" && (
        <p className="text-sm text-[var(--color-bearish)] mt-3 max-w-md">
          {error}
        </p>
      )}
    </div>
  )
}
