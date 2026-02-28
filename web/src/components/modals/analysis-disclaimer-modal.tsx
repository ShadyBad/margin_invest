"use client"

import { useEffect, useState, useCallback } from "react"

export function AnalysisDisclaimerModal() {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const handler = () => {
      // Only show if not already acknowledged
      try {
        if (localStorage.getItem("disclaimer_acknowledged") === "true") return
      } catch {
        // localStorage may be unavailable (e.g. SSR, iframe sandbox)
      }
      setIsOpen(true)
    }
    window.addEventListener("analysis-disclaimer-required", handler)
    return () => window.removeEventListener("analysis-disclaimer-required", handler)
  }, [])

  const handleAccept = useCallback(() => {
    try {
      localStorage.setItem("disclaimer_acknowledged", "true")
    } catch {
      // localStorage may be unavailable
    }
    setIsOpen(false)
  }, [])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      data-testid="analysis-disclaimer-modal"
    >
      {/* Backdrop — no dismiss on click */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="relative bg-bg-elevated border border-border-primary rounded-lg p-6 max-w-lg w-full mx-4 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="analysis-disclaimer-title"
      >
        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="w-12 h-12 rounded-full bg-accent/15 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-accent"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
              />
            </svg>
          </div>
        </div>

        <h2
          id="analysis-disclaimer-title"
          className="text-lg font-semibold text-text-primary text-center mb-2"
        >
          Quantitative Analysis Tool
        </h2>
        <p className="text-sm text-text-secondary text-center mb-6 leading-relaxed">
          Margin Invest provides quantitative factor analysis for informational purposes only. It
          does not provide investment advice, recommendations, or fiduciary guidance. You are solely
          responsible for your own investment decisions. Scores and signals reflect historical and
          current factor data — they are not predictions of future performance.
        </p>

        <button
          onClick={handleAccept}
          className="block w-full text-center bg-accent text-white py-2.5 px-4 rounded-lg font-medium hover:bg-accent-hover transition-colors"
          data-testid="disclaimer-accept"
        >
          I Understand
        </button>
      </div>
    </div>
  )
}
