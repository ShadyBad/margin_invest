import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ScoreNotification } from '@/components/ScoreNotification'
import type { ScoreUpdate } from '@/hooks/useScoreUpdates'

describe('ScoreNotification', () => {
  const update: ScoreUpdate = {
    ticker: 'AAPL',
    old_score: 70,
    new_score: 85,
    delta: 15,
    severity: 'major',
    timestamp: '2026-02-23T12:00:00Z',
    event_id: 'evt-001',
  }

  it('renders ticker and delta', () => {
    render(<ScoreNotification update={update} onDismiss={vi.fn()} />)
    expect(screen.getByText('AAPL')).toBeDefined()
    expect(screen.getByText(/\+15/)).toBeDefined()
  })

  it('calls onDismiss when close button clicked', () => {
    const onDismiss = vi.fn()
    render(<ScoreNotification update={update} onDismiss={onDismiss} />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(onDismiss).toHaveBeenCalledWith('evt-001')
  })

  it('shows severity indicator', () => {
    render(<ScoreNotification update={update} onDismiss={vi.fn()} />)
    expect(screen.getByText(/major/i)).toBeDefined()
  })

  it('shows negative delta without plus sign', () => {
    const negativeUpdate = { ...update, delta: -8, old_score: 85, new_score: 77 }
    render(<ScoreNotification update={negativeUpdate} onDismiss={vi.fn()} />)
    expect(screen.getByText(/-8/)).toBeDefined()
  })

  it('applies correct severity style for moderate', () => {
    const modUpdate = { ...update, severity: 'moderate' as const }
    render(<ScoreNotification update={modUpdate} onDismiss={vi.fn()} />)
    const alert = screen.getByRole('alert')
    expect(alert.className).toContain('border-l-amber-500')
  })
})
