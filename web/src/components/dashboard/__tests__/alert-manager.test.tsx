import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AlertManager } from '../alert-manager'

vi.mock('@/lib/api/watchlist', () => ({
  getAlerts: vi.fn(),
  createAlert: vi.fn(),
  deleteAlert: vi.fn(),
}))

import { getAlerts, createAlert, deleteAlert } from '@/lib/api/watchlist'

const mockGetAlerts = vi.mocked(getAlerts)
const mockDeleteAlert = vi.mocked(deleteAlert)

describe('AlertManager', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders empty state', async () => {
    mockGetAlerts.mockResolvedValue({ items: [], count: 0 })
    render(<AlertManager />)
    await waitFor(() => {
      expect(screen.getByText(/no alerts/i)).toBeInTheDocument()
    })
  })

  it('renders existing alerts', async () => {
    mockGetAlerts.mockResolvedValue({
      items: [{
        id: 1, ticker: 'AAPL', alert_type: 'above' as const,
        threshold: 75.0, is_active: true, last_triggered_at: null,
        created_at: '2026-04-01T00:00:00Z',
      }],
      count: 1,
    })
    render(<AlertManager />)
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument()
      expect(screen.getByText(/above 75/i)).toBeInTheDocument()
    })
  })

  it('deletes alert when delete button clicked', async () => {
    mockGetAlerts.mockResolvedValue({
      items: [{
        id: 1, ticker: 'AAPL', alert_type: 'above' as const,
        threshold: 75.0, is_active: true, last_triggered_at: null,
        created_at: '2026-04-01T00:00:00Z',
      }],
      count: 1,
    })
    mockDeleteAlert.mockResolvedValue(undefined)
    render(<AlertManager />)
    await waitFor(() => { expect(screen.getByText('AAPL')).toBeInTheDocument() })
    const deleteButton = screen.getByRole('button', { name: /delete/i })
    await userEvent.click(deleteButton)
    expect(mockDeleteAlert).toHaveBeenCalledWith(1)
  })
})
