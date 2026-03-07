"use client"

interface TooltipData {
  score: number
  delta?: number
  signal?: string
  conviction?: string
}

interface ChartTooltipProps {
  active?: boolean
  payload?: Array<{ payload?: TooltipData }>
  label?: string
}

export function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null

  const data = payload[0]?.payload
  if (!data) return null

  return (
    <div className="bg-bg-elevated/95 backdrop-blur-[8px] border border-border-subtle rounded-lg px-3 py-2 shadow-lg">
      <p className="text-[11px] font-mono text-text-tertiary">{label}</p>
      <p className="text-[20px] font-display text-accent leading-tight">{Math.round(data.score)}</p>
      {data.delta != null && (
        <p className={`text-[11px] font-mono ${data.delta >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {data.delta > 0 ? "+" : ""}{data.delta.toFixed(1)} pts
        </p>
      )}
      <div className="flex items-center gap-2 mt-0.5">
        {data.signal && (
          <span className="text-[10px] font-mono text-text-secondary uppercase">{data.signal}</span>
        )}
        {data.conviction && (
          <span className="text-[10px] font-mono text-text-tertiary uppercase">{data.conviction}</span>
        )}
      </div>
    </div>
  )
}
