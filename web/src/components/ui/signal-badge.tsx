interface SignalBadgeProps {
  signal: string
  className?: string
}

const signalStyles: Record<string, string> = {
  buy: "text-bullish",
  hold: "text-accent",
  sell: "text-bearish",
  watch: "text-text-secondary",
  "urgent sell": "text-bearish font-bold",
}

export function SignalBadge({ signal, className = "" }: SignalBadgeProps) {
  const style = signalStyles[signal.toLowerCase()] || "text-text-secondary"
  return (
    <span className={`text-sm font-medium uppercase tracking-wide ${style} ${className}`}>
      {signal}
    </span>
  )
}
