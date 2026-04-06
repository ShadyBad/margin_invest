import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { WatchlistButton } from '../watchlist-button'

vi.mock('@/lib/api/watchlist', () => ({
  addToWatchlist: vi.fn(),
  removeFromWatchlist: vi.fn(),
}))

import { addToWatchlist, removeFromWatchlist } from '@/lib/api/watchlist'

const mockAdd = vi.mocked(addToWatchlist)
const mockRemove = vi.mocked(removeFromWatchlist)

describe('WatchlistButton', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders add state when not on watchlist', () => {
    render(<WatchlistButton ticker="AAPL" isOnWatchlist={false} />)
    expect(screen.getByText(/add to watchlist/i)).toBeInTheDocument()
  })

  it('renders on-watchlist state when already added', () => {
    render(<WatchlistButton ticker="AAPL" isOnWatchlist={true} />)
    expect(screen.getByText(/on watchlist/i)).toBeInTheDocument()
  })

  it('calls addToWatchlist on click when not added', async () => {
    mockAdd.mockResolvedValue({
      ticker: 'AAPL', name: null, sector: null,
      composite_score: null, composite_tier: null, signal: null,
      added_at: '2026-04-01T00:00:00Z',
    })
    render(<WatchlistButton ticker="AAPL" isOnWatchlist={false} />)
    await userEvent.click(screen.getByRole('button'))
    expect(mockAdd).toHaveBeenCalledWith('AAPL')
    await waitFor(() => {
      expect(screen.getByText(/on watchlist/i)).toBeInTheDocument()
    })
  })

  it('calls removeFromWatchlist on click when already added', async () => {
    mockRemove.mockResolvedValue(undefined)
    render(<WatchlistButton ticker="AAPL" isOnWatchlist={true} />)
    await userEvent.click(screen.getByRole('button'))
    expect(mockRemove).toHaveBeenCalledWith('AAPL')
  })
})
