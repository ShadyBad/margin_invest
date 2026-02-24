import { apiFetch } from "./client"
import type { BacktestResult, BacktestListResponse, BacktestTeaserResponse } from "./types"

export async function getBacktestTeaser(ticker: string): Promise<BacktestTeaserResponse> {
  return apiFetch<BacktestTeaserResponse>(`/api/v1/backtest/teaser/${ticker}`)
}

export async function runBacktest(): Promise<BacktestResult> {
  return apiFetch<BacktestResult>("/api/v1/backtest/run", {
    method: "POST",
    body: JSON.stringify({}),
  })
}

export async function getBacktestResults(): Promise<BacktestListResponse> {
  return apiFetch<BacktestListResponse>("/api/v1/backtest/results")
}

export async function getBacktestResult(id: string): Promise<BacktestResult> {
  return apiFetch<BacktestResult>(`/api/v1/backtest/results/${id}`)
}
