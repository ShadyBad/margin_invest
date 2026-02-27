import { apiFetch } from "./client"

export interface Proposal {
  id: number
  proposal_type: string
  status: string
  payload: Record<string, unknown> | null
  created_at: string | null
  decided_at: string | null
}

export interface ProposalListResponse {
  proposals: Proposal[]
}

export async function getProposals(status?: string): Promise<ProposalListResponse> {
  const params = status ? `?status=${status}` : ""
  return apiFetch<ProposalListResponse>(`/api/v1/proposals${params}`)
}

export async function acceptProposal(id: number): Promise<{ status: string }> {
  return apiFetch(`/api/v1/proposals/${id}/accept`, { method: "POST" })
}

export async function dismissProposal(id: number): Promise<{ status: string }> {
  return apiFetch(`/api/v1/proposals/${id}/dismiss`, { method: "POST" })
}
