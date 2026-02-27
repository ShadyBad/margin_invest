"use client"

import { useEffect, useState } from "react"
import { getProposals, acceptProposal, dismissProposal } from "@/lib/api/proposals"
import type { Proposal } from "@/lib/api/proposals"

export function ProposalBanner() {
  const [proposals, setProposals] = useState<Proposal[]>([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    getProposals("pending")
      .then((res) => {
        setProposals(res.proposals)
      })
      .catch(() => {
        // Silently fail — banner is non-critical
      })
      .finally(() => setLoaded(true))
  }, [])

  async function handleAccept(id: number) {
    try {
      await acceptProposal(id)
      setProposals((prev) => prev.filter((p) => p.id !== id))
    } catch {
      // Silently fail
    }
  }

  async function handleDismiss(id: number) {
    try {
      await dismissProposal(id)
      setProposals((prev) => prev.filter((p) => p.id !== id))
    } catch {
      // Silently fail
    }
  }

  if (!loaded || proposals.length === 0) return null

  return (
    <div className="mb-6 space-y-3" data-testid="proposal-banner">
      {proposals.map((proposal) => {
        const ticker = proposal.payload?.ticker as string | undefined
        const rationale = proposal.payload?.rationale as string | undefined

        return (
          <div
            key={proposal.id}
            className="terminal-card flex items-center justify-between gap-4 px-4 py-3"
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="inline-flex items-center rounded-sm bg-surface-secondary px-2 py-0.5 text-xs font-mono text-text-secondary">
                {proposal.proposal_type}
              </span>
              {ticker && (
                <span className="font-semibold text-text-primary">{ticker}</span>
              )}
              {rationale && (
                <span className="text-sm text-text-secondary truncate">{rationale}</span>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => handleAccept(proposal.id)}
                className="rounded-sm bg-bullish/20 px-3 py-1 text-xs font-medium text-bullish hover:bg-bullish/30 transition-colors"
              >
                Accept
              </button>
              <button
                onClick={() => handleDismiss(proposal.id)}
                className="rounded-sm bg-surface-secondary px-3 py-1 text-xs font-medium text-text-secondary hover:bg-surface-secondary/80 transition-colors"
              >
                Dismiss
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
