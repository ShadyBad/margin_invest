"use client"

import { useEffect, useRef, useState } from "react"
import posthog from "posthog-js"

export function CheckoutButton() {
  const [loading, setLoading] = useState(false)

  async function handleClick() {
    posthog.capture("checkout_click", {
      experiment: "ten_dollar_list",
      amount_cents: 1000,
    })

    setLoading(true)
    try {
      const origin = window.location.origin
      const res = await fetch("/api/v1/experiment/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          success_url: `${origin}/experiment/this-week?success=1`,
          cancel_url: `${origin}/experiment/this-week`,
        }),
      })

      if (!res.ok) {
        setLoading(false)
        return
      }

      const data = await res.json()
      if (data.checkout_url) {
        posthog.capture("checkout_redirect", { experiment: "ten_dollar_list" })
        window.location.href = data.checkout_url
      }
    } catch {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className="w-full rounded-lg bg-white px-8 py-4 text-lg font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
    >
      {loading ? "Redirecting to checkout\u2026" : "Get This Week\u2019s List \u2014 $10"}
    </button>
  )
}

export function ExperimentTracker({ success }: { success: boolean }) {
  const hasTracked = useRef(false)

  useEffect(() => {
    if (hasTracked.current) return
    hasTracked.current = true

    if (success) {
      posthog.capture("purchase_complete", {
        experiment: "ten_dollar_list",
        amount_cents: 1000,
      })
    } else {
      posthog.capture("page_view", {
        experiment: "ten_dollar_list",
        page: "/experiment/this-week",
      })
    }
  }, [success])

  return null
}
