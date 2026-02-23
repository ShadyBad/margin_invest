'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

export interface ScoreUpdate {
  ticker: string
  old_score: number
  new_score: number
  delta: number
  severity: 'minor' | 'moderate' | 'major'
  timestamp: string
  event_id: string
}

const WS_URL = (process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, 'ws') ?? 'ws://localhost:8000') + '/ws/scores'
const HEARTBEAT_INTERVAL = 30_000
const RECONNECT_DELAY = 5_000

export function useScoreUpdates() {
  const [updates, setUpdates] = useState<ScoreUpdate[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearUpdate = useCallback((eventId: string) => {
    setUpdates(prev => prev.filter(u => u.event_id !== eventId))
  }, [])

  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
    let unmounted = false

    function connect() {
      if (unmounted) return
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, HEARTBEAT_INTERVAL)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ScoreUpdate
          if (data.ticker) {
            setUpdates(prev => [data, ...prev].slice(0, 50))
          }
        } catch {
          // Ignore non-JSON messages (pong, etc.)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (heartbeatRef.current) clearInterval(heartbeatRef.current)
        if (!unmounted) {
          reconnectTimeout = setTimeout(connect, RECONNECT_DELAY)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      unmounted = true
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      if (heartbeatRef.current) clearInterval(heartbeatRef.current)
      wsRef.current?.close()
    }
  }, [])

  return { updates, connected, clearUpdate }
}
