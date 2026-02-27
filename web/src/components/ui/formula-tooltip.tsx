"use client"

import { useState, useRef, useEffect, type ReactNode } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { FORMULA_DEFINITIONS } from "@/lib/formula-definitions"

interface FormulaTooltipProps {
  metricKey: string
  children: ReactNode
}

export function FormulaTooltip({ metricKey, children }: FormulaTooltipProps) {
  const definition = FORMULA_DEFINITIONS[metricKey]
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e: MouseEvent) {
      if (triggerRef.current && !triggerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [open])

  if (!definition) {
    return <>{children}</>
  }

  return (
    <span
      ref={triggerRef}
      className="relative inline-flex items-center gap-1"
      data-testid={`formula-trigger-${metricKey}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {children}
      <svg
        width="12"
        height="12"
        viewBox="0 0 16 16"
        fill="none"
        className="text-text-tertiary shrink-0"
        aria-hidden="true"
      >
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
        <text
          x="8"
          y="12"
          textAnchor="middle"
          fontSize="10"
          fill="currentColor"
          fontFamily="serif"
        >
          i
        </text>
      </svg>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full mt-1.5 z-50 w-80 rounded-md border border-border-primary p-3 shadow-lg"
            style={{ background: "var(--color-bg-elevated)" }}
            role="tooltip"
            data-testid={`formula-popover-${metricKey}`}
          >
            <p className="text-sm font-semibold text-text-primary">{definition.name}</p>
            <p
              className="mt-1 text-xs leading-relaxed break-words"
              style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}
            >
              {definition.formula}
            </p>
            <p className="mt-1.5 text-xs italic text-text-secondary">{definition.source}</p>
            <p className="mt-1 text-xs text-text-tertiary">{definition.interpretation}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  )
}
