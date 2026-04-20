/**
 * 13F institutional holdings API client helpers.
 */
import { apiFetch } from "./client"

// ---------------------------------------------------------------------------
// Types matching Python Pydantic schemas (api/src/margin_api/schemas/thirteenf.py)
// ---------------------------------------------------------------------------

export interface HolderResponse {
  manager_name: string
  tier: string
  shares_held: number
  value_millions: number
  shares_changed: number
  pct_portfolio: number | null
  is_new_position: boolean
  quarters_held: number | null
}

export interface HoldingsSummary {
  total_holders: number
  curated_holders: number
  net_shares_changed: number
  signal_score: number
}

export interface HoldingsResponse {
  ticker: string
  period_of_report: string
  curated_holders: HolderResponse[]
  other_holders: HolderResponse[]
  summary: HoldingsSummary
}

export interface HoldingsHistoryQuarter {
  period: string
  curated_holders: number
  total_holders: number
  total_shares: number
  net_change: number
}

export interface HoldingsHistoryResponse {
  ticker: string
  quarters: HoldingsHistoryQuarter[]
}

export interface ManagerResponse {
  id: number
  name: string
  tier: string
  aum_millions: number | null
  total_holdings: number
  top_positions: string[]
  last_filing: string | null
  period_of_report: string | null
}

export interface PortfolioHolding {
  ticker: string | null
  cusip: string
  shares_held: number
  value_millions: number
  pct_portfolio: number
  shares_changed: number
  is_new_position: boolean
}

export interface ChangesSummary {
  new_positions: string[]
  exited_positions: string[]
  increased: number
  decreased: number
  unchanged: number
}

export interface ManagerPortfolioResponse {
  manager: string
  period_of_report: string
  aum_millions: number | null
  holdings: PortfolioHolding[]
  changes_summary: ChangesSummary
}

export interface OverlapEntry {
  ticker: string
  holder_count: number
  curated_count: number
}

export interface CrowdedTrade {
  ticker: string
  holder_count: number
  concentration_pct: number
  total_value_millions: number
}

export interface OverlapResponse {
  period_of_report: string
  most_held: OverlapEntry[]
  crowded_trades: CrowdedTrade[]
  total_managers: number | null
}

export interface NewPositionEntry {
  ticker: string
  managers: string[]
  total_new_funds: number
  curated_new_funds: number
  total_value_millions: number
}

export interface NewPositionResponse {
  period_of_report: string
  previous_quarter: string
  new_positions: NewPositionEntry[]
}

export interface ClonePosition {
  ticker: string
  target_weight: number
}

export interface ClonePerformance {
  return_1y: number | null
  cagr_3y: number | null
  max_drawdown: number | null
  sharpe: number | null
}

export interface CloneResponse {
  manager: string
  strategy: string
  period_of_report: string
  positions: ClonePosition[]
  historical_performance: ClonePerformance | null
}

// Market Pulse types

export interface SectorFlowItem {
  sector: string
  net_shares: number
  direction: "up" | "down" | "flat"
}

export interface ConsensusPick {
  ticker: string
  curated_holders: number
  agreement_pct: number
}

export interface MarketPulseResponse {
  breadth_pct: number
  breadth_direction: "up" | "down" | "flat"
  sector_flows: SectorFlowItem[]
  consensus_picks: ConsensusPick[]
  flow_trend_pct: number
  flow_trend_direction: "up" | "down" | "flat"
  as_of_quarter: string
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export function getHoldings(ticker: string): Promise<HoldingsResponse> {
  return apiFetch<HoldingsResponse>(`/api/v1/13f/holdings/${ticker.toUpperCase()}`)
}

export function getHoldingsHistory(ticker: string, limit = 10): Promise<HoldingsHistoryResponse> {
  return apiFetch<HoldingsHistoryResponse>(
    `/api/v1/13f/holdings/${ticker.toUpperCase()}/history?limit=${limit}`,
  )
}

export function getManagers(tier?: string): Promise<ManagerResponse[]> {
  const params = tier ? `?tier=${tier}` : ""
  return apiFetch<ManagerResponse[]>(`/api/v1/13f/managers${params}`)
}

export function getManagerPortfolio(
  managerId: number,
  period?: string,
): Promise<ManagerPortfolioResponse> {
  const params = period ? `?period=${period}` : ""
  return apiFetch<ManagerPortfolioResponse>(
    `/api/v1/13f/managers/${managerId}/portfolio${params}`,
  )
}

export function getOverlap(): Promise<OverlapResponse> {
  return apiFetch<OverlapResponse>("/api/v1/13f/analytics/overlap")
}

export function getNewPositions(): Promise<NewPositionResponse> {
  return apiFetch<NewPositionResponse>("/api/v1/13f/analytics/new-positions")
}

export function getClonePortfolio(
  managerId: number,
  strategy = "equal_weight_top_20",
): Promise<CloneResponse> {
  return apiFetch<CloneResponse>(
    `/api/v1/13f/analytics/clone/${managerId}?strategy=${strategy}`,
  )
}

export async function getMarketPulse(): Promise<MarketPulseResponse> {
  return apiFetch<MarketPulseResponse>("/api/v1/13f/analytics/market-pulse")
}
