"use client"

import type { GateCheck } from "@/lib/api/model-validation"

interface ValidationChecklistProps {
  checks: GateCheck[]
  gatePassed: boolean
}

export function ValidationChecklist({ checks, gatePassed }: ValidationChecklistProps) {
  return (
    <div data-testid="validation-checklist" className="terminal-card p-5">
      {/* Overall gate status */}
      <div className="flex items-center gap-3 mb-4">
        <span
          data-testid="gate-status"
          className={`text-lg font-semibold ${
            gatePassed ? "text-bullish" : "text-bearish"
          }`}
        >
          {gatePassed ? "GATE PASSED" : "GATE FAILED"}
        </span>
        <span
          className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-sm font-bold ${
            gatePassed
              ? "bg-[var(--color-bullish)]/20 text-bullish"
              : "bg-[var(--color-bearish)]/20 text-bearish"
          }`}
        >
          {gatePassed ? "\u2713" : "\u2717"}
        </span>
      </div>

      {/* Individual checks */}
      {checks.length === 0 ? (
        <p className="text-sm text-text-tertiary">No gate checks available.</p>
      ) : (
        <ul className="space-y-2">
          {checks.map((check) => (
            <li
              key={check.name}
              data-testid={`gate-check-${check.name}`}
              className="flex items-center gap-3 text-sm"
            >
              <span
                className={`flex-shrink-0 font-bold ${
                  check.passed ? "text-bullish" : "text-bearish"
                }`}
              >
                {check.passed ? "\u2713" : "\u2717"}
              </span>
              <span className="text-text-primary flex-1">{check.name}</span>
              <span className="font-mono text-text-secondary">
                {check.value.toFixed(4)}
              </span>
              <span className="text-text-tertiary text-xs">
                (threshold: {check.threshold.toFixed(4)})
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
