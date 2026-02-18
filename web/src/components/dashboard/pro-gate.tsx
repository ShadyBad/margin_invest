"use client"

import { useSubscriptionTier } from "@/lib/hooks/use-subscription-tier"

interface ProGateProps {
  children: React.ReactNode
  className?: string
}

export function ProGate({ children, className = "" }: ProGateProps) {
  const { tier, loading } = useSubscriptionTier()

  if (loading || tier === "pro") {
    return <div className={className}>{children}</div>
  }

  return (
    <div className={`relative ${className}`}>
      <div
        data-testid="pro-gate-overlay"
        className="blur-[6px] select-none pointer-events-none"
        aria-hidden="true"
      >
        {children}
      </div>
      <div className="mt-3 flex items-center gap-3 bg-accent/[0.04] border border-accent/10 rounded-sm py-3 px-5">
        <svg
          className="w-3.5 h-3.5 text-accent/40 shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
          />
        </svg>
        <span className="text-sm text-text-secondary">
          Unlock institutional-grade analytics
        </span>
        <span className="text-xs font-medium bg-accent/10 text-accent px-2 py-0.5 rounded-sm">
          Pro Insight
        </span>
        <a
          href="/account"
          className="ml-auto text-accent/60 hover:text-accent transition-colors"
          aria-label="Upgrade to Pro"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M8.25 4.5l7.5 7.5-7.5 7.5"
            />
          </svg>
        </a>
      </div>
    </div>
  )
}
