import { apiFetch } from './client'
import type {
  UserWatchlistResponse,
  UserWatchlistItem,
  AlertListResponse,
  ScoreAlertItem,
  AlertCreateRequest,
} from './types'

export async function getWatchlist(): Promise<UserWatchlistResponse> {
  return apiFetch<UserWatchlistResponse>('/api/v1/me/watchlist')
}

export async function addToWatchlist(ticker: string): Promise<UserWatchlistItem> {
  return apiFetch<UserWatchlistItem>(`/api/v1/me/watchlist/${ticker}`, {
    method: 'POST',
  })
}

export async function removeFromWatchlist(ticker: string): Promise<void> {
  await apiFetch<void>(`/api/v1/me/watchlist/${ticker}`, {
    method: 'DELETE',
  })
}

export async function getAlerts(): Promise<AlertListResponse> {
  return apiFetch<AlertListResponse>('/api/v1/me/alerts')
}

export async function createAlert(request: AlertCreateRequest): Promise<ScoreAlertItem> {
  return apiFetch<ScoreAlertItem>('/api/v1/me/alerts', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export async function deleteAlert(alertId: number): Promise<void> {
  await apiFetch<void>(`/api/v1/me/alerts/${alertId}`, {
    method: 'DELETE',
  })
}
