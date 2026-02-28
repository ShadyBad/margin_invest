interface SignalBadgeProps {
  signal: string
  className?: string
}

const signalStyles: Record<string, string> = {
  strong: "text-bullish",
  stable: "text-accent",
  weak: "text-bearish",
  emerging: "text-text-secondary",
  failed: "text-bearish font-bold",
  neutral: "text-text-tertiary",
  // Backward compat for any old signal values still in DB
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
