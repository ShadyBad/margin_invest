import { ConvictionBadge } from "@/components/ui"
import type { WatchlistItem } from "@/lib/api/types"

interface WatchlistTableProps {
  items: WatchlistItem[]
  className?: string
}

export function WatchlistTable({ items, className = "" }: WatchlistTableProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <div
      className={`bg-bg-elevated border border-border-primary rounded-sm overflow-hidden ${className}`}
      data-testid="watchlist-table"
    >
      <table className="w-full">
        <thead>
          <tr className="border-b border-border-primary">
            <th className="text-left text-sm font-medium text-text-secondary px-6 py-3">
              Ticker
            </th>
            <th className="text-left text-sm font-medium text-text-secondary px-6 py-3">
              Name
            </th>
            <th className="text-right text-sm font-medium text-text-secondary px-6 py-3">
              Percentile
            </th>
            <th className="text-right text-sm font-medium text-text-secondary px-6 py-3">
              Conviction
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.ticker}
              className="border-b border-border-primary last:border-b-0"
              data-testid={`watchlist-row-${item.ticker}`}
            >
              <td className="px-6 py-4 text-sm font-bold text-text-primary">
                {item.ticker}
              </td>
              <td className="px-6 py-4 text-sm text-text-secondary truncate max-w-[200px]">
                {item.name}
              </td>
              <td className="px-6 py-4 text-sm font-mono text-text-primary text-right">
                {item.composite_percentile.toFixed(0)}
              </td>
              <td className="px-6 py-4 text-right">
                <ConvictionBadge level={item.conviction_level} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
