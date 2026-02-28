"use client"

interface ChartTooltipProps {
  active?: boolean
  payload?: Array<{ payload?: Record<string, unknown> }>
  label?: string
}

export function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null

  const data = payload[0]?.payload
  if (!data) return null

  return (
    <div className="bg-[rgba(17,17,19,0.8)] backdrop-blur-[8px] border border-white/[0.06] rounded-lg px-3 py-2 shadow-lg">
      <p className="text-[11px] font-mono text-[#5C5955]">{label}</p>
      <p className="text-[20px] font-display text-[#1A7A5A] leading-tight">{Math.round(data.score)}</p>
      {data.delta != null && (
        <p className={`text-[11px] font-mono ${data.delta >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {data.delta > 0 ? "+" : ""}{data.delta.toFixed(1)} pts
        </p>
      )}
      <div className="flex items-center gap-2 mt-0.5">
        {data.signal && (
          <span className="text-[10px] font-mono text-[#9A9590] uppercase">{data.signal}</span>
        )}
        {data.conviction && (
          <span className="text-[10px] font-mono text-[#5C5955] uppercase">{data.conviction}</span>
        )}
      </div>
    </div>
  )
}
