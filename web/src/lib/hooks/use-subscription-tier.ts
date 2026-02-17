"use client"

import { useEffect, useState } from "react"

export type SubscriptionTier = "free" | "pro"

interface SubscriptionTierResult {
  tier: SubscriptionTier
  loading: boolean
}

export function useSubscriptionTier(): SubscriptionTierResult {
  const [tier, setTier] = useState<SubscriptionTier>("free")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/v1/billing/status")
      .then((r) => r.json())
      .then((data) => {
        setTier(data.is_active ? "pro" : "free")
      })
      .catch(() => {
        setTier("free")
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  return { tier, loading }
}
