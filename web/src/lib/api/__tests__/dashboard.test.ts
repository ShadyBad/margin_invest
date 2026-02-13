import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getDashboard } from '../dashboard'

describe('Dashboard API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('getDashboard fetches dashboard data', async () => {
    const mockDashboard = {
      picks: [],
      watchlist: [],
      last_updated: '2026-02-12T00:00:00Z',
      total_scored: 0,
    }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockDashboard),
    })

    const result = await getDashboard()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dashboard'),
      expect.any(Object),
    )
    expect(result).toEqual(mockDashboard)
  })
})
