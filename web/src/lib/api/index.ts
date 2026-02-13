export { apiFetch, ApiError } from './client'
export { getScore, listScores, deleteScore } from './scores'
export { getDashboard } from './dashboard'
export { getHealth } from './health'
export { runBacktest, getBacktestResults, getBacktestResult } from './backtest'
export type {
  ScoreResponse,
  ScoreListResponse,
  DashboardResponse,
  PickSummary,
  WatchlistItem,
  FactorBreakdownResponse,
  FactorScoreResponse,
  FilterResultResponse,
  HealthResponse,
  BacktestConfig,
  BacktestMetrics,
  ValidationCheck,
  BacktestValidation,
  BacktestResult,
  BacktestSummary,
  BacktestListResponse,
} from './types'
