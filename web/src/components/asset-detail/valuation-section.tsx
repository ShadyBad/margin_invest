"use client"

import { useState } from "react"
import { getValuationAudit } from "@/lib/api/scores"
import type { ValuationAuditResponse } from "@/lib/api/types"

interface ValuationSectionProps {
  ticker: string
  buyPrice: number | null
  sellPrice: number | null
  intrinsicValue: number | null
  currentPrice: number | null
  priceUpside: number | null
  marginOfSafety: number | null
  valuationMethods: Record<string, number> | null
  invalidReason?: string | null
}

const METHOD_LABELS: Record<string, string> = {
  dcf: "DCF Model",
  ev_fcf: "EV/FCF",
  acquirers_multiple: "EV/EBIT",
  shareholder_yield: "Shareholder Yield",
}

function PriceRuler({
  buyPrice,
  sellPrice,
  intrinsicValue,
  currentPrice,
}: {
  buyPrice: number | null
  sellPrice: number | null
  intrinsicValue: number | null
  currentPrice: number | null
}) {
  const prices = [buyPrice, sellPrice, intrinsicValue, currentPrice].filter(
    (p): p is number => p != null
  )
  if (prices.length < 2) return null

  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1
  const pad = 0.1 * range
  const absMin = min - pad
  const absMax = max + pad
  const absRange = absMax - absMin

  function pct(val: number): number {
    return ((val - absMin) / absRange) * 100
  }

  return (
    <div className="relative py-8 px-4" data-testid="price-ruler">
      {/* Track */}
      <div className="relative h-1 bg-white/[0.08] rounded-full">
        {/* Buy marker */}
        {buyPrice != null && (
          <div className="absolute -top-6" style={{ left: `${pct(buyPrice)}%` }}>
            <span className="text-[10px] font-mono text-bullish block text-center transform -translate-x-1/2">
              Buy
            </span>
            <span className="text-xs font-mono text-text-secondary block text-center transform -translate-x-1/2">
              ${buyPrice.toFixed(0)}
            </span>
          </div>
        )}

        {/* Sell marker */}
        {sellPrice != null && (
          <div className="absolute -top-6" style={{ left: `${pct(sellPrice)}%` }}>
            <span className="text-[10px] font-mono text-bearish block text-center transform -translate-x-1/2">
              Sell
            </span>
            <span className="text-xs font-mono text-text-secondary block text-center transform -translate-x-1/2">
              ${sellPrice.toFixed(0)}
            </span>
          </div>
        )}

        {/* Intrinsic value marker */}
        {intrinsicValue != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-0.5 h-4 bg-accent"
            style={{ left: `${pct(intrinsicValue)}%` }}
          >
            <span className="absolute top-5 left-1/2 -translate-x-1/2 text-[10px] text-accent whitespace-nowrap">
              Intrinsic
            </span>
            <span className="absolute top-8 left-1/2 -translate-x-1/2 text-[10px] font-mono text-accent whitespace-nowrap">
              ${intrinsicValue.toFixed(2)}
            </span>
          </div>
        )}

        {/* Current price marker */}
        {currentPrice != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-text-primary border-2 border-bg-primary transform -translate-x-1/2"
            style={{ left: `${pct(currentPrice)}%` }}
          >
            <span className="absolute top-4 left-1/2 -translate-x-1/2 text-[10px] text-text-primary whitespace-nowrap">
              Current
            </span>
            <span className="absolute top-7 left-1/2 -translate-x-1/2 text-[10px] font-mono text-text-primary whitespace-nowrap">
              ${currentPrice.toFixed(2)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export function ValuationSection({
  ticker,
  buyPrice,
  sellPrice,
  intrinsicValue,
  currentPrice,
  priceUpside,
  marginOfSafety,
  valuationMethods,
  invalidReason,
}: ValuationSectionProps) {
  const [showAudit, setShowAudit] = useState(false)
  const [auditData, setAuditData] = useState<ValuationAuditResponse | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)

  const isOvervalued =
    currentPrice != null && intrinsicValue != null && currentPrice > intrinsicValue
  const entries = valuationMethods ? Object.entries(valuationMethods) : []

  async function handleAuditClick() {
    setShowAudit(!showAudit)
    if (!auditData && !auditLoading) {
      setAuditLoading(true)
      try {
        const data = await getValuationAudit(ticker)
        setAuditData(data)
      } catch {
        // Audit is optional enrichment
      } finally {
        setAuditLoading(false)
      }
    }
  }

  return (
    <section data-testid="valuation-section" className="space-y-4">
      <h2 className="text-lg font-semibold text-text-primary">Valuation</h2>

      {/* Unavailable state */}
      {intrinsicValue == null && (
        <div className="terminal-card p-4 space-y-2">
          <p className="text-sm text-text-secondary">Intrinsic value unavailable.</p>
          {invalidReason && (
            <p className="text-xs text-text-tertiary">Reason: {invalidReason}</p>
          )}
          <p className="text-xs text-text-tertiary">
            Score-based assessment is still available above.
          </p>
        </div>
      )}

      {/* Price ruler */}
      {intrinsicValue != null && (
        <div className="terminal-card p-4">
          <PriceRuler
            buyPrice={buyPrice}
            sellPrice={sellPrice}
            intrinsicValue={intrinsicValue}
            currentPrice={currentPrice}
          />

          {/* Metrics */}
          <div className="flex items-center gap-6 text-sm font-mono mt-2">
            {priceUpside != null && (
              <div>
                <span className="text-[10px] text-text-tertiary uppercase tracking-wider block">
                  Price Upside
                </span>
                <span className={priceUpside >= 0 ? "text-bullish" : "text-bearish"}>
                  {priceUpside >= 0 ? "+" : ""}
                  {(priceUpside * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {marginOfSafety != null && (
              <div>
                <span className="text-[10px] text-text-tertiary uppercase tracking-wider block">
                  Margin of Safety
                </span>
                <span className={marginOfSafety >= 0 ? "text-bullish" : "text-bearish"}>
                  {marginOfSafety >= 0 ? "+" : ""}
                  {(marginOfSafety * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {/* Overvalued warning */}
          {isOvervalued && (
            <div className="flex items-center gap-2 mt-3 px-3 py-2 rounded bg-warning/10 border border-warning/20">
              <span className="text-warning text-sm">
                Currently trading ABOVE intrinsic value
              </span>
            </div>
          )}
        </div>
      )}

      {/* Valuation methods table */}
      {entries.length > 0 && (
        <div className="terminal-card p-4 space-y-3">
          <h3 className="text-sm font-semibold text-text-secondary">Valuation Methods</h3>
          <div className="space-y-2">
            <div className="grid grid-cols-[1fr_100px_60px] gap-2 text-[10px] uppercase tracking-wider text-text-tertiary">
              <span>Method</span>
              <span className="text-right">Implied Value</span>
              <span className="text-right">Status</span>
            </div>
            {entries.map(([key, val]) => (
              <div
                key={key}
                className="grid grid-cols-[1fr_100px_60px] gap-2 text-xs items-center"
              >
                <span className="text-text-primary">{METHOD_LABELS[key] ?? key}</span>
                <span className="text-right font-mono text-text-primary">${val.toFixed(2)}</span>
                <span className="text-right text-bullish">Computed</span>
              </div>
            ))}
            {intrinsicValue != null && (
              <div className="grid grid-cols-[1fr_100px_60px] gap-2 text-xs items-center border-t border-white/[0.06] pt-2 mt-2">
                <span className="text-text-primary font-semibold">Blended Intrinsic Value</span>
                <span className="text-right font-mono text-text-primary font-semibold">
                  ${intrinsicValue.toFixed(2)}
                </span>
                <span />
              </div>
            )}
          </div>

          {/* Audit toggle */}
          <button
            className="text-xs text-accent hover:text-accent-hover transition-colors"
            onClick={handleAuditClick}
          >
            {showAudit ? "Hide" : "Full"} Valuation Audit (DCF scenarios, sensitivity analysis)
          </button>
          {showAudit && auditLoading && (
            <p className="text-xs text-text-tertiary">Loading audit data...</p>
          )}
          {showAudit && auditData && (
            <pre className="text-[10px] font-mono text-text-tertiary bg-white/[0.02] rounded p-3 overflow-x-auto max-h-64">
              {JSON.stringify(auditData, null, 2)}
            </pre>
          )}
        </div>
      )}
    </section>
  )
}
