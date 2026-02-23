import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useScoreUpdates } from '@/hooks/useScoreUpdates'

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  onopen: (() => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  readyState = 0

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
    setTimeout(() => {
      this.readyState = 1
      this.onopen?.()
    }, 0)
  }

  send = vi.fn()
  close = vi.fn()
}

describe('useScoreUpdates', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('connects to ws/scores endpoint', async () => {
    renderHook(() => useScoreUpdates())
    await vi.advanceTimersByTimeAsync(0)
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toContain('/ws/scores')
  })

  it('returns score update messages', async () => {
    const { result } = renderHook(() => useScoreUpdates())
    await vi.advanceTimersByTimeAsync(0)

    const ws = MockWebSocket.instances[0]
    act(() => {
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          ticker: 'AAPL',
          old_score: 70,
          new_score: 85,
          delta: 15,
          severity: 'major',
          timestamp: '2026-02-23T12:00:00Z',
          event_id: 'evt-001',
        }),
      }))
    })

    expect(result.current.updates).toHaveLength(1)
    expect(result.current.updates[0].ticker).toBe('AAPL')
  })

  it('reports connected state', async () => {
    const { result } = renderHook(() => useScoreUpdates())
    expect(result.current.connected).toBe(false)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(result.current.connected).toBe(true)
  })

  it('clearUpdate removes by event_id', async () => {
    const { result } = renderHook(() => useScoreUpdates())
    await vi.advanceTimersByTimeAsync(0)

    const ws = MockWebSocket.instances[0]
    act(() => {
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          ticker: 'AAPL',
          old_score: 70,
          new_score: 85,
          delta: 15,
          severity: 'major',
          timestamp: '2026-02-23T12:00:00Z',
          event_id: 'evt-001',
        }),
      }))
    })

    expect(result.current.updates).toHaveLength(1)

    act(() => {
      result.current.clearUpdate('evt-001')
    })

    expect(result.current.updates).toHaveLength(0)
  })

  it('ignores non-JSON messages', async () => {
    const { result } = renderHook(() => useScoreUpdates())
    await vi.advanceTimersByTimeAsync(0)

    const ws = MockWebSocket.instances[0]
    act(() => {
      ws.onmessage?.(new MessageEvent('message', { data: 'pong' }))
    })

    expect(result.current.updates).toHaveLength(0)
  })
})
