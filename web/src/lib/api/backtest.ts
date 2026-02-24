import { apiFetch } from "./client"
import type { BacktestResult, BacktestListResponse, FullBacktestResponse, ShadowPortfolioResponse } from "./types"

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

export async function getDefaultBacktest(): Promise<FullBacktestResponse> {
  return apiFetch<FullBacktestResponse>("/api/v1/backtest/default")
}

export async function runReplay(config: {
  start_date?: string
  end_date?: string | null
  rebalance_frequency?: string
  conviction_threshold?: number
  weighting?: string
  sector_exclusions?: string[]
  transaction_cost_bps?: number
}): Promise<FullBacktestResponse> {
  return apiFetch<FullBacktestResponse>("/api/v1/backtest/replay", {
    method: "POST",
    body: JSON.stringify(config),
  })
}

export async function getShadowPortfolio(): Promise<ShadowPortfolioResponse> {
  return apiFetch<ShadowPortfolioResponse>("/api/v1/backtest/shadow-portfolio")
}
