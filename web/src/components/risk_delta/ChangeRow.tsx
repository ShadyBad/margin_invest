"use client"

import { useState } from "react"
import type { MaterialChange } from "@/lib/api/risk_diffing"
import { SeverityPill } from "./SeverityPill"

interface ChangeRowProps {
  change: MaterialChange
}

const CHANGE_TYPE_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  NEW: {
    label: "NEW",
    color: "var(--color-bullish)",
    bg: "color-mix(in srgb, var(--color-bullish) 12%, transparent)",
  },
  REMOVED: {
    label: "REMOVED",
    color: "var(--color-bearish)",
    bg: "color-mix(in srgb, var(--color-bearish) 12%, transparent)",
  },
  EXPANDED: {
    label: "EXPANDED",
    color: "#f97316",
    bg: "color-mix(in srgb, #f97316 12%, transparent)",
  },
  SOFTENED: {
    label: "SOFTENED",
    color: "var(--color-warning)",
    bg: "color-mix(in srgb, var(--color-warning) 12%, transparent)",
  },
}

function getChangeTypeStyle(changeType: string) {
  return (
    CHANGE_TYPE_STYLES[changeType.toUpperCase()] ?? {
      label: changeType,
      color: "var(--color-on-surface-variant)",
      bg: "color-mix(in srgb, var(--color-on-surface-variant) 10%, transparent)",
    }
  )
}

export function ChangeRow({ change }: ChangeRowProps) {
  const [expanded, setExpanded] = useState(false)
  const style = getChangeTypeStyle(change.change_type)

  return (
    <div
      style={{
        borderBottom: "1px solid var(--color-ghost)",
        paddingTop: "0.75rem",
        paddingBottom: "0.75rem",
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          width: "100%",
          textAlign: "left",
          background: "none",
          border: "none",
          padding: 0,
          cursor: "pointer",
        }}
      >
        {/* Change type badge */}
        <span
          style={{
            display: "inline-block",
            padding: "0.125rem 0.4rem",
            borderRadius: "0.25rem",
            fontSize: "0.625rem",
            fontWeight: 700,
            letterSpacing: "0.05em",
            color: style.color,
            backgroundColor: style.bg,
            flexShrink: 0,
          }}
        >
          {style.label}
        </span>

        {/* Topic */}
        <span
          style={{
            flex: 1,
            fontSize: "0.875rem",
            color: "var(--color-on-surface)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {change.topic}
        </span>

        {/* Severity pill */}
        <SeverityPill severity={change.severity} />

        {/* Expand arrow */}
        <span
          style={{
            color: "var(--color-on-surface-variant)",
            fontSize: "0.75rem",
            flexShrink: 0,
            marginLeft: "0.25rem",
          }}
          aria-hidden="true"
        >
          {expanded ? "\u25B2" : "\u25BC"}
        </span>
      </button>

      {expanded && (
        <div
          style={{
            marginTop: "0.5rem",
            paddingLeft: "0.25rem",
          }}
        >
          <p
            style={{
              fontSize: "0.8125rem",
              color: "var(--color-on-surface-variant)",
              lineHeight: 1.5,
            }}
          >
            {change.summary_50_words}
          </p>
        </div>
      )}
    </div>
  )
}
