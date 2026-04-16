"use client"

import { useState, useRef, type FormEvent } from "react"
import Link from "next/link"
import posthog from "posthog-js"
import { apiFetch, ApiError } from "@/lib/api/client"
import { formatScore } from "@/lib/format"

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

    posthog.capture("asset_searched", { query: ticker })
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
      <form onSubmit={handleSubmit} className="flex gap-2 max-w-md mx-auto">
        {/* Input container with focus ring */}
        <div
          ref={containerRef}
          className="flex-1 flex items-center gap-2 px-3 py-3 rounded-md transition-all"
          style={{
            background: "var(--color-surface-container-lowest)",
            border: inputFocused ? "1px solid var(--color-primary)" : "1px solid transparent",
            boxShadow: inputFocused
              ? "0 0 0 3px rgba(128,216,178,0.12)"
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
            className="flex-1 bg-transparent text-sm placeholder:text-[var(--color-text-tertiary)] focus:outline-none"
            style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}
            disabled={state === "loading"}
          />
        </div>
        <button
          type="submit"
          disabled={state === "loading" || !query.trim()}
          aria-label="Search"
          className="px-5 py-3 font-medium text-sm hover:opacity-90 transition-colors disabled:opacity-50"
          style={{
            background: "var(--color-primary-container)",
            color: "var(--color-on-primary-container)",
            borderRadius: "0.375rem",
          }}
        >
          {state === "loading" ? (
            <span data-testid="hero-search-loading" className="inline-block w-4 h-4 border-2 border-[var(--color-on-primary-container)] border-t-transparent rounded-full animate-spin" />
          ) : (
            "Search"
          )}
        </button>
      </form>

      {/* Ticker suggestion chips */}
      {state === "idle" && (
        <div className="flex items-center justify-center gap-2 mt-4 flex-wrap">
          <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>Try:</span>
          {["AAPL", "TSLA", "JNJ", "COST", "ETSY"].map((ticker) => (
            <button
              key={ticker}
              type="button"
              onClick={() => {
                posthog.capture("asset_searched", { query: ticker })
                setQuery(ticker)
                setState("loading")
                setError("")
                setResult(null)
                apiFetch<PublicScoreResult>(`/api/v1/public/score/${ticker}`)
                  .then((data) => {
                    setResult(data)
                    setState("result")
                  })
                  .catch((err) => {
                    if (err instanceof ApiError && err.status === 404) {
                      setError("Ticker not found. Check the symbol and try again.")
                    } else {
                      setError("Something went wrong. Please try again.")
                    }
                    setState("error")
                  })
              }}
              className="text-xs transition-colors px-2 py-1 rounded-sm"
              style={{
                fontFamily: "var(--font-data)",
                color: "var(--color-primary)",
                border: "1px solid var(--color-ghost-border)",
              }}
            >
              {ticker}
            </button>
          ))}
        </div>
      )}

      {/* Result card */}
      {state === "result" && result && (
        <div
          className="relative overflow-hidden rounded-lg mt-4 max-w-md mx-auto animate-in fade-in duration-200"
          style={{
            background: "var(--color-surface-container-low)",
            border: "1px solid var(--color-ghost-border)",
            boxShadow: "0 0 24px 0 rgba(128,216,178,0.04)",
          }}
        >
          <div className="p-5">
            {/* Header: ticker + name (left) + score (right) */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <span
                  className="text-lg font-bold"
                  style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}
                >
                  {result.ticker}
                </span>
                <span className="text-sm ml-2" style={{ color: "var(--color-on-surface-variant)" }}>
                  {result.company_name}
                </span>
                {result.eliminated && (
                  <span
                    className="ml-2 text-xs uppercase tracking-wider px-2 py-0.5 rounded-sm"
                    style={{
                      fontFamily: "var(--font-data)",
                      color: "var(--color-bearish)",
                      background: "color-mix(in srgb, var(--color-bearish) 10%, transparent)",
                    }}
                  >
                    Eliminated
                  </span>
                )}
              </div>

              {/* Large score top-right */}
              <span
                className="text-4xl font-bold leading-none"
                style={{
                  fontFamily: "var(--font-data)",
                  color: TIER_COLORS[result.composite_tier] || "var(--color-on-surface)",
                }}
              >
                {formatScore(result.composite_score)}
              </span>
            </div>

            {/* Tier + signal line */}
            <div className="flex items-center gap-1.5 mb-4">
              <span className="text-xs uppercase tracking-wider" style={{ color: "var(--color-text-tertiary)" }}>
                {result.composite_tier}
              </span>
              <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>&middot;</span>
              <span className="text-xs" style={{ color: "var(--color-on-surface-variant)" }}>
                {SIGNAL_LABELS[result.signal] || result.signal}
              </span>
            </div>

            {/* Elimination reason */}
            {result.eliminated && result.elimination_reason && (
              <p className="text-xs mb-3" style={{ fontFamily: "var(--font-data)", color: "var(--color-bearish)" }}>
                Failed: {result.elimination_reason}
              </p>
            )}

            {/* Factor bars */}
            <div className="space-y-2 mb-4">
              {factors.map((factor) => (
                <div key={factor.label} className="flex items-center gap-2">
                  <span className="text-xs w-20 shrink-0" style={{ color: "var(--color-on-surface-variant)" }}>
                    {factor.label}
                  </span>
                  <div className="flex-1 h-1.5 rounded-sm overflow-hidden" style={{ background: "var(--color-surface-container-lowest)" }}>
                    <div
                      className="h-full rounded-sm transition-all duration-500"
                      style={{ width: `${factor.value}%`, background: "var(--color-primary-container)" }}
                    />
                  </div>
                  <span className="text-xs w-8 text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}>
                    {Math.round(factor.value)}
                  </span>
                </div>
              ))}
            </div>

            {/* CTA with arrow */}
            <Link
              href={`/asset/${result.ticker}`}
              className="inline-flex items-center gap-1.5 text-sm transition-colors hover:opacity-80"
              style={{ color: "var(--color-primary)" }}
            >
              View full forensic report
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
        <p className="text-sm text-[var(--color-bearish)] mt-3 max-w-md mx-auto text-center">
          {error}
        </p>
      )}
    </div>
  )
}
