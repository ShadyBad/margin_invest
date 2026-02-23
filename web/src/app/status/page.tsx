import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"
import { StatusPageClient } from "@/components/status"
import type { StatusResponse } from "@/components/status"

export const metadata: Metadata = {
  title: "System Status | Margin Invest",
  description:
    "Real-time status of Margin Invest services — API, database, and scoring engine availability.",
}

const API_URL = process.env.API_URL || "http://localhost:8000"

async function fetchInitialStatus(): Promise<StatusResponse | null> {
  try {
    const { default: incidents } = await import("@/data/incidents.json")
    const response = await fetch(`${API_URL}/health`, { cache: "no-store" })
    const health = await response.json()

    const services: StatusResponse["services"] = {
      api: health.status === "ok" ? "operational" : "outage",
      database: health.database === "ok" ? "operational" : "outage",
      scoring: health.redis === "ok" ? "operational" : "outage",
    }

    const typedIncidents = incidents as StatusResponse["incidents"]
    const hasMajor = typedIncidents.some((i) => i.status !== "resolved" && i.severity === "major")
    const hasActive = typedIncidents.some((i) => i.status !== "resolved")
    const hasOutage = Object.values(services).includes("outage")

    let status: StatusResponse["status"] = "operational"
    if (hasMajor || hasOutage) status = "outage"
    else if (hasActive) status = "degraded"

    return { status, services, version: health.version || "unknown", incidents: typedIncidents }
  } catch {
    return null
  }
}

export default async function StatusPage() {
  const initial = await fetchInitialStatus()

  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <div className="text-center mb-12">
            <h1 className="heading-2 text-text-primary mb-3">System Status</h1>
            <p className="body-text text-text-secondary">
              Real-time availability of Margin Invest services.
            </p>
          </div>

          <StatusPageClient initial={initial} />

          <div className="mt-16 pt-8 border-t border-border-subtle">
            <Link
              href="/"
              className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
            >
              &larr; Back to home
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
