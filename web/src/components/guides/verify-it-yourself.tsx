import type { ReactNode } from "react"

interface VerifyItYourselfProps {
  claim: string
  children: ReactNode
}

export function VerifyItYourself({ claim, children }: VerifyItYourselfProps) {
  return (
    <div className="border border-accent/30 bg-accent/5 rounded-lg px-5 py-4 my-6">
      <div className="flex items-center gap-2 mb-2">
        <svg
          className="w-4 h-4 text-accent flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M5 13l4 4L19 7"
          />
        </svg>
        <span className="text-[13px] uppercase tracking-wider font-semibold text-accent">
          Verify it yourself
        </span>
      </div>
      <div className="font-semibold text-text-primary mb-2">{claim}</div>
      <div className="body-text text-text-secondary">{children}</div>
    </div>
  )
}
