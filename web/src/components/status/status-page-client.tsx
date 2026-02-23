"use client"

import { useState, useEffect, useCallback } from "react"
import { StatusBanner } from "./status-banner"
import { ServiceCards } from "./service-cards"
import { ActiveIncidents, IncidentHistory } from "./incident-list"
import type { StatusResponse, ServiceInfo } from "./status-types"

const POLL_INTERVAL = 30_000

function mapToServiceInfos(services: StatusResponse["services"]): ServiceInfo[] {
  return [
    { name: "API", status: services.api, description: "Platform availability and response times" },
    { name: "Database", status: services.database, description: "Data storage and retrieval" },
    { name: "Scoring Engine", status: services.scoring, description: "Score computation and caching" },
  ]
}

export function StatusPageClient({ initial }: { initial: StatusResponse | null }) {
  const [data, setData] = useState<StatusResponse | null>(initial)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/status", { cache: "no-store" })
      if (res.ok) {
        const json: StatusResponse = await res.json()
        setData(json)
        setLastUpdated(new Date())
      }
    } catch {
      // Keep showing last known data
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(refresh, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [refresh])

  if (!data) {
    return (
      <div className="space-y-8">
        <StatusBanner status="degraded" />
        <p className="text-[14px] text-text-tertiary text-center">
          Unable to load status information. Please try again later.
        </p>
      </div>
    )
  }

  const serviceInfos = mapToServiceInfos(data.services)
  const activeIncidents = data.incidents.filter((i) => i.status !== "resolved")
  const resolvedIncidents = data.incidents.filter((i) => i.status === "resolved")

  return (
    <div className="space-y-12">
      <StatusBanner status={data.status} />
      <ServiceCards services={serviceInfos} />
      {activeIncidents.length > 0 && <ActiveIncidents incidents={activeIncidents} />}
      <IncidentHistory incidents={resolvedIncidents} />
      <p className="text-[12px] text-text-tertiary text-center">
        Last updated: {lastUpdated.toLocaleTimeString()} &middot; Refreshes every 30 seconds
      </p>
    </div>
  )
}
