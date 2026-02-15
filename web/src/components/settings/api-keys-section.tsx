"use client"

import { useEffect, useState } from "react"

const providers = [
  { id: "fmp", name: "Financial Modeling Prep", description: "Fundamentals, pre-computed ratios" },
  { id: "polygon", name: "Polygon.io", description: "Superior price data" },
  { id: "finnhub", name: "Finnhub", description: "News, earnings, insider data" },
  { id: "fred", name: "FRED", description: "Macro economic indicators" },
]

interface ApiKeyData {
  id: number
  provider_name: string
  masked_key: string
  is_platform_managed: boolean
  created_at: string
}

export function ApiKeysSection() {
  const [plan, setPlan] = useState<string | null>(null)
  const [keys, setKeys] = useState<ApiKeyData[]>([])
  const [inputKeys, setInputKeys] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})

  useEffect(() => {
    fetch("/api/v1/billing/status")
      .then((r) => r.json())
      .then((data) => {
        setPlan(data.subscription_plan)
        if (data.is_active) {
          fetch("/api/v1/keys/")
            .then((r) => r.json())
            .then((d) => setKeys(d.keys))
        }
      })
  }, [])

  const handleUpgrade = async () => {
    const resp = await fetch("/api/v1/billing/checkout", { method: "POST" })
    const data = await resp.json()
    window.location.href = data.checkout_url
  }

  const handleSave = async (providerId: string) => {
    const value = inputKeys[providerId]
    if (!value) return
    setSaving((prev) => ({ ...prev, [providerId]: true }))
    const resp = await fetch("/api/v1/keys/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider_name: providerId, api_key: value }),
    })
    if (resp.ok) {
      const saved = await resp.json()
      setKeys((prev) => [...prev.filter((k) => k.provider_name !== providerId), saved])
      setInputKeys((prev) => ({ ...prev, [providerId]: "" }))
    }
    setSaving((prev) => ({ ...prev, [providerId]: false }))
  }

  const handleDelete = async (providerId: string) => {
    await fetch(`/api/v1/keys/${providerId}`, { method: "DELETE" })
    setKeys((prev) => prev.filter((k) => k.provider_name !== providerId))
  }

  if (plan === null) return null

  if (plan === "free") {
    return (
      <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <h2 className="text-lg font-bold text-text-primary mb-2">API Keys</h2>
        <p className="text-sm text-text-secondary mb-4">
          Upgrade to Margin Invest to unlock premium data providers.
        </p>
        <button
          onClick={handleUpgrade}
          className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors"
        >
          Upgrade to Margin Invest
        </button>
      </section>
    )
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-2">API Keys</h2>
      <p className="text-sm text-text-secondary mb-6">
        Add provider API keys to unlock premium data sources. Keys are encrypted at rest.
      </p>
      <div className="space-y-4">
        {providers.map((provider) => {
          const existingKey = keys.find((k) => k.provider_name === provider.id)
          return (
            <div
              key={provider.id}
              className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-bg-primary rounded-sm border border-border-primary"
            >
              <div className="flex-1">
                <div className="text-text-primary font-medium">{provider.name}</div>
                <div className="text-xs text-text-secondary">{provider.description}</div>
                {existingKey && (
                  <div className="text-xs text-text-tertiary mt-1 font-mono">
                    {existingKey.masked_key}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                {existingKey ? (
                  <button
                    onClick={() => handleDelete(provider.id)}
                    className="px-3 py-2 text-danger text-sm font-medium hover:bg-danger/10 rounded-sm transition-colors"
                  >
                    Revoke
                  </button>
                ) : (
                  <>
                    <input
                      type="password"
                      placeholder="Enter API key"
                      value={inputKeys[provider.id] || ""}
                      onChange={(e) =>
                        setInputKeys((prev) => ({ ...prev, [provider.id]: e.target.value }))
                      }
                      className="px-3 py-2 bg-bg-elevated border border-border-primary rounded-sm text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none w-48"
                    />
                    <button
                      onClick={() => handleSave(provider.id)}
                      disabled={!inputKeys[provider.id] || saving[provider.id]}
                      className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {saving[provider.id] ? "Saving..." : "Save"}
                    </button>
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
