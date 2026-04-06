"use client"

import { useState, useEffect } from "react"
import { getAlerts, createAlert, deleteAlert } from "@/lib/api/watchlist"
import type { ScoreAlertItem, AlertCreateRequest } from "@/lib/api/types"

function alertTypeLabel(type: ScoreAlertItem["alert_type"], threshold: number | null): string {
  if (type === "survivor") return "Survivor status change"
  if (type === "above") return `above ${threshold ?? ""}`
  if (type === "below") return `below ${threshold ?? ""}`
  return type
}

export function AlertManager() {
  const [items, setItems] = useState<ScoreAlertItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  // Form state
  const [formTicker, setFormTicker] = useState("")
  const [formType, setFormType] = useState<AlertCreateRequest["alert_type"]>("above")
  const [formThreshold, setFormThreshold] = useState("")
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getAlerts()
      .then((res) => {
        if (!cancelled) setItems(res.items)
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load alerts")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  async function handleDelete(alertId: number) {
    // Optimistic update
    setItems((prev) => prev.filter((a) => a.id !== alertId))
    try {
      await deleteAlert(alertId)
    } catch {
      // Re-fetch to restore state on failure
      getAlerts()
        .then((res) => setItems(res.items))
        .catch(() => {/* best-effort */})
    }
  }

  async function handleCreate() {
    if (!formTicker.trim()) {
      setFormError("Ticker is required")
      return
    }
    if (formType !== "survivor" && !formThreshold) {
      setFormError("Threshold is required for above/below alerts")
      return
    }

    setFormSubmitting(true)
    setFormError(null)

    const request: AlertCreateRequest = {
      ticker: formTicker.trim().toUpperCase(),
      alert_type: formType,
      threshold: formType !== "survivor" ? parseFloat(formThreshold) : null,
    }

    try {
      const newAlert = await createAlert(request)
      setItems((prev) => [...prev, newAlert])
      setShowForm(false)
      setFormTicker("")
      setFormType("above")
      setFormThreshold("")
    } catch {
      setFormError("Failed to create alert. Please try again.")
    } finally {
      setFormSubmitting(false)
    }
  }

  function handleCancel() {
    setShowForm(false)
    setFormTicker("")
    setFormType("above")
    setFormThreshold("")
    setFormError(null)
  }

  if (loading) {
    return (
      <div className="space-y-2" data-testid="alert-manager-skeleton">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-12 rounded-lg bg-bg-elevated animate-pulse border border-border-subtle"
          />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-text-secondary" data-testid="alert-manager-error">
        {error}
      </p>
    )
  }

  return (
    <div data-testid="alert-manager">
      {items.length === 0 && !showForm && (
        <div className="rounded-lg border border-border-subtle bg-bg-elevated p-6 text-center" data-testid="alert-manager-empty">
          <p className="text-sm text-text-secondary mb-3">
            No alerts configured.
          </p>
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="text-sm text-accent-primary hover:underline underline-offset-2"
          >
            Create your first alert
          </button>
        </div>
      )}

      {items.length > 0 && (
        <div className="rounded-lg border border-border-subtle bg-bg-elevated overflow-hidden mb-3">
          {items.map((alert) => (
            <div
              key={alert.id}
              className="flex items-center gap-4 px-4 py-3 border-b border-border-subtle last:border-b-0"
              data-testid={`alert-item-${alert.id}`}
            >
              {/* Ticker */}
              <span className="text-sm font-bold text-text-primary w-16 flex-shrink-0">
                {alert.ticker}
              </span>

              {/* Type label */}
              <span className="text-sm text-text-secondary flex-1">
                {alertTypeLabel(alert.alert_type, alert.threshold)}
              </span>

              {/* Recently fired badge */}
              {alert.last_triggered_at && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-amber-500/10 text-amber-500 border border-amber-500/20 flex-shrink-0">
                  Fired
                </span>
              )}

              {/* Active/inactive indicator */}
              {!alert.is_active && (
                <span className="text-xs text-text-tertiary flex-shrink-0">
                  Inactive
                </span>
              )}

              {/* Delete button */}
              <button
                type="button"
                onClick={() => handleDelete(alert.id)}
                aria-label={`Delete alert for ${alert.ticker}`}
                className="text-xs text-text-tertiary hover:text-bearish transition-colors flex-shrink-0 px-2 py-1 rounded border border-transparent hover:border-border-subtle"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add alert button (when list is not empty) */}
      {items.length > 0 && !showForm && (
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="text-sm text-accent-primary hover:underline underline-offset-2"
        >
          + Add alert
        </button>
      )}

      {/* Create form */}
      {showForm && (
        <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4" data-testid="alert-create-form">
          <h3 className="text-sm font-semibold text-text-primary mb-3">New Alert</h3>

          <div className="space-y-3">
            {/* Ticker */}
            <div>
              <label htmlFor="alert-ticker" className="block text-xs text-text-secondary mb-1">
                Ticker
              </label>
              <input
                id="alert-ticker"
                type="text"
                value={formTicker}
                onChange={(e) => setFormTicker(e.target.value)}
                placeholder="e.g. AAPL"
                className="w-full bg-transparent border border-border-subtle rounded px-3 py-1.5 text-sm text-text-primary placeholder:text-text-tertiary outline-none focus:border-accent-primary transition-colors"
              />
            </div>

            {/* Alert type */}
            <div>
              <label htmlFor="alert-type" className="block text-xs text-text-secondary mb-1">
                Alert type
              </label>
              <select
                id="alert-type"
                value={formType}
                onChange={(e) => setFormType(e.target.value as AlertCreateRequest["alert_type"])}
                className="w-full bg-bg-elevated border border-border-subtle rounded px-3 py-1.5 text-sm text-text-primary outline-none focus:border-accent-primary transition-colors"
              >
                <option value="above">Score above threshold</option>
                <option value="below">Score below threshold</option>
                <option value="survivor">Survivor status change</option>
              </select>
            </div>

            {/* Threshold (hidden for survivor) */}
            {formType !== "survivor" && (
              <div>
                <label htmlFor="alert-threshold" className="block text-xs text-text-secondary mb-1">
                  Threshold (0–100)
                </label>
                <input
                  id="alert-threshold"
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={formThreshold}
                  onChange={(e) => setFormThreshold(e.target.value)}
                  placeholder="e.g. 75"
                  className="w-full bg-transparent border border-border-subtle rounded px-3 py-1.5 text-sm text-text-primary placeholder:text-text-tertiary outline-none focus:border-accent-primary transition-colors"
                />
              </div>
            )}

            {formError && (
              <p className="text-xs text-bearish">{formError}</p>
            )}

            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={handleCreate}
                disabled={formSubmitting}
                className="px-4 py-1.5 rounded text-sm bg-accent-primary text-white hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {formSubmitting ? "Creating…" : "Create"}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                disabled={formSubmitting}
                className="px-4 py-1.5 rounded text-sm text-text-secondary border border-border-subtle hover:text-text-primary transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
