import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getHealth } from '../health'

describe('Health API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('getHealth fetches health status', async () => {
    const mockHealth = { status: 'ok', version: '0.1.0' }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockHealth),
    })

    const result = await getHealth()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.any(Object),
    )
    expect(result).toEqual(mockHealth)
  })
})
