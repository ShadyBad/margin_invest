import { apiFetch } from "./client"

export interface Approval {
  id: number
  gate_type: string
  status: string
  pipeline_id: string | null
  payload_ref: Record<string, unknown> | null
  impact_summary: Record<string, unknown> | null
  submitted_at: string | null
  decided_at: string | null
  decided_by: number | null
  decision_reason: string | null
  expires_at: string | null
}

export interface ApprovalListResponse {
  approvals: Approval[]
}

export async function getApprovals(status?: string): Promise<ApprovalListResponse> {
  const params = status ? `?status=${status}` : ""
  return apiFetch<ApprovalListResponse>(`/api/v1/admin/approvals${params}`)
}

export async function approveApproval(id: number, reason?: string): Promise<{ status: string }> {
  return apiFetch(`/api/v1/admin/approvals/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  })
}

export async function rejectApproval(id: number, reason?: string): Promise<{ status: string }> {
  return apiFetch(`/api/v1/admin/approvals/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  })
}

export interface DashboardResponse {
  pending_count: number
  avg_approval_latency_hours: number | null
  rejection_rate: number | null
  recent_anomalies: unknown[]
}

export interface TransparencyResponse {
  oversight_levels: Record<string, string[]>
  last_approvals: Record<string, { decided_at: string; status: string }>
  pipeline_health: { status: string; last_successful_run: string | null }
}

export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>("/api/v1/admin/governance/dashboard")
}

export async function getTransparency(): Promise<TransparencyResponse> {
  return apiFetch<TransparencyResponse>("/api/v1/governance/transparency")
}

export interface GovernanceEvent {
  id: number
  event_type: string
  source: string
  detail: Record<string, unknown> | null
  created_at: string | null
}

export interface EventListResponse {
  events: GovernanceEvent[]
  total: number
}

export async function getEvents(
  options?: { event_type?: string; limit?: number; offset?: number }
): Promise<EventListResponse> {
  const params = new URLSearchParams()
  if (options?.event_type) params.set("event_type", options.event_type)
  if (options?.limit) params.set("limit", String(options.limit))
  if (options?.offset) params.set("offset", String(options.offset))
  const query = params.toString()
  return apiFetch<EventListResponse>(`/api/v1/admin/governance/events${query ? `?${query}` : ""}`)
}
