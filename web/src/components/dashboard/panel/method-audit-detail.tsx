import type { MethodAuditResponse } from "@/lib/api/types"

function formatLargeNumber(n: number): string {
  const abs = Math.abs(n)
  if (abs >= 1e12) return `${(n / 1e12).toFixed(2)}T`
  if (abs >= 1e9) return `${(n / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${(n / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return n.toFixed(2)
}

function formatKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

interface MethodAuditDetailProps {
  audit: MethodAuditResponse
}

export function MethodAuditDetail({ audit }: MethodAuditDetailProps) {
  const inputEntries = Object.entries(audit.inputs)
  const intermediateEntries = Object.entries(audit.intermediates)

  return (
    <div
      className="mt-1.5 mb-2 ml-[123px] pl-3 border-l border-white/[0.06] space-y-2"
      data-testid="method-audit-detail"
    >
      {/* Inclusion status */}
      <div className="flex items-center gap-2">
        {audit.included ? (
          <span className="text-[10px] font-mono text-[#1A7A5A] bg-[#1A7A5A]/10 px-1.5 py-0.5 rounded">
            Included
          </span>
        ) : (
          <span className="text-[10px] font-mono text-[#C74B50] bg-[#C74B50]/10 px-1.5 py-0.5 rounded">
            Excluded
          </span>
        )}
        {audit.exclusion_reason && (
          <span className="text-[10px] font-mono text-[#9A9590]">
            {audit.exclusion_reason}
          </span>
        )}
      </div>

      {/* Weight and result */}
      <div className="flex gap-4 text-[11px] font-mono">
        {audit.result_per_share != null && (
          <span className="text-[#E8E6E3]">
            Result: ${audit.result_per_share.toFixed(2)}
          </span>
        )}
        <span className="text-[#9A9590]">
          Weight: {(audit.weight * 100).toFixed(0)}%
        </span>
        {audit.renormalized_weight != null && (
          <span className="text-[#9A9590]">
            Renorm: {(audit.renormalized_weight * 100).toFixed(1)}%
          </span>
        )}
      </div>

      {/* Inputs and intermediates in two columns */}
      {(inputEntries.length > 0 || intermediateEntries.length > 0) && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {inputEntries.length > 0 && (
            <div>
              <span className="text-[10px] text-[#5C5955] uppercase tracking-wider">
                Inputs
              </span>
              {inputEntries.map(([key, value]) => (
                <div
                  key={key}
                  className="flex justify-between text-[10px] font-mono"
                >
                  <span className="text-[#9A9590]">{formatKey(key)}</span>
                  <span className="text-[#E8E6E3]">
                    {formatLargeNumber(value)}
                  </span>
                </div>
              ))}
            </div>
          )}
          {intermediateEntries.length > 0 && (
            <div>
              <span className="text-[10px] text-[#5C5955] uppercase tracking-wider">
                Intermediates
              </span>
              {intermediateEntries.map(([key, value]) => (
                <div
                  key={key}
                  className="flex justify-between text-[10px] font-mono"
                >
                  <span className="text-[#9A9590]">{formatKey(key)}</span>
                  <span className="text-[#E8E6E3]">
                    {formatLargeNumber(value)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
