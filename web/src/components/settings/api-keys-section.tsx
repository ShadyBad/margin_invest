"use client"

import { useState } from "react"

const providers = [
  { id: "fmp", name: "Financial Modeling Prep", description: "Fundamentals, pre-computed ratios" },
  { id: "polygon", name: "Polygon.io", description: "Superior price data" },
  { id: "finnhub", name: "Finnhub", description: "News, earnings, insider data" },
  { id: "fred", name: "FRED", description: "Macro economic indicators" },
]

export function ApiKeysSection() {
  const [keys, setKeys] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState<Record<string, boolean>>({})

  const handleSave = (providerId: string) => {
    // Placeholder: In production, this will POST to the API
    setSaved((prev) => ({ ...prev, [providerId]: true }))
    setTimeout(() => {
      setSaved((prev) => ({ ...prev, [providerId]: false }))
    }, 2000)
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-2">API Keys</h2>
      <p className="text-sm text-text-secondary mb-6">
        Add provider API keys to unlock premium data sources. Keys are encrypted at rest.
      </p>
      <div className="space-y-4">
        {providers.map((provider) => (
          <div key={provider.id} className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-bg-primary rounded-sm border border-border-primary">
            <div className="flex-1">
              <div className="text-text-primary font-medium">{provider.name}</div>
              <div className="text-xs text-text-secondary">{provider.description}</div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="password"
                placeholder="Enter API key"
                value={keys[provider.id] || ""}
                onChange={(e) => setKeys((prev) => ({ ...prev, [provider.id]: e.target.value }))}
                className="px-3 py-2 bg-bg-elevated border border-border-primary rounded-sm text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none w-48"
              />
              <button
                onClick={() => handleSave(provider.id)}
                disabled={!keys[provider.id]}
                className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saved[provider.id] ? "Saved" : "Save"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
