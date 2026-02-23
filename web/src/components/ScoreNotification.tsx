'use client'

import type { ScoreUpdate } from '@/hooks/useScoreUpdates'

const SEVERITY_STYLES = {
  major: 'border-l-red-500 bg-red-500/10',
  moderate: 'border-l-amber-500 bg-amber-500/10',
  minor: 'border-l-blue-500 bg-blue-500/10',
} as const

export function ScoreNotification({
  update,
  onDismiss,
}: {
  update: ScoreUpdate
  onDismiss: (eventId: string) => void
}) {
  const sign = update.delta > 0 ? '+' : ''

  return (
    <div
      className={`border-l-4 rounded-r-lg p-3 flex items-center justify-between gap-3 ${SEVERITY_STYLES[update.severity]}`}
      role="alert"
    >
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">{update.ticker}</span>
          <span className="text-xs uppercase opacity-70">{update.severity}</span>
        </div>
        <div className="text-xs opacity-80">
          Score: {update.old_score.toFixed(1)} → {update.new_score.toFixed(1)} ({sign}{update.delta.toFixed(1)})
        </div>
      </div>
      <button
        onClick={() => onDismiss(update.event_id)}
        className="text-xs opacity-50 hover:opacity-100"
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  )
}
