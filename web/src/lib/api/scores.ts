import { apiFetch } from './client'
import type { ScoreResponse, ScoreListResponse, InstitutionalMetricsResponse, ScoreHistoryResponse } from './types'

export interface ListScoresParams {
  page?: number
  page_size?: number
  min_percentile?: number
  conviction?: string
}

export async function getScore(
  ticker: string,
  include?: string[],
): Promise<ScoreResponse> {
  const params = include?.length ? `?include=${include.join(',')}` : ''
  return apiFetch<ScoreResponse>(`/api/v1/scores/${ticker.toUpperCase()}${params}`)
}

export async function getMetrics(
  ticker: string,
): Promise<InstitutionalMetricsResponse> {
  return apiFetch<InstitutionalMetricsResponse>(`/api/v1/scores/${ticker.toUpperCase()}/metrics`)
}

export async function listScores(params: ListScoresParams = {}): Promise<ScoreListResponse> {
  const searchParams = new URLSearchParams()
  if (params.page !== undefined) searchParams.set('page', String(params.page))
  if (params.page_size !== undefined) searchParams.set('page_size', String(params.page_size))
  if (params.min_percentile !== undefined) searchParams.set('min_percentile', String(params.min_percentile))
  if (params.conviction) searchParams.set('conviction', params.conviction)

  const query = searchParams.toString()
  return apiFetch<ScoreListResponse>(`/api/v1/scores${query ? `?${query}` : ''}`)
}

export async function getScoreHistory(ticker: string): Promise<ScoreHistoryResponse> {
  return apiFetch<ScoreHistoryResponse>(`/api/v1/scores/${ticker.toUpperCase()}/history`)
}

export async function deleteScore(ticker: string): Promise<void> {
  return apiFetch<void>(`/api/v1/scores/${ticker.toUpperCase()}`, {
    method: 'DELETE',
  })
}
