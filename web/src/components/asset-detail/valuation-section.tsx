"use client"

import { useState } from "react"
import { getValuationAudit } from "@/lib/api/scores"
import { FormulaTooltip } from "@/components/ui/formula-tooltip"
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

const METHOD_FORMULA_KEYS: Record<string, string> = {
  dcf: "dcf_valuation",
  ev_fcf: "ev_fcf_valuation",
  acquirers_multiple: "ev_ebit_valuation",
  shareholder_yield: "shareholder_yield_valuation",
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
      <div
        className="relative h-1 rounded-sm"
        style={{ background: "var(--color-surface-container-lowest)" }}
      >
        {/* Buy marker */}
        {buyPrice != null && (
          <div className="absolute -top-6" style={{ left: `${pct(buyPrice)}%` }}>
            <span
              className="text-xs block text-center transform -translate-x-1/2"
              style={{ fontFamily: "var(--font-data)", color: "var(--color-primary-muted)" }}
            >
              Buy
            </span>
            <span
              className="text-xs block text-center transform -translate-x-1/2"
              style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}
            >
              ${buyPrice.toFixed(0)}
            </span>
          </div>
        )}

        {/* Sell marker */}
        {sellPrice != null && (
          <div className="absolute -top-6" style={{ left: `${pct(sellPrice)}%` }}>
            <span
              className="text-xs block text-center transform -translate-x-1/2"
              style={{ fontFamily: "var(--font-data)", color: "var(--color-bearish)" }}
            >
              Sell
            </span>
            <span
              className="text-xs block text-center transform -translate-x-1/2"
              style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)" }}
            >
              ${sellPrice.toFixed(0)}
            </span>
          </div>
        )}

        {/* Intrinsic value marker */}
        {intrinsicValue != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-0.5 h-4"
            style={{ left: `${pct(intrinsicValue)}%`, background: "var(--color-primary-muted)" }}
          >
            <span
              className="absolute top-5 left-1/2 -translate-x-1/2 text-xs whitespace-nowrap"
              style={{ color: "var(--color-primary-muted)" }}
            >
              Intrinsic
            </span>
            <span
              className="absolute top-8 left-1/2 -translate-x-1/2 text-xs whitespace-nowrap"
              style={{ fontFamily: "var(--font-data)", color: "var(--color-primary-muted)" }}
            >
              ${intrinsicValue.toFixed(2)}
            </span>
          </div>
        )}

        {/* Current price marker */}
        {currentPrice != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full transform -translate-x-1/2"
            style={{
              left: `${pct(currentPrice)}%`,
              background: "var(--color-on-surface)",
              border: "2px solid var(--color-surface-container-low)",
            }}
          >
            <span
              className="absolute top-4 left-1/2 -translate-x-1/2 text-xs whitespace-nowrap"
              style={{ color: "var(--color-on-surface)" }}
            >
              Current
            </span>
            <span
              className="absolute top-7 left-1/2 -translate-x-1/2 text-xs whitespace-nowrap"
              style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}
            >
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
  const [auditError, setAuditError] = useState(false)

  const isOvervalued =
    currentPrice != null && intrinsicValue != null && currentPrice > intrinsicValue
  const entries = valuationMethods ? Object.entries(valuationMethods) : []

  async function handleAuditClick() {
    setShowAudit(!showAudit)
    if (!auditData && !auditLoading && !auditError) {
      setAuditLoading(true)
      try {
        const data = await getValuationAudit(ticker)
        setAuditData(data)
      } catch {
        setAuditError(true)
      } finally {
        setAuditLoading(false)
      }
    }
  }

  return (
    <section
      data-testid="valuation-section"
      className="rounded-lg p-6 space-y-4"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
      }}
    >
      <h2 className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
        VALUATION EVIDENCE
      </h2>

      {/* Unavailable state */}
      {intrinsicValue == null && (
        <div className="space-y-2">
          <p className="text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
            Intrinsic value unavailable.
          </p>
          {invalidReason && (
            <p className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
              Reason: {invalidReason}
            </p>
          )}
          <p className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
            Score-based assessment is still available above.
          </p>
        </div>
      )}

      {/* Price ruler */}
      {intrinsicValue != null && (
        <div>
          <PriceRuler
            buyPrice={buyPrice}
            sellPrice={sellPrice}
            intrinsicValue={intrinsicValue}
            currentPrice={currentPrice}
          />

          {/* Metrics */}
          <div className="flex items-center gap-6 text-sm mt-2">
            {priceUpside != null && (
              <div>
                <span className="text-label-sm block" style={{ color: "var(--color-on-surface-variant)" }}>
                  PRICE UPSIDE
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-data)",
                    color: priceUpside >= 0 ? "var(--color-bullish)" : "var(--color-bearish)",
                  }}
                >
                  {priceUpside >= 0 ? "+" : ""}
                  {(priceUpside * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {marginOfSafety != null && (
              <div>
                <span className="text-label-sm block" style={{ color: "var(--color-on-surface-variant)" }}>
                  MARGIN OF SAFETY
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-data)",
                    color: marginOfSafety >= 0 ? "var(--color-bullish)" : "var(--color-bearish)",
                  }}
                >
                  {marginOfSafety >= 0 ? "+" : ""}
                  {(marginOfSafety * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {/* Overvalued warning */}
          {isOvervalued && (
            <div className="mt-3 space-y-2">
              <div
                className="flex items-center gap-2 px-3 py-2 rounded-sm"
                style={{
                  background: "color-mix(in srgb, var(--color-warning) 10%, transparent)",
                  border: "1px solid color-mix(in srgb, var(--color-warning) 20%, transparent)",
                }}
              >
                <span style={{ color: "var(--color-warning)" }} className="text-sm">
                  Currently trading ABOVE intrinsic value
                </span>
              </div>
              <p className="text-xs px-1" style={{ color: "var(--color-text-tertiary)" }}>
                The composite score ranks quality, value, and momentum factors relative to the full
                universe. A stock can rank highly on these dimensions while trading above its
                intrinsic value estimate.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Valuation methods table */}
      {entries.length > 0 && (
        <div className="space-y-3 mt-4">
          <h3 className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
            VALUATION METHODS
          </h3>
          <div className="space-y-0">
            <div
              className="grid grid-cols-[1fr_100px_60px] gap-2 text-label-sm py-2 px-2"
              style={{ color: "var(--color-text-tertiary)" }}
            >
              <span>Method</span>
              <span className="text-right">Implied Value</span>
              <span className="text-right">Status</span>
            </div>
            {entries.map(([key, val], idx) => (
              <div
                key={key}
                className="grid grid-cols-[1fr_100px_60px] gap-2 text-xs items-center px-2 py-1.5 rounded-sm"
                style={{
                  background: idx % 2 === 0 ? "var(--color-surface)" : "var(--color-surface-container-lowest)",
                }}
              >
                <FormulaTooltip metricKey={METHOD_FORMULA_KEYS[key] ?? key}>
                  <span style={{ color: "var(--color-on-surface)" }}>{METHOD_LABELS[key] ?? key}</span>
                </FormulaTooltip>
                <span className="text-right" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
                  ${val.toFixed(2)}
                </span>
                <span className="text-right" style={{ color: "var(--color-bullish)" }}>Computed</span>
              </div>
            ))}
            {intrinsicValue != null && (
              <div
                className="grid grid-cols-[1fr_100px_60px] gap-2 text-xs items-center px-2 py-2 mt-2 rounded-sm"
                style={{ background: "var(--color-surface-container)" }}
              >
                <span className="font-semibold" style={{ color: "var(--color-on-surface)" }}>Blended Intrinsic Value</span>
                <span className="text-right font-semibold" style={{ fontFamily: "var(--font-data)", color: "var(--color-on-surface)" }}>
                  ${intrinsicValue.toFixed(2)}
                </span>
                <span />
              </div>
            )}
          </div>

          {/* Audit toggle */}
          <button
            className="text-label-sm transition-opacity hover:opacity-80"
            style={{ color: "var(--color-primary-muted)" }}
            onClick={handleAuditClick}
          >
            {showAudit ? "HIDE AUDIT TRAIL" : "VIEW AUDIT TRAIL"}
          </button>
          {showAudit && auditLoading && (
            <p className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>Loading audit data...</p>
          )}
          {showAudit && auditData && (
            <pre
              className="text-xs rounded-sm p-3 overflow-x-auto max-h-64"
              style={{
                fontFamily: "var(--font-data)",
                color: "var(--color-text-tertiary)",
                background: "var(--color-surface)",
              }}
            >
              {JSON.stringify(auditData, null, 2)}
            </pre>
          )}
          {showAudit && !auditLoading && !auditData && (
            <p className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>No audit data available</p>
          )}
        </div>
      )}
    </section>
  )
}
