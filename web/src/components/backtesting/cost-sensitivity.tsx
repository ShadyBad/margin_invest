"use client"

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import type { CostSensitivityRow } from "@/lib/api/types"

interface CostSensitivityProps {
  rows: CostSensitivityRow[]
}

const MULTIPLIER_LABELS: Record<number, string> = {
  1: "Base (1x)",
  2: "Conservative (2x)",
  3: "Stress (3x)",
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function formatBps(value: number): string {
  return `${Math.round(value)} bps`
}

export function CostSensitivity({ rows }: CostSensitivityProps) {
  if (rows.length === 0) {
    return (
      <div className="terminal-card p-4" data-testid="cost-sensitivity">
        <h3 className="text-xs font-semibold tracking-widest text-text-secondary mb-4">
          COST SENSITIVITY
        </h3>
        <p className="text-sm text-text-secondary">No sensitivity data available.</p>
      </div>
    )
  }

  const chartData = rows.map((r) => ({
    multiplier: MULTIPLIER_LABELS[r.multiplier] ?? `${r.multiplier}x`,
    CAGR: +(r.cagr * 100).toFixed(2),
    Sharpe: +r.sharpe.toFixed(2),
  }))

  return (
    <div className="terminal-card p-4" data-testid="cost-sensitivity">
      <h3 className="text-xs font-semibold tracking-widest text-text-secondary mb-4">
        COST SENSITIVITY
      </h3>

      {/* Chart */}
      <div className="mb-6" style={{ width: "100%", height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="multiplier"
              tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }}
            />
            <YAxis tick={{ fontSize: 11, fill: "var(--color-text-secondary)" }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border)",
                borderRadius: 4,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="CAGR"
              stroke="var(--color-accent)"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="Sharpe"
              stroke="var(--color-bullish)"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-primary">
              <th className="text-left py-2 pr-4 text-text-secondary font-medium">Metric</th>
              {rows.map((r) => (
                <th
                  key={r.multiplier}
                  className="text-right py-2 px-2 text-text-secondary font-medium"
                >
                  {MULTIPLIER_LABELS[r.multiplier] ?? `${r.multiplier}x`}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border-primary/50">
              <td className="py-2 pr-4 text-text-secondary">CAGR</td>
              {rows.map((r) => (
                <td key={r.multiplier} className="text-right py-2 px-2 text-text-primary">
                  {formatPct(r.cagr)}
                </td>
              ))}
            </tr>
            <tr className="border-b border-border-primary/50">
              <td className="py-2 pr-4 text-text-secondary">Sharpe</td>
              {rows.map((r) => (
                <td key={r.multiplier} className="text-right py-2 px-2 text-text-primary">
                  {r.sharpe.toFixed(2)}
                </td>
              ))}
            </tr>
            <tr className="border-b border-border-primary/50">
              <td className="py-2 pr-4 text-text-secondary">Max DD</td>
              {rows.map((r) => (
                <td key={r.multiplier} className="text-right py-2 px-2 text-text-primary">
                  {formatPct(r.max_drawdown)}
                </td>
              ))}
            </tr>
            <tr>
              <td className="py-2 pr-4 text-text-secondary">Cost Drag</td>
              {rows.map((r) => (
                <td key={r.multiplier} className="text-right py-2 px-2 text-text-primary">
                  {formatBps(r.cost_drag_bps)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
