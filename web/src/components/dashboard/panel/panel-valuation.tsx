"use client"

import { useState } from "react"
import { PriceLadder } from "./price-ladder"
import { MethodAuditDetail } from "./method-audit-detail"
import { getValuationAudit } from "@/lib/api/scores"
import type { ValuationAuditResponse } from "@/lib/api/types"

const METHOD_LABELS: Record<string, string> = {
  dcf: "DCF Model",
  ev_fcf: "EV/FCF",
  acquirers_multiple: "EV/EBIT",
  shareholder_yield: "Shareholder Yield",
}

interface PanelValuationProps {
  ticker?: string
  marginInvestValue: number | null
  currentPrice: number | null
  marginOfSafety: number | null
  methods: Record<string, number> | null
  buyPrice?: number | null
  sellPrice?: number | null
}

export function PanelValuation({
  ticker,
  marginInvestValue,
  currentPrice,
  marginOfSafety,
  methods,
  buyPrice,
  sellPrice,
}: PanelValuationProps) {
  const [expandedMethod, setExpandedMethod] = useState<string | null>(null)
  const [auditData, setAuditData] = useState<ValuationAuditResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [auditError, setAuditError] = useState(false)

  const entries = methods ? Object.entries(methods) : []

  if (entries.length === 0 && marginInvestValue == null) {
    return (
      <div data-testid="panel-valuation">
        <h3 className="text-[14px] font-semibold text-text-primary mb-3">Valuation</h3>
        <p className="text-[13px] text-text-tertiary">No valuation data</p>
      </div>
    )
  }

  const maxValue = entries.length > 0 ? Math.max(...entries.map(([, v]) => v)) : 0

  async function handleMethodClick(method: string) {
    if (expandedMethod === method) {
      setExpandedMethod(null)
      return
    }
    setExpandedMethod(method)
    if (!auditData && !auditError && ticker) {
      setLoading(true)
      try {
        const data = await getValuationAudit(ticker)
        setAuditData(data)
      } catch {
        setAuditError(true)
      } finally {
        setLoading(false)
      }
    }
  }

  return (
    <div data-testid="panel-valuation">
      <h3 className="text-[14px] font-semibold text-text-primary mb-3">Valuation</h3>

      {/* Header trio: MIV, Current Price, MoS */}
      {marginInvestValue != null && (
        <div className="mb-2">
          <div className="grid grid-cols-3 gap-2">
            <div>
              <span className="text-[10px] text-text-secondary uppercase tracking-wider block">Margin Invest Value</span>
              <span className="text-[16px] font-mono text-text-primary font-medium">${marginInvestValue.toFixed(2)}</span>
            </div>
            {currentPrice != null && (
              <div>
                <span className="text-[10px] text-text-secondary uppercase tracking-wider block">Current Price</span>
                <span className="text-[16px] font-mono text-text-primary">${currentPrice.toFixed(2)}</span>
              </div>
            )}
            {marginOfSafety != null && (
              <div>
                <span className="text-[10px] text-text-secondary uppercase tracking-wider block">Margin of Safety</span>
                <span className={`text-[16px] font-mono font-medium ${
                  marginOfSafety > 0 ? "text-bullish" : "text-bearish"
                }`}>
                  {Math.round(marginOfSafety * 100)}%
                </span>
              </div>
            )}
          </div>

          {/* Price Ladder */}
          <PriceLadder
            buyPrice={buyPrice ?? null}
            currentPrice={currentPrice}
            fairValue={marginInvestValue}
            sellPrice={sellPrice ?? null}
          />
        </div>
      )}

      {/* Method breakdown bars */}
      {entries.length > 0 && (
        <div className="space-y-2.5 pt-3 border-t border-border-subtle">
          {entries.map(([key, value]) => {
            const isExpanded = expandedMethod === key
            const methodAudit = auditData?.methods.find((m) => m.method === key)

            return (
              <div key={key}>
                <div
                  className="flex items-center gap-3 cursor-pointer hover:bg-surface-overlay rounded px-1 -mx-1 py-0.5"
                  onClick={() => handleMethodClick(key)}
                  data-testid={`method-bar-${key}`}
                >
                  <span className="text-[12px] text-text-secondary w-[120px] shrink-0">
                    {METHOD_LABELS[key] ?? key}
                  </span>
                  <div className="flex-1 h-[3px] rounded-full bg-border-subtle">
                    <div
                      className="h-full rounded-full bg-accent/40"
                      style={{ width: `${(value / maxValue) * 100}%` }}
                    />
                  </div>
                  <span className="text-[12px] font-mono text-text-primary w-16 text-right">${value.toFixed(2)}</span>
                </div>
                {isExpanded && methodAudit && (
                  <MethodAuditDetail audit={methodAudit} />
                )}
                {isExpanded && loading && (
                  <div className="ml-[123px] py-2 text-[11px] text-text-tertiary">Loading audit data...</div>
                )}
                {isExpanded && !loading && !methodAudit && (
                  <div className="ml-[123px] py-2 text-[11px] text-text-tertiary">No audit data available</div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
