import type { PriceBar, ScoreResponse } from "@/lib/api/types"

export interface InstitutionalMetrics {
  sharpeRatio: number | null
  maxDrawdown: number
  volatility: number | null
  avgProfitMargin: number | null
  riskClassification: string
}

const RISK_FREE_RATE = 0.05
const TRADING_DAYS_PER_YEAR = 252
const MIN_BARS_FOR_STATS = 5

function dailyReturns(bars: PriceBar[]): number[] {
  const returns: number[] = []
  for (let i = 1; i < bars.length; i++) {
    if (bars[i - 1].close > 0) {
      returns.push((bars[i].close - bars[i - 1].close) / bars[i - 1].close)
    }
  }
  return returns
}

function mean(values: number[]): number {
  return values.reduce((sum, v) => sum + v, 0) / values.length
}

function stddev(values: number[]): number {
  const m = mean(values)
  const variance = values.reduce((sum, v) => sum + (v - m) ** 2, 0) / (values.length - 1)
  return Math.sqrt(variance)
}

export function computeSharpeRatio(bars: PriceBar[]): number | null {
  const returns = dailyReturns(bars)
  if (returns.length < MIN_BARS_FOR_STATS) return null

  const avgDailyReturn = mean(returns)
  const dailyStd = stddev(returns)
  if (dailyStd === 0) return null

  const dailyRiskFree = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
  const sharpe = ((avgDailyReturn - dailyRiskFree) / dailyStd) * Math.sqrt(TRADING_DAYS_PER_YEAR)
  return Math.round(sharpe * 100) / 100
}

export function computeMaxDrawdown(bars: PriceBar[]): number {
  let peak = -Infinity
  let maxDd = 0
  for (const bar of bars) {
    if (bar.close > peak) peak = bar.close
    const dd = (bar.close - peak) / peak
    if (dd < maxDd) maxDd = dd
  }
  return Math.round(maxDd * 10000) / 10000
}

export function computeVolatility(bars: PriceBar[]): number | null {
  const returns = dailyReturns(bars)
  if (returns.length < MIN_BARS_FOR_STATS) return null

  const annualized = stddev(returns) * Math.sqrt(TRADING_DAYS_PER_YEAR) * 100
  return Math.round(annualized * 10) / 10
}

function classifyRisk(volatility: number | null): string {
  if (volatility == null) return "Unknown"
  if (volatility > 40) return "Aggressive"
  if (volatility > 25) return "Moderate-High"
  if (volatility > 15) return "Moderate"
  return "Conservative"
}

export function computeInstitutionalMetrics(score: ScoreResponse): InstitutionalMetrics | null {
  if (!score.price_history || score.price_history.length === 0) return null

  const sorted = [...score.price_history].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )

  const volatility = computeVolatility(sorted)

  return {
    sharpeRatio: computeSharpeRatio(sorted),
    maxDrawdown: computeMaxDrawdown(sorted),
    volatility,
    avgProfitMargin: null,
    riskClassification: classifyRisk(volatility),
  }
}
