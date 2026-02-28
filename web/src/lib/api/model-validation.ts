import { apiFetch } from "./client"

export interface MetricDistribution {
  mean: number
  median: number
  std: number
  min: number
  max: number
  ci_lower: number
  ci_upper: number
  cv: number
}

export interface GateCheck {
  name: string
  value: number
  threshold: number
  passed: boolean
}

export interface ModelComparison {
  p_value: number
  effect_size: number
  significant: boolean
  label: string
  n_compared: number
  mean_difference: number
}

export interface SeedDetail {
  seed: number
  rank_ic: number
  n_clusters: number
  n_samples: number
  selected: boolean
}

export interface SeedValidationReport {
  run_group_id: string
  created_at: string
  n_seeds: number
  gate_passed: boolean
  selected_seed: number | null
  metric_distributions: Record<string, MetricDistribution>
  gate_checks: GateCheck[]
  seed_details: SeedDetail[]
  environment_snapshot: Record<string, unknown>
  comparison: ModelComparison | null
}

export interface ValidationHistory {
  reports: SeedValidationReport[]
  total: number
}

export async function getLatestValidationReport(
  adminKey: string,
): Promise<SeedValidationReport> {
  return apiFetch<SeedValidationReport>(
    "/api/v1/admin/model-validation/latest",
    { headers: { "X-Admin-Key": adminKey } },
  )
}

export async function getValidationHistory(
  adminKey: string,
  limit = 20,
  offset = 0,
): Promise<ValidationHistory> {
  return apiFetch<ValidationHistory>(
    `/api/v1/admin/model-validation/history?limit=${limit}&offset=${offset}`,
    { headers: { "X-Admin-Key": adminKey } },
  )
}

export async function getValidationReport(
  adminKey: string,
  runGroupId: string,
): Promise<SeedValidationReport> {
  return apiFetch<SeedValidationReport>(
    `/api/v1/admin/model-validation/${runGroupId}`,
    { headers: { "X-Admin-Key": adminKey } },
  )
}
