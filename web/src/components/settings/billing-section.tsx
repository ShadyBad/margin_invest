"use client"

import { useEffect, useState } from "react"

interface BillingStatus {
  subscription_plan: string
  stripe_subscription_id: string | null
  is_active: boolean
}

export function BillingSection() {
  const [status, setStatus] = useState<BillingStatus | null>(null)

  useEffect(() => {
    fetch("/api/v1/billing/status")
      .then((r) => r.json())
      .then(setStatus)
  }, [])

  const handleUpgrade = async () => {
    const resp = await fetch("/api/v1/billing/checkout", { method: "POST" })
    const data = await resp.json()
    window.location.href = data.checkout_url
  }

  const handleManage = async () => {
    const resp = await fetch("/api/v1/billing/portal", { method: "POST" })
    const data = await resp.json()
    window.location.href = data.portal_url
  }

  if (!status) return null

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-2">Billing</h2>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-text-primary font-medium">
            {status.is_active ? "Margin Invest" : "Free"}
          </div>
          <div className="text-sm text-text-secondary">
            {status.is_active
              ? "Premium data providers and priority scoring"
              : "Basic scoring with yfinance data"}
          </div>
        </div>
        {status.is_active ? (
          <button
            onClick={handleManage}
            className="px-4 py-2 border border-border-primary text-text-primary font-medium text-sm rounded-sm hover:bg-bg-subtle transition-colors"
          >
            Manage subscription
          </button>
        ) : (
          <button
            onClick={handleUpgrade}
            className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors"
          >
            Upgrade
          </button>
        )}
      </div>
    </section>
  )
}
