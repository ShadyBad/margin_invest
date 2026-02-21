"use client"

import { useEffect, useState, useCallback } from "react"
import Link from "next/link"

export function MfaRequiredModal() {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const handler = () => setIsOpen(true)
    window.addEventListener("mfa-required", handler)
    return () => window.removeEventListener("mfa-required", handler)
  }, [])

  const handleDismiss = useCallback(() => {
    setIsOpen(false)
  }, [])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      data-testid="mfa-required-modal"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleDismiss}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="relative bg-bg-elevated border border-border-primary rounded-lg p-6 max-w-md w-full mx-4 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mfa-required-title"
      >
        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="w-12 h-12 rounded-full bg-warning/15 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-warning"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>
        </div>

        <h2
          id="mfa-required-title"
          className="text-lg font-semibold text-text-primary text-center mb-2"
        >
          MFA Required
        </h2>
        <p className="text-sm text-text-secondary text-center mb-6">
          Multi-factor authentication is required to perform this action. Set up
          MFA to continue.
        </p>

        <div className="flex flex-col gap-3">
          <Link
            href="/mfa/setup"
            className="block w-full text-center bg-accent text-white py-2.5 px-4 rounded-lg font-medium hover:bg-accent-hover transition-colors"
          >
            Set Up MFA
          </Link>
          <button
            onClick={handleDismiss}
            className="text-sm text-text-secondary hover:text-text-primary text-center py-1"
          >
            Go back
          </button>
        </div>
      </div>
    </div>
  )
}
