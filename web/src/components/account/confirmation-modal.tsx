"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export interface ModalField {
  name: string
  label: string
  type: "text" | "password"
}

interface ConfirmationModalProps {
  open: boolean
  title: string
  description?: string
  fields?: ModalField[]
  onClose: () => void
  onConfirm: (values: Record<string, string>) => void
  confirmLabel: string
  confirmVariant?: "accent" | "danger"
  loading?: boolean
  error?: string | null
}

function toLoadingLabel(label: string): string {
  const lower = label.toLowerCase()
  // Handle common patterns: "Remove" -> "Removing", "Delete" -> "Deleting"
  if (lower.endsWith("e")) {
    return label.slice(0, -1) + "ing"
  }
  return label + "ing"
}

export function ConfirmationModal({
  open,
  title,
  description,
  fields,
  onClose,
  onConfirm,
  confirmLabel,
  confirmVariant = "accent",
  loading = false,
  error,
}: ConfirmationModalProps) {
  const [values, setValues] = useState<Record<string, string>>({})
  const firstInputRef = useRef<HTMLInputElement>(null)
  const confirmBtnRef = useRef<HTMLButtonElement>(null)

  // Reset field values when modal opens
  useEffect(() => {
    if (open) {
      const initial: Record<string, string> = {}
      if (fields) {
        for (const field of fields) {
          initial[field.name] = ""
        }
      }
      setValues(initial)
    }
  }, [open, fields])

  // Auto-focus first input or confirm button on open
  useEffect(() => {
    if (open) {
      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        if (firstInputRef.current) {
          firstInputRef.current.focus()
        } else if (confirmBtnRef.current) {
          confirmBtnRef.current.focus()
        }
      })
    }
  }, [open])

  const dialogContainerRef = useRef<HTMLDivElement>(null)

  // Escape key + focus trap
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose()
        return
      }

      if (e.key === "Tab" && dialogContainerRef.current) {
        const focusable = dialogContainerRef.current.querySelectorAll<HTMLElement>(
          'input, button, [tabindex]:not([tabindex="-1"])'
        )
        if (focusable.length === 0) return

        const first = focusable[0]
        const last = focusable[focusable.length - 1]

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    },
    [onClose]
  )

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown)
      return () => document.removeEventListener("keydown", handleKeyDown)
    }
  }, [open, handleKeyDown])

  if (!open) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onConfirm(values)
  }

  const handleFieldChange = (name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    // Only close if clicking the backdrop itself, not the dialog
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const buttonLabel = loading ? toLoadingLabel(confirmLabel) : confirmLabel

  const confirmClassName =
    confirmVariant === "danger"
      ? "bg-red-500/90 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors hover:bg-red-600"
      : "bg-accent text-bg-primary px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors hover:bg-accent-hover"

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      data-testid="modal-backdrop"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogContainerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="terminal-card max-w-sm mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="modal-title" className="text-lg font-semibold text-text-primary mb-1">
          {title}
        </h2>

        {description && (
          <p className="text-sm text-text-secondary mb-4">{description}</p>
        )}

        <form onSubmit={handleSubmit}>
          {fields && fields.length > 0 && (
            <div className="space-y-3 mb-4">
              {fields.map((field, index) => (
                <div key={field.name}>
                  <label
                    htmlFor={`modal-${field.name}`}
                    className="block text-sm text-text-secondary mb-1"
                  >
                    {field.label}
                  </label>
                  <input
                    ref={index === 0 ? firstInputRef : undefined}
                    id={`modal-${field.name}`}
                    type={field.type}
                    value={values[field.name] ?? ""}
                    onChange={(e) => handleFieldChange(field.name, e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-primary text-text-primary text-sm focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
              ))}
            </div>
          )}

          {error && (
            <p className="text-sm text-red-400 mb-3">{error}</p>
          )}

          <div className="flex justify-end gap-3 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
            <button
              ref={!fields || fields.length === 0 ? confirmBtnRef : undefined}
              type="submit"
              disabled={loading}
              className={confirmClassName}
            >
              {buttonLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
