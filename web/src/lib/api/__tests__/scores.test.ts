import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getScore, listScores, deleteScore } from '../scores'

describe('Score API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('getScore fetches a single score', async () => {
    const mockScore = { ticker: 'AAPL', composite_percentile: 85 }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockScore),
    })

    const result = await getScore('aapl')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/scores/AAPL'),
      expect.any(Object),
    )
    expect(result).toEqual(mockScore)
  })

  it('listScores builds query string', async () => {
    const mockList = { scores: [], total: 0, page: 1, page_size: 50 }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockList),
    })

    await listScores({ page: 2, conviction: 'high' })
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('page=2'),
      expect.any(Object),
    )
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('conviction=high'),
      expect.any(Object),
    )
  })

  it('deleteScore sends DELETE request', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
    })

    await deleteScore('MSFT')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/scores/MSFT'),
      expect.objectContaining({ method: 'DELETE' }),
    )
  })
})
