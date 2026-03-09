"use client"

interface PriceLadderProps {
  buyPrice: number | null
  currentPrice: number | null
  fairValue: number | null
  sellPrice: number | null
}

function formatPrice(v: number): string {
  return `$${v.toFixed(0)}`
}

/**
 * Horizontal price ladder showing buy/current/fair/sell positions.
 * Color-coded zones: green (below buy), neutral (buy-sell band), red (above sell).
 */
export function PriceLadder({ buyPrice, currentPrice, fairValue, sellPrice }: PriceLadderProps) {
  // Need at least buy and sell to render
  if (buyPrice == null || sellPrice == null) {
    return null
  }

  const min = Math.min(buyPrice, currentPrice ?? buyPrice, fairValue ?? buyPrice) * 0.95
  const max = Math.max(sellPrice, currentPrice ?? sellPrice, fairValue ?? sellPrice) * 1.05
  const range = max - min

  const toPercent = (v: number) => ((v - min) / range) * 100

  const buyPct = toPercent(buyPrice)
  const sellPct = toPercent(sellPrice)
  const fairPct = fairValue != null ? toPercent(fairValue) : null
  const currentPct = currentPrice != null ? toPercent(currentPrice) : null

  // Determine current price zone
  let zone: "buy" | "hold" | "sell" = "hold"
  if (currentPrice != null) {
    if (currentPrice <= buyPrice) zone = "buy"
    else if (currentPrice >= sellPrice) zone = "sell"
  }

  const zoneColors = {
    buy: "text-emerald-400",
    hold: "text-zinc-400",
    sell: "text-red-400",
  }

  return (
    <div className="mt-3 mb-1">
      {/* Price labels */}
      <div className="relative h-5 text-xs font-mono">
        <span className="absolute text-emerald-400/70" style={{ left: `${buyPct}%`, transform: "translateX(-50%)" }}>
          {formatPrice(buyPrice)}
        </span>
        {fairPct != null && fairValue != null && (
          <span className="absolute text-zinc-500" style={{ left: `${fairPct}%`, transform: "translateX(-50%)" }}>
            {formatPrice(fairValue)}
          </span>
        )}
        <span className="absolute text-red-400/70" style={{ left: `${sellPct}%`, transform: "translateX(-50%)" }}>
          {formatPrice(sellPrice)}
        </span>
      </div>

      {/* Bar */}
      <div className="relative h-2 rounded-full bg-white/[0.06] overflow-hidden">
        {/* Green zone (below buy) */}
        <div
          className="absolute top-0 bottom-0 bg-emerald-500/20 rounded-l-full"
          style={{ left: 0, width: `${buyPct}%` }}
        />
        {/* Neutral zone (buy to sell) */}
        <div
          className="absolute top-0 bottom-0 bg-white/[0.04]"
          style={{ left: `${buyPct}%`, width: `${sellPct - buyPct}%` }}
        />
        {/* Red zone (above sell) */}
        <div
          className="absolute top-0 bottom-0 bg-red-500/20 rounded-r-full"
          style={{ left: `${sellPct}%`, right: 0 }}
        />

        {/* Current price marker */}
        {currentPct != null && (
          <div
            className={`absolute top-[-2px] w-3 h-3 rounded-full border-2 border-bg-primary ${
              zone === "buy" ? "bg-emerald-400" : zone === "sell" ? "bg-red-400" : "bg-blue-400"
            }`}
            style={{ left: `${currentPct}%`, transform: "translateX(-50%)" }}
          />
        )}
      </div>

      {/* Current price label below */}
      {currentPct != null && currentPrice != null && (
        <div className="relative h-4 mt-1">
          <span
            className={`absolute text-xs font-mono font-medium ${zoneColors[zone]}`}
            style={{ left: `${currentPct}%`, transform: "translateX(-50%)" }}
          >
            {formatPrice(currentPrice)}
          </span>
        </div>
      )}

      {/* Zone labels */}
      <div className="flex justify-between text-[9px] text-zinc-600 mt-1">
        <span>Buy Zone</span>
        <span>Hold Zone</span>
        <span>Sell Zone</span>
      </div>
    </div>
  )
}
