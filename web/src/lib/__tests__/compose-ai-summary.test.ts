import { describe, it, expect } from "vitest"
import { composeAiSummary } from "../compose-ai-summary"
import type { FactorBreakdownResponse, ScoreResponse } from "@/lib/api/types"

function makeFactor(name: string, percentile: number): FactorBreakdownResponse {
  return {
    factor_name: name,
    weight: 0.33,
    sub_scores: [],
    average_percentile: percentile,
  }
}

describe("composeAiSummary", () => {
  it("produces a summary string for a high-scoring stock", () => {
    const score = {
      ticker: "AAPL",
      name: "Apple Inc.",
      quality: makeFactor("quality", 88),
      value: makeFactor("value", 72),
      momentum: makeFactor("momentum", 65),
      score: 85,
    } as unknown as ScoreResponse

    const result = composeAiSummary(score)
    expect(result.summary.length).toBeGreaterThan(20)
    expect(result.summary).toContain("AAPL")
    expect(result.confidence).toBeGreaterThan(0)
    expect(result.confidence).toBeLessThanOrEqual(100)
  })

  it("produces lower confidence for mixed signals", () => {
    const highScore = {
      ticker: "GOOD",
      name: "Good Co",
      quality: makeFactor("quality", 90),
      value: makeFactor("value", 85),
      momentum: makeFactor("momentum", 80),
      score: 90,
    } as unknown as ScoreResponse

    const mixedScore = {
      ticker: "MIX",
      name: "Mixed Co",
      quality: makeFactor("quality", 90),
      value: makeFactor("value", 30),
      momentum: makeFactor("momentum", 20),
      score: 50,
    } as unknown as ScoreResponse

    const highResult = composeAiSummary(highScore)
    const mixedResult = composeAiSummary(mixedScore)
    expect(highResult.confidence).toBeGreaterThan(mixedResult.confidence)
  })

  it("mentions winning track when present", () => {
    const score = {
      ticker: "CMP",
      name: "Compounder Co",
      quality: makeFactor("quality", 85),
      value: makeFactor("value", 75),
      momentum: makeFactor("momentum", 60),
      winning_track: "compounder",
      score: 80,
    } as unknown as ScoreResponse

    const result = composeAiSummary(score)
    expect(result.summary.toLowerCase()).toContain("compounder")
  })
})
