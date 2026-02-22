import { NextResponse } from "next/server"
import type { StatusResponse, ServiceStatus, OverallStatus, Incident } from "@/components/status/status-types"
import incidents from "@/data/incidents.json"

const API_URL = process.env.API_URL || "http://localhost:8000"

function mapHealthToServices(health: Record<string, string>): StatusResponse["services"] {
  return {
    api: health.status === "ok" ? "operational" : "outage",
    database: health.database === "ok" ? "operational" : "outage",
    scoring: health.redis === "ok" ? "operational" : "outage",
  }
}

function deriveOverallStatus(
  services: StatusResponse["services"],
  activeIncidents: Incident[]
): OverallStatus {
  const hasMajorIncident = activeIncidents.some(
    (i) => i.status !== "resolved" && i.severity === "major"
  )
  const hasActiveIncident = activeIncidents.some((i) => i.status !== "resolved")
  const serviceValues = Object.values(services) as ServiceStatus[]
  const hasOutage = serviceValues.includes("outage")
  const hasUnknown = serviceValues.includes("unknown")

  if (hasMajorIncident || hasOutage) return "outage"
  if (hasActiveIncident || hasUnknown) return "degraded"
  return "operational"
}

export async function GET() {
  const typedIncidents = incidents as Incident[]
  let services: StatusResponse["services"]
  let version = "unknown"

  try {
    const response = await fetch(`${API_URL}/health`, { cache: "no-store" })
    const health = await response.json()
    services = mapHealthToServices(health)
    version = health.version || "unknown"
  } catch {
    services = { api: "unknown", database: "unknown", scoring: "unknown" }
  }

  const status = deriveOverallStatus(services, typedIncidents)

  const payload: StatusResponse = { status, services, version, incidents: typedIncidents }

  return NextResponse.json(payload, {
    headers: { "Cache-Control": "no-store, max-age=0" },
  })
}
