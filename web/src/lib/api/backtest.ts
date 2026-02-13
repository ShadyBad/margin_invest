import { apiFetch } from "./client"
import type { BacktestResult, BacktestListResponse } from "./types"

export async function runBacktest(): Promise<BacktestResult> {
  return apiFetch<BacktestResult>("/api/v1/backtest/run", { method: "POST" })
}

export async function getBacktestResults(): Promise<BacktestListResponse> {
  return apiFetch<BacktestListResponse>("/api/v1/backtest/results")
}

export async function getBacktestResult(id: string): Promise<BacktestResult> {
  return apiFetch<BacktestResult>(`/api/v1/backtest/results/${id}`)
}
