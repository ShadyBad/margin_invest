interface AuditEntry {
  date: string
  action: string
  universeSize: number
  selectedCount: number
  factorCoverage: number
  regime: string
  turnover: number
}

interface AuditLogProps {
  entries: AuditEntry[]
  maxHeight?: number
}

const COLUMNS = [
  "Date",
  "Action",
  "Universe",
  "Selected",
  "Coverage",
  "Regime",
  "Turnover",
] as const

const REGIME_COLORS: Record<string, string> = {
  bull: "bg-bullish",
  bear: "bg-bearish",
  recovery: "bg-accent",
  correction: "bg-warning",
}

function regimeDotClass(regime: string): string {
  return REGIME_COLORS[regime] ?? "bg-text-secondary"
}

export function AuditLog({ entries, maxHeight = 400 }: AuditLogProps) {
  return (
    <div className="terminal-card" data-testid="audit-log">
      <div className="p-4 border-b border-border-primary">
        <h3 className="text-xs font-semibold tracking-widest text-text-secondary">
          REBALANCE AUDIT LOG
        </h3>
      </div>

      {entries.length === 0 ? (
        <div className="p-4">
          <p className="text-text-secondary text-sm">No audit entries</p>
        </div>
      ) : (
        <div className="overflow-y-auto" style={{ maxHeight }}>
          <table className="w-full text-sm border-collapse" aria-label="Rebalance audit log">
            <thead className="sticky top-0 bg-bg-elevated z-10">
              <tr className="border-b border-border-primary">
                {COLUMNS.map((col) => (
                  <th
                    key={col}
                    scope="col"
                    className="text-left text-xs text-text-secondary font-medium px-3 py-2 whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, i) => (
                <tr
                  key={`${entry.date}-${i}`}
                  className={`border-b border-border-primary ${
                    i % 2 === 1 ? "bg-bg-elevated" : ""
                  }`}
                >
                  <td className="px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-text-primary whitespace-nowrap">
                    {entry.date}
                  </td>
                  <td className="px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-text-primary whitespace-nowrap">
                    {entry.action}
                  </td>
                  <td className="px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-text-primary whitespace-nowrap">
                    {entry.universeSize}
                  </td>
                  <td className="px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-text-primary whitespace-nowrap">
                    {entry.selectedCount}
                  </td>
                  <td className="px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-text-primary whitespace-nowrap">
                    {Math.round(entry.factorCoverage * 100)}%
                  </td>
                  <td className="px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-text-primary whitespace-nowrap">
                    <span className="inline-flex items-center gap-1.5">
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${regimeDotClass(entry.regime)}`}
                        aria-hidden="true"
                      />
                      {entry.regime}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-[family-name:var(--font-mono)] text-xs text-text-primary whitespace-nowrap">
                    {Math.round(entry.turnover * 100)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
