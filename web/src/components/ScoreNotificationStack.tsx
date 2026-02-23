'use client'

import { useScoreUpdates } from '@/hooks/useScoreUpdates'
import { ScoreNotification } from '@/components/ScoreNotification'

export function ScoreNotificationStack() {
  const { updates, clearUpdate } = useScoreUpdates()

  if (updates.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
      {updates.slice(0, 5).map((update) => (
        <ScoreNotification
          key={update.event_id}
          update={update}
          onDismiss={clearUpdate}
        />
      ))}
    </div>
  )
}
