"use client"

import { useState, useEffect, useCallback } from "react"
import { getEvents, type GovernanceEvent } from "@/lib/api/governance"

interface EventTableProps {
  adminKey: string
}

const PAGE_SIZE = 50

function truncateJson(detail: Record<string, unknown> | null): string {
  if (!detail) return "\u2014"
  const json = JSON.stringify(detail)
  if (json.length <= 100) return json
  return json.slice(0, 100) + "..."
}

function formatDatetime(iso: string | null): string {
  if (!iso) return "\u2014"
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function EventTable({ adminKey }: EventTableProps) {
  const [events, setEvents] = useState<GovernanceEvent[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [filter, setFilter] = useState("")
  const [loading, setLoading] = useState(true)

  const fetchEvents = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getEvents(adminKey, {
        event_type: filter,
        limit: PAGE_SIZE,
        offset,
      })
      setEvents(data.events)
      setTotal(data.total)
    } catch {
      // Silently handle errors
    } finally {
      setLoading(false)
    }
  }, [adminKey, filter, offset])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  const handleFilterChange = (value: string) => {
    setFilter(value)
    setOffset(0)
  }

  const canGoBack = offset > 0
  const canGoNext = offset + PAGE_SIZE < total
  const rangeStart = total > 0 ? offset + 1 : 0
  const rangeEnd = Math.min(offset + PAGE_SIZE, total)

  return (
    <div data-testid="event-table" className="terminal-card p-5">
      {/* Filter input */}
      <div className="mb-4">
        <input
          type="text"
          value={filter}
          onChange={(e) => handleFilterChange(e.target.value)}
          placeholder="Filter by event type..."
          className="w-full max-w-sm px-3 py-2 text-sm rounded-lg border border-border-primary bg-bg-primary text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>

      {/* Loading state */}
      {loading && (
        <div className="text-center py-8 text-text-tertiary text-sm">
          Loading events...
        </div>
      )}

      {/* Empty state */}
      {!loading && events.length === 0 && (
        <div className="text-center py-8 text-text-tertiary text-sm">
          No events found.
        </div>
      )}

      {/* Table */}
      {!loading && events.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-primary text-left text-text-secondary">
                  <th className="pb-2 pr-4 font-medium">Event Type</th>
                  <th className="pb-2 pr-4 font-medium">Source</th>
                  <th className="pb-2 pr-4 font-medium">Detail</th>
                  <th className="pb-2 font-medium">Created At</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr
                    key={event.id}
                    className="border-b border-border-primary/50"
                  >
                    <td
                      data-testid={`event-type-${event.id}`}
                      className="py-2 pr-4 font-mono text-accent"
                    >
                      {event.event_type}
                    </td>
                    <td className="py-2 pr-4 text-text-primary">
                      {event.source}
                    </td>
                    <td
                      data-testid={`event-detail-${event.id}`}
                      className="py-2 pr-4 text-text-secondary font-mono text-xs max-w-xs truncate"
                    >
                      {truncateJson(event.detail)}
                    </td>
                    <td className="py-2 text-text-secondary whitespace-nowrap">
                      {formatDatetime(event.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border-primary">
            <span className="text-xs text-text-secondary">
              {rangeStart}&ndash;{rangeEnd} of {total}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                disabled={!canGoBack}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border-primary text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                disabled={!canGoNext}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border-primary text-text-secondary hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
