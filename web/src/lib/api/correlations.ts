import { apiFetch } from './client'
import type { CorrelationResponse } from './types'

export async function getShowcaseCorrelations(): Promise<CorrelationResponse> {
  return apiFetch<CorrelationResponse>('/api/v1/correlations/showcase')
}
