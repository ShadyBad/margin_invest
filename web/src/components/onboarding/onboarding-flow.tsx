"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { TickerInput } from "./ticker-input"

type Stage = "input" | "scoring" | "results"

export function OnboardingFlow() {
  const [stage, setStage] = useState<Stage>("input")
  const [tickers, setTickers] = useState<string[]>([])
  const router = useRouter()

  const handleSubmit = async (inputTickers: string[]) => {
    setTickers(inputTickers)
    setStage("scoring")

    // Simulate scoring delay, then redirect to dashboard
    // In production, this would call the scoring API
    await new Promise((resolve) => setTimeout(resolve, 2000))
    router.push("/dashboard")
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
              {["Data", "Filter", "Score", "Rank"].map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full border border-accent/40 flex items-center justify-center text-[11px] font-mono text-accent animate-pulse">
                    {i + 1}
                  </div>
                  <span className="text-[12px] text-text-secondary">{step}</span>
                  {i < 3 && <span className="text-text-tertiary mx-1">&rarr;</span>}
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
