import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ScoreNotificationStack } from '@/components/ScoreNotificationStack'

// Mock the hook
vi.mock('@/hooks/useScoreUpdates', () => ({
  useScoreUpdates: vi.fn(),
}))

import { useScoreUpdates } from '@/hooks/useScoreUpdates'

const mockUseScoreUpdates = vi.mocked(useScoreUpdates)

describe('ScoreNotificationStack', () => {
  beforeEach(() => {
    mockUseScoreUpdates.mockReturnValue({
      updates: [],
      connected: false,
      clearUpdate: vi.fn(),
    })
  })

  it('renders nothing when no updates', () => {
    const { container } = render(<ScoreNotificationStack />)
    expect(container.innerHTML).toBe('')
  })

  it('renders notifications when updates exist', () => {
    mockUseScoreUpdates.mockReturnValue({
      updates: [{
        ticker: 'AAPL',
        old_score: 70,
        new_score: 85,
        delta: 15,
        severity: 'major',
        timestamp: '2026-02-23T12:00:00Z',
        event_id: 'evt-001',
      }],
      connected: true,
      clearUpdate: vi.fn(),
    })

    render(<ScoreNotificationStack />)
    expect(screen.getByText('AAPL')).toBeDefined()
  })

  it('limits to 5 notifications', () => {
    const updates = Array.from({ length: 10 }, (_, i) => ({
      ticker: `T${i}`,
      old_score: 70,
      new_score: 85,
      delta: 15,
      severity: 'major' as const,
      timestamp: '2026-02-23T12:00:00Z',
      event_id: `evt-${i}`,
    }))

    mockUseScoreUpdates.mockReturnValue({
      updates,
      connected: true,
      clearUpdate: vi.fn(),
    })

    render(<ScoreNotificationStack />)
    const alerts = screen.getAllByRole('alert')
    expect(alerts).toHaveLength(5)
  })
})
