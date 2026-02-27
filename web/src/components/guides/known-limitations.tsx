import type { ReactNode } from "react"

interface KnownLimitationsProps {
  children: ReactNode
}

export function KnownLimitations({ children }: KnownLimitationsProps) {
  return (
    <div className="border border-warning/30 bg-warning/5 rounded-lg px-5 py-4 my-6">
      <div className="flex items-center gap-2 mb-2">
        <svg
          className="w-4 h-4 text-warning flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span className="text-[13px] uppercase tracking-wider font-semibold text-warning">
          Known Limitations
        </span>
      </div>
      <div className="body-text text-text-secondary">{children}</div>
    </div>
  )
}
