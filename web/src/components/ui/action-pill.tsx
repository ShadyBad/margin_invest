interface ActionPillProps {
  signal: string
  buyPrice?: number | null
  sellPrice?: number | null
  actualPrice?: number | null
  className?: string
}

const pillConfig: Record<string, { bg: string; text: string; label: string }> = {
  strong: { bg: "bg-bullish/10", text: "text-bullish", label: "STRONG" },
  stable: { bg: "bg-accent/10", text: "text-accent", label: "STABLE" },
  weak: { bg: "bg-warning/10", text: "text-warning", label: "WEAK" },
  emerging: { bg: "bg-text-secondary/10", text: "text-text-secondary", label: "EMERGING" },
  failed: { bg: "bg-bearish/10", text: "text-bearish", label: "FAILED" },
  neutral: { bg: "bg-bg-secondary", text: "text-text-tertiary", label: "\u2014" },
  // Backward compat for old signal values
  buy: { bg: "bg-bullish/10", text: "text-bullish", label: "STRONG" },
  hold: { bg: "bg-accent/10", text: "text-accent", label: "STABLE" },
  sell: { bg: "bg-warning/10", text: "text-warning", label: "WEAK" },
  watch: { bg: "bg-text-secondary/10", text: "text-text-secondary", label: "EMERGING" },
  urgent_sell: { bg: "bg-bearish/10", text: "text-bearish", label: "FAILED" },
  no_action: { bg: "bg-bg-secondary", text: "text-text-tertiary", label: "\u2014" },
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
  if ((s === "strong" || s === "buy") && buyPrice != null) return `Below ${formatPrice(buyPrice)} target`
  if ((s === "stable" || s === "hold") && actualPrice != null && buyPrice != null && sellPrice != null) {
    return `Between ${formatPrice(buyPrice)} and ${formatPrice(sellPrice)}`
  }
  if ((s === "weak" || s === "sell") && sellPrice != null) return `Above ${formatPrice(sellPrice)} target`
  if ((s === "failed" || s === "urgent_sell") && actualPrice != null && sellPrice != null) {
    const pct = ((actualPrice - sellPrice) / sellPrice * 100)
    return `+${pct.toFixed(0)}% over target`
  }
  if (s === "emerging" || s === "watch") return "Monitoring"
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
