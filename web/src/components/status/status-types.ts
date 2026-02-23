export type ServiceStatus = "operational" | "degraded" | "outage" | "unknown"
export type OverallStatus = "operational" | "degraded" | "outage"
export type IncidentStatus = "investigating" | "identified" | "monitoring" | "resolved"
export type IncidentSeverity = "minor" | "major" | "maintenance"

export interface ServiceInfo {
  name: string
  status: ServiceStatus
  description: string
}

export interface IncidentUpdate {
  message: string
  timestamp: string
}

export interface Incident {
  id: string
  title: string
  status: IncidentStatus
  severity: IncidentSeverity
  createdAt: string
  resolvedAt: string | null
  updates: IncidentUpdate[]
}

export interface StatusResponse {
  status: OverallStatus
  services: {
    api: ServiceStatus
    database: ServiceStatus
    scoring: ServiceStatus
  }
  version: string
  incidents: Incident[]
}
