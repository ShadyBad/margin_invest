import { apiFetch } from './client'
import type { DashboardResponse } from './types'

export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>('/api/v1/dashboard')
}
