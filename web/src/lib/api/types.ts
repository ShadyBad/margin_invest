export interface FilterResultResponse {
  name: string
  passed: boolean
  value: number | null
  threshold: number | null
  detail: string
  verdict: string
  missing_fields?: string[] | null
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
  score: number                // Raw weighted average — the true quality measure
  universe_percentile: number  // Universe-level rank (0-100)
  composite_percentile: number // Kept for backwards compat
  composite_raw_score: number  // Kept for backwards compat
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
  margin_invest_value: number | null
  buy_price: number | null
  sell_price: number | null
  actual_price: number | null
  price_upside: number | null
  margin_of_safety: number | null
  valuation_methods: Record<string, number> | null
  // Optional includes
  price_history?: PriceBar[] | null
  signal_history?: SignalTransition[] | null
  // v2 Conviction Engine fields
  opportunity_type?: string | null
  winning_track?: string | null
  asymmetry_ratio?: number | null
  max_position_pct?: number | null
  timing_signal?: string | null
  capital_allocation?: FactorBreakdownResponse | null
  catalyst?: FactorBreakdownResponse | null
  price_target_invalid_reason?: string | null
  // Asset context fields
  sector?: string | null
  universe_size?: number | null
  total_scored?: number | null
  filters_survived_count?: number | null
  sector_survivor_count?: number | null
  // V4 / ML fields
  ml_alpha?: number | null
  ml_confidence?: number | null
  ml_override?: string | null
  rules_conviction?: string | null
  style?: string | null
  regime?: string | null
  track_a?: Record<string, unknown> | null
  track_b?: Record<string, unknown> | null
  track_c?: Record<string, unknown> | null
  ml_model_qualified?: boolean | null
  ml_model_rank_ic?: number | null
  ml_model_trained_at?: string | null
}

export interface ScoreListResponse {
  scores: ScoreResponse[]
  total: number
  page: number
  page_size: number
}

export interface MetricStatus {
  value: number | null
  unavailable_reason: string | null
}

export interface InstitutionalMetricsResponse {
  sharpe_ratio: MetricStatus
  sharpe_ratio_3y: MetricStatus
  max_drawdown: MetricStatus
  max_drawdown_3y: MetricStatus
  volatility: MetricStatus
  volatility_3y: MetricStatus
  avg_profit_margin: MetricStatus
  delta: MetricStatus
  risk_classification: string
  margin_of_safety: MetricStatus
}

export interface PickSummary {
  score_id: number              // DB primary key for traceability
  ticker: string
  name: string
  score: number                // Raw weighted average
  universe_percentile: number  // Universe-level rank (0-100)
  composite_percentile: number // Kept for backwards compat
  conviction_level: string
  signal: string
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  sentiment_percentile?: number | null
  growth_percentile?: number | null
  actual_price: number | null
  buy_price: number | null
  sell_price: number | null
  price_upside: number | null
  data_freshness?: "fresh" | "stale" | "expired"
  scored_at?: string
  price_source?: "live" | "daily_close"
  price_updated_at?: string | null
  ingestion_status?: "complete" | "processing" | "failed" | "pending"
  // v2 Conviction Engine fields
  opportunity_type?: string | null
  winning_track?: string | null
  margin_of_safety?: number | null
  max_position_pct?: number | null
  timing_signal?: string | null
  sector?: string | null
  price_target_invalid_reason?: string | null
  // V4 / ML fields
  ml_override?: string | null
  style?: string | null
}

export interface WatchlistItem {
  ticker: string
  name: string
  composite_raw_score: number
  conviction_level: string
  sector?: string | null
  actual_price?: number | null
  price_upside?: number | null
  opportunity_type?: string | null
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

export interface ScoreHistoryPoint {
  scored_at: string
  composite_percentile: number
  composite_raw_score: number | null
  quality_percentile: number | null
  value_percentile: number | null
  momentum_percentile: number | null
  conviction_level: string
  signal: string
  margin_invest_value: number | null
  buy_price: number | null
  sell_price: number | null
  actual_price: number | null
  delta: number | null
}

export interface ScoreHistoryResponse {
  ticker: string
  points: ScoreHistoryPoint[]
  total_runs: number
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
  snapshots?: Array<{
    date: string
    portfolio_value: number
    benchmark_value: number
    portfolio_return: number
    benchmark_return: number
  }>
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

export interface MethodAuditResponse {
  method: string
  result_per_share: number | null
  weight: number
  renormalized_weight: number | null
  included: boolean
  exclusion_reason: string | null
  inputs: Record<string, number>
  intermediates: Record<string, number>
}

export interface ValuationAuditResponse {
  margin_invest_value: number | null
  margin_of_safety: number | null
  buy_price: number | null
  sell_price: number | null
  actual_price: number | null
  methods: MethodAuditResponse[]
  mos_base: number | null
  mos_cv: number | null
  mos_adjustment: number | null
  was_clamped: boolean
  clamp_reason: string | null
}

export interface BacktestTeaserResponse {
  ticker: string | null
  model_return: number
  benchmark_return: number
  max_drawdown: number
  benchmark_max_drawdown: number
  start_date: string
  end_date: string
}

export interface ExcludedTickerResponse {
  ticker: string
  reason: string
}

export interface CorrelationResponse {
  tickers: string[]
  method: string
  matrix: (number | null)[][]
  sample_sizes: number[][]
  excluded: ExcludedTickerResponse[]
  window_days: number
  computed_at: string
}
