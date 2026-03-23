"use client"

import { useState, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api/client"
import { toast } from "sonner"
import posthog from "posthog-js"
import { TickerInput } from "./ticker-input"

type Stage = "input" | "scoring"

interface PublicScoreResult {
  ticker: string
  company_name: string
  composite_score: number
  composite_tier: string
  signal: string
  factor_summary: {
    quality_percentile: number
    value_percentile: number
    momentum_percentile: number
  }
  eliminated: boolean
  elimination_reason: string | null
  scored_at: string
}

const STEPS = ["Data", "Filter", "Score", "Rank"] as const

export function OnboardingFlow() {
  const [stage, setStage] = useState<Stage>("input")
  const [tickers, setTickers] = useState<string[]>([])
  const [completedSteps, setCompletedSteps] = useState(0)
  const router = useRouter()
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    posthog.capture("onboarding_started")
  }, [])

  const handleSubmit = async (inputTickers: string[]) => {
    setTickers(inputTickers)
    setStage("scoring")
    setCompletedSteps(0)

    abortRef.current = new AbortController()
    const timeout = setTimeout(() => abortRef.current?.abort(), 10000)

    try {
      posthog.capture("onboarding_step_completed", { step: "Data" })
      setCompletedSteps(1)

      const results = await Promise.all(
        inputTickers.map((ticker) =>
          apiFetch<PublicScoreResult>(
            `/api/v1/public/score/${ticker.toUpperCase()}`,
            { signal: abortRef.current!.signal }
          )
        )
      )

      posthog.capture("onboarding_step_completed", { step: "Filter" })
      setCompletedSteps(2)
      posthog.capture("onboarding_step_completed", { step: "Score" })
      setCompletedSteps(3)

      await new Promise((r) => setTimeout(r, 400))
      posthog.capture("onboarding_step_completed", { step: "Rank" })
      setCompletedSteps(4)

      clearTimeout(timeout)

      const firstTicker = results[0]?.ticker || inputTickers[0].toUpperCase()
      await new Promise((r) => setTimeout(r, 300))
      router.push(`/asset/${firstTicker}`)
    } catch {
      clearTimeout(timeout)
      toast.error("Scoring is taking longer than usual. Your results will appear on the dashboard shortly.")
      router.push("/dashboard")
    }
  }

  return (
    <div className="w-full max-w-[560px]">
      <div className="bg-bg-elevated/60 backdrop-blur-[16px] border border-border-subtle rounded-[8px] p-8 md:p-10">
        {stage === "input" && (
          <div className="flex flex-col items-center text-center">
            <h1 className="text-[28px] md:text-[32px] font-bold text-text-primary leading-tight tracking-[-0.3px] mb-2">
              Score your portfolio.
            </h1>
            <p className="text-[15px] text-text-secondary mb-8">
              Enter your tickers and see composite scores in 60 seconds.
            </p>
            <TickerInput onSubmit={handleSubmit} />
          </div>
        )}

        {stage === "scoring" && (
          <div className="flex flex-col items-center text-center py-8">
            <div className="flex items-center gap-3 mb-6">
              {STEPS.map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <div
                    className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs font-mono transition-colors ${
                      i < completedSteps
                        ? "border-accent bg-accent/10 text-accent"
                        : i === completedSteps
                          ? "border-accent/40 text-accent animate-pulse"
                          : "border-border-subtle text-text-tertiary"
                    }`}
                  >
                    {i < completedSteps ? "✓" : i + 1}
                  </div>
                  <span className="text-[12px] text-text-secondary">{step}</span>
                  {i < STEPS.length - 1 && (
                    <span className="text-text-tertiary mx-1">&rarr;</span>
                  )}
                </div>
              ))}
            </div>
            <p className="text-[15px] text-text-secondary">
              Scoring {tickers.join(", ")}...
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
