interface ActionPillProps {
  signal: string
  buyPrice?: number | null
  sellPrice?: number | null
  actualPrice?: number | null
  className?: string
}

const pillConfig: Record<string, { bg: string; text: string; label: string }> = {
  buy: { bg: "bg-bullish/10", text: "text-bullish", label: "BUY" },
  hold: { bg: "bg-accent/10", text: "text-accent", label: "HOLD" },
  sell: { bg: "bg-warning/10", text: "text-warning", label: "SELL" },
  watch: { bg: "bg-text-secondary/10", text: "text-text-secondary", label: "WATCH" },
  urgent_sell: { bg: "bg-bearish/10", text: "text-bearish", label: "SELL" },
  no_action: { bg: "bg-bg-secondary", text: "text-text-tertiary", label: "N/A" },
}

function formatPrice(price: number | null | undefined): string {
  if (price == null) return "N/A"
  return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function getSubtext(
  signal: string,
  buyPrice?: number | null,
  sellPrice?: number | null,
  actualPrice?: number | null,
): string {
  const s = signal.toLowerCase()
  if (s === "buy" && buyPrice != null) return `Buy below ${formatPrice(buyPrice)}`
  if (s === "hold" && actualPrice != null && buyPrice != null) {
    const pct = ((actualPrice - buyPrice) / buyPrice * 100)
    return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`
  }
  if (s === "sell" && sellPrice != null) return `Sell above ${formatPrice(sellPrice)}`
  if (s === "urgent_sell" && actualPrice != null && sellPrice != null) {
    const pct = ((actualPrice - sellPrice) / sellPrice * 100)
    return `+${pct.toFixed(0)}% over FV`
  }
  if (s === "watch") return "Monitoring"
  return ""
}

export function ActionPill({
  signal,
  buyPrice,
  sellPrice,
  actualPrice,
  className = "",
}: ActionPillProps) {
  const config = pillConfig[signal.toLowerCase()] ?? pillConfig.no_action
  const subtext = getSubtext(signal, buyPrice, sellPrice, actualPrice)

  return (
    <div
      className={`inline-flex flex-col items-center px-3 py-1.5 rounded-sm ${config.bg} ${className}`}
      data-testid="action-pill"
    >
      <span className={`text-sm font-semibold uppercase tracking-wide ${config.text}`}>
        {config.label}
      </span>
      {subtext && (
        <span className={`text-xs ${config.text} opacity-70`}>{subtext}</span>
      )}
    </div>
  )
}
