import { apiFetch } from './client'
import type { CorrelationResponse } from './types'

export async function getCorrelations(
  method: 'returns' | 'factors',
  tickers?: string[],
  window?: number,
): Promise<CorrelationResponse> {
  const params = new URLSearchParams({ method })
  if (tickers?.length) params.set('tickers', tickers.join(','))
  if (window !== undefined) params.set('window', String(window))
  return apiFetch<CorrelationResponse>(`/api/v1/correlations?${params}`)
}

export async function getShowcaseCorrelations(): Promise<CorrelationResponse> {
  return apiFetch<CorrelationResponse>('/api/v1/correlations/showcase')
}
