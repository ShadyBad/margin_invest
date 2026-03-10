export interface CandidateCard {
  ticker: string
  name: string
  sector: string
  actual_price: number
  buy_price: number
  margin_of_safety: number
  score: number                  // Raw weighted composite (0-100) — displayed as Composite Score
  composite_percentile: number   // Percentile rank — kept for factor bar compat
  composite_tier: string
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  sentiment_percentile: number
  growth_percentile: number
  scored_at: string
  filters_passed: number
  filters_total: number
}

export interface HomepageData {
  candidates: CandidateCard[]
  allPicks: CandidateCard[]
  last_updated: string
  universe_size: number
  eligible_count: number
  total_scored: number
  total_universe: number
  surviving_count: number
  isFallback?: boolean
}
