export interface FilterResultResponse {
  name: string
  passed: boolean
  reason?: string
}

export interface FactorScoreResponse {
  name: string
  raw_value: number
  percentile: number
  weight: number
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
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  growth_stage?: string
  factor_breakdown: Record<string, FactorBreakdownResponse>
  filters_passed: FilterResultResponse[]
  scored_at: string
  data_coverage?: number
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
