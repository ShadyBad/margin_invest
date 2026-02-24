"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"

export function TickerSearch() {
  const [query, setQuery] = useState("")
  const router = useRouter()

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      const ticker = query.trim().toUpperCase()
      if (ticker) {
        router.push(`/asset/${ticker}`)
        setQuery("")
      }
    },
    [query, router]
  )

  return (
    <form onSubmit={handleSubmit} className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search any ticker..."
        className="w-32 sm:w-40 h-8 px-3 text-xs bg-white/[0.04] border border-white/[0.08] rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent/40 transition-colors"
      />
    </form>
  )
}
