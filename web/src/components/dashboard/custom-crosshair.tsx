interface PayloadItem {
  dataKey: string
  value: number
  color: string
}

interface CustomCrosshairProps {
  active: boolean
  payload: PayloadItem[]
  label: string
}

function formatVolume(vol: number): string {
  if (vol >= 1_000_000_000) return `${(vol / 1_000_000_000).toFixed(1)}B`
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`
  return vol.toString()
}

export function CustomCrosshair({ active, payload, label }: CustomCrosshairProps) {
  if (!active || !payload || payload.length === 0) return null

  const close = payload.find((p) => p.dataKey === "close")
  const volume = payload.find((p) => p.dataKey === "volume")

  return (
    <div className="bg-bg-elevated border border-border-primary shadow-modal rounded-sm px-3 py-2 text-xs">
      <div className="font-mono text-text-tertiary mb-1">{label}</div>
      {close && (
        <div className="flex justify-between gap-4">
          <span className="text-text-secondary">Close</span>
          <span className="font-mono font-bold text-text-primary">
            ${close.value.toFixed(2)}
          </span>
        </div>
      )}
      {volume && (
        <div className="flex justify-between gap-4">
          <span className="text-text-secondary">Volume</span>
          <span className="font-mono text-text-primary">
            {formatVolume(volume.value)}
          </span>
        </div>
      )}
    </div>
  )
}
