"use client"

import { useState, useRef, type FormEvent } from "react"
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
  exceptional: "var(--color-bullish)",
  high: "var(--color-bullish)",
  medium: "var(--color-warning)",
  none: "var(--color-text-tertiary)",
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
  const [inputFocused, setInputFocused] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

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
        {/* Input container with focus ring */}
        <div
          ref={containerRef}
          className="flex-1 flex items-center gap-2 px-3 py-3 bg-bg-subtle rounded transition-all"
          style={{
            border: `1px solid ${inputFocused ? "var(--color-accent)" : "var(--color-border-subtle)"}`,
            boxShadow: inputFocused
              ? "0 0 0 3px color-mix(in srgb, var(--color-accent) 12%, transparent)"
              : "none",
          }}
        >
          {/* Search icon */}
          <svg
            width={14}
            height={14}
            viewBox="0 0 14 14"
            fill="none"
            className="shrink-0"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5" />
            <path d="M9.5 9.5L13 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setInputFocused(true)}
            onBlur={() => {
              setInputFocused(false)
              setQuery((q) => q.toUpperCase())
            }}
            placeholder="Search any ticker..."
            className="flex-1 bg-transparent text-text-primary font-mono text-sm placeholder:text-text-tertiary focus:outline-none"
            disabled={state === "loading"}
          />
        </div>
        <button
          type="submit"
          disabled={state === "loading" || !query.trim()}
          aria-label="Search"
          className="px-5 py-3 text-bg-primary font-medium text-sm rounded hover:opacity-90 transition-colors disabled:opacity-50"
          style={{ backgroundColor: "color-mix(in srgb, var(--color-accent) 85%, var(--color-bg-primary))" }}
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
        <div
          className="relative overflow-hidden rounded-xl bg-bg-elevated mt-4 max-w-md animate-in fade-in duration-200"
          style={{
            border: "1px solid color-mix(in srgb, var(--color-accent) 25%, var(--color-border-subtle))",
            boxShadow: "0 0 24px 0 color-mix(in srgb, var(--color-accent) 6%, transparent)",
          }}
        >
          {/* 2px gradient top bar */}
          <div
            className="w-full"
            style={{
              height: "2px",
              background: "linear-gradient(to right, var(--color-accent), transparent)",
            }}
          />

          <div className="p-5">
            {/* Header: ticker + name (left) + score (right) */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <span className="font-mono text-lg font-bold text-text-primary">
                  {result.ticker}
                </span>
                <span className="text-sm text-text-secondary ml-2">
                  {result.company_name}
                </span>
                {result.eliminated && (
                  <span className="ml-2 text-xs font-mono uppercase tracking-wider text-[var(--color-bearish)] bg-[var(--color-bearish)]/10 px-2 py-0.5 rounded">
                    Eliminated
                  </span>
                )}
              </div>

              {/* Large score top-right */}
              <span
                className="font-mono text-4xl font-bold leading-none"
                style={{
                  color: TIER_COLORS[result.composite_tier] || "var(--color-text-primary)",
                }}
              >
                {Math.round(result.composite_score)}
              </span>
            </div>

            {/* Tier + signal line */}
            <div className="flex items-center gap-1.5 mb-4">
              <span className="text-xs uppercase tracking-wider text-text-tertiary">
                {result.composite_tier}
              </span>
              <span className="text-xs text-text-tertiary">&middot;</span>
              <span className="text-xs text-text-secondary">
                {SIGNAL_LABELS[result.signal] || result.signal}
              </span>
            </div>

            {/* Elimination reason */}
            {result.eliminated && result.elimination_reason && (
              <p className="text-xs text-[var(--color-bearish)] mb-3 font-mono">
                Failed: {result.elimination_reason}
              </p>
            )}

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

            {/* CTA with arrow */}
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-1.5 text-sm text-accent hover:text-accent/80 transition-colors"
            >
              See the full forensic report
              <svg
                width={14}
                height={14}
                viewBox="0 0 14 14"
                fill="none"
                className="shrink-0"
              >
                <path
                  d="M3 7h8m0 0L8 4m3 3L8 10"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </Link>
          </div>
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
