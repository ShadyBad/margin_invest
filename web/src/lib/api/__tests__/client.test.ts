import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiFetch, ApiError } from '../client'

describe('apiFetch', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches data successfully', async () => {
    const mockData = { status: 'ok' }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData),
    })

    const result = await apiFetch('/health')
    expect(result).toEqual(mockData)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      }),
    )
  })

  it('throws ApiError on non-2xx response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve('Not found'),
    })

    await expect(apiFetch('/api/v1/scores/INVALID')).rejects.toThrow(ApiError)
    await expect(apiFetch('/api/v1/scores/INVALID')).rejects.toMatchObject({
      status: 404,
    })
  })

  it('handles 204 No Content', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
    })

    const result = await apiFetch('/api/v1/scores/AAPL')
    expect(result).toBeUndefined()
  })
})
