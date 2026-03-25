"use client"

import Link from "next/link"
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
    <div className={className}>
      {/* Visible preview — first section unblurred, rest faded */}
      <div className="relative" data-testid="pro-gate-overlay">
        <div className="relative overflow-hidden" style={{ maxHeight: 280 }}>
          <div className="pointer-events-none select-none">
            {children}
          </div>
          {/* Gradient fade to hide content */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: "linear-gradient(to bottom, transparent 20%, var(--color-bg-primary) 95%)",
            }}
          />
        </div>
      </div>

      {/* Upgrade CTA */}
      <div className="mt-6 border border-accent/20 rounded-xl bg-accent/[0.03] p-8 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-accent/10 mb-4">
          <svg
            className="w-6 h-6 text-accent"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-text-primary mb-2">
          Unlock institutional-grade analytics
        </h3>
        <p className="text-sm text-text-secondary max-w-md mx-auto mb-6">
          Upgrade to Portfolio to access 13F fund tracking, crowded trade detection,
          and clone portfolio analysis from top institutional managers.
        </p>
        <Link
          href="/account"
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-accent text-bg-primary font-medium text-sm hover:bg-accent/90 transition-colors"
        >
          Upgrade to Portfolio
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </Link>
        <p className="text-xs text-text-tertiary mt-3">
          $49/mo &middot; 30-day money-back guarantee
        </p>
      </div>
    </div>
  )
}
