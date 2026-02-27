"use client"

import { useState, type ReactNode } from "react"

interface TechnicalDetailProps {
  summary: string
  defaultOpen?: boolean
  children: ReactNode
}

export function TechnicalDetail({
  summary,
  defaultOpen = false,
  children,
}: TechnicalDetailProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="bg-bg-subtle border border-border-subtle rounded-lg my-6 overflow-hidden">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left cursor-pointer hover:bg-bg-elevated transition-colors"
      >
        <span className="font-mono text-[13px] text-accent select-none">{"{ }"}</span>
        <span className="flex-1 text-[14px] font-medium text-text-primary">{summary}</span>
        <svg
          className={`w-4 h-4 text-text-tertiary transition-transform duration-200 ${
            isOpen ? "rotate-90" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
      <div
        aria-hidden={!isOpen}
        style={{ display: isOpen ? "block" : "none" }}
        className="px-4 pb-4 pt-1 border-t border-border-subtle"
      >
        {children}
      </div>
    </div>
  )
}
