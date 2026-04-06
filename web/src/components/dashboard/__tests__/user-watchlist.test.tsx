import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UserWatchlist } from '../user-watchlist'

vi.mock('@/lib/api/watchlist', () => ({
  getWatchlist: vi.fn(),
  removeFromWatchlist: vi.fn(),
}))

import { getWatchlist, removeFromWatchlist } from '@/lib/api/watchlist'

const mockGetWatchlist = vi.mocked(getWatchlist)
const mockRemoveFromWatchlist = vi.mocked(removeFromWatchlist)

describe('UserWatchlist', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders empty state when no items', async () => {
    mockGetWatchlist.mockResolvedValue({ items: [], count: 0 })
    render(<UserWatchlist />)
    await waitFor(() => {
      expect(screen.getByText(/no tickers/i)).toBeInTheDocument()
    })
  })

  it('renders watchlist items with scores', async () => {
    mockGetWatchlist.mockResolvedValue({
      items: [{
        ticker: 'AAPL', name: 'Apple Inc.', sector: 'TECHNOLOGY',
        composite_score: 72.5, composite_tier: 'high', signal: null,
        added_at: '2026-04-01T00:00:00Z',
      }],
      count: 1,
    })
    render(<UserWatchlist />)
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument()
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
    })
  })

  it('removes item when delete button clicked', async () => {
    mockGetWatchlist.mockResolvedValue({
      items: [{
        ticker: 'AAPL', name: 'Apple Inc.', sector: 'TECHNOLOGY',
        composite_score: 72.5, composite_tier: 'high', signal: null,
        added_at: '2026-04-01T00:00:00Z',
      }],
      count: 1,
    })
    mockRemoveFromWatchlist.mockResolvedValue(undefined)
    render(<UserWatchlist />)
    await waitFor(() => { expect(screen.getByText('AAPL')).toBeInTheDocument() })
    const removeButton = screen.getByRole('button', { name: /remove/i })
    await userEvent.click(removeButton)
    expect(mockRemoveFromWatchlist).toHaveBeenCalledWith('AAPL')
  })
})
