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

export interface PriceBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  adj_close: number | null
}

export interface SignalTransition {
  previous_signal: string
  new_signal: string
  previous_conviction: string
  new_conviction: string
  actual_price_at_transition: number | null
  intrinsic_value_at_transition: number | null
  composite_percentile: number
  transitioned_at: string
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
  // Price targets
  intrinsic_value: number | null
  buy_price: number | null
  sell_price: number | null
  actual_price: number | null
  price_upside: number | null
  margin_of_safety: number | null
  valuation_methods: Record<string, number> | null
  // Optional includes
  price_history?: PriceBar[] | null
  signal_history?: SignalTransition[] | null
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
  actual_price: number | null
  buy_price: number | null
  sell_price: number | null
  price_upside: number | null
  data_freshness?: "fresh" | "stale" | "expired"
  scored_at?: string
  price_source?: "live" | "daily_close"
  price_updated_at?: string | null
  ingestion_status?: "complete" | "processing" | "failed" | "pending"
}

export interface WatchlistItem {
  ticker: string
  name: string
  composite_percentile: number
  conviction_level: string
}

export interface UniverseSummary {
  version: string
  size: number
  scoring_coverage: number
  is_complete: boolean
  last_scoring_run: string | null
}

export interface Warning {
  code: string
  message: string
  severity: "warning" | "error"
}

export interface DashboardResponse {
  picks: PickSummary[]
  watchlist: WatchlistItem[]
  last_updated: string
  total_scored: number
  universe: UniverseSummary | null
  warnings?: Warning[]
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
