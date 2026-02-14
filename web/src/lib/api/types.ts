export interface FilterResultResponse {
  name: string
  passed: boolean
  value: number | null
  threshold: number | null
  detail: string
  verdict: string
}

export interface FactorScoreResponse {
  name: string
  raw_value: number
  percentile_rank: number
  detail: string
}

export interface FactorBreakdownResponse {
  factor_name: string
  weight: number
  sub_scores: FactorScoreResponse[]
  average_percentile: number
}

export interface ScoreResponse {
  ticker: string
  name: string
  composite_percentile: number
  conviction_level: string
  signal: string
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  filters_passed: FilterResultResponse[]
  data_coverage: number
  growth_stage?: string
  scored_at?: string
}

export interface ScoreListResponse {
  scores: ScoreResponse[]
  total: number
  page: number
  page_size: number
}

export interface PickSummary {
  ticker: string
  name: string
  composite_percentile: number
  conviction_level: string
  signal: string
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
}

export interface WatchlistItem {
  ticker: string
  name: string
  composite_percentile: number
  conviction_level: string
}

export interface DashboardResponse {
  picks: PickSummary[]
  watchlist: WatchlistItem[]
  last_updated: string
  total_scored: number
}

export interface HealthResponse {
  status: string
  version: string
}

export interface BacktestConfig {
  start_date: string
  end_date: string | null
  rebalance_frequency: string
  top_percentile: number
  transaction_cost_bps: number
  slippage_bps: number
  benchmark_ticker: string
}

export interface BacktestMetrics {
  cagr: number
  excess_cagr: number
  sharpe_ratio: number
  sortino_ratio: number
  max_drawdown: number
  win_rate: number
  information_ratio: number
  total_return: number
  benchmark_total_return: number
  num_months: number
  avg_turnover: number
}

export interface ValidationCheck {
  name: string
  threshold: number
  actual: number
  passed: boolean
}

export interface BacktestValidation {
  overall_pass: boolean
  passed_count: number
  total_checks: number
  checks: ValidationCheck[]
}

export interface BacktestResult {
  config: BacktestConfig
  metrics: BacktestMetrics
  validation: BacktestValidation | null
  num_snapshots: number
  run_at: string
  duration_seconds: number
}

export interface BacktestSummary {
  id: string
  run_at: string
  config: BacktestConfig
  overall_pass: boolean | null
  excess_cagr: number
  sharpe_ratio: number
}

export interface BacktestListResponse {
  results: BacktestSummary[]
  total: number
}
