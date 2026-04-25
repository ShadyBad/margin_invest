/**
 * Risk factor diffing API client helpers.
 */
import { apiFetch } from "./client"

// ---------------------------------------------------------------------------
// Types matching Python Pydantic schemas for risk factor analysis
// ---------------------------------------------------------------------------

export interface MaterialChange {
  change_type: string
  topic: string
  severity: number
  summary_50_words: string
  verbatim_new_text: string
  verbatim_old_text: string
}

export interface RiskFactorAnalysis {
  ticker: string
  current_period: string
  prior_period: string
  overall_risk_delta_score: number
  model_confidence: number
  material_changes: MaterialChange[]
  prompt_version: string
  analyzed_at: string
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getRiskFactorAnalysis(
  ticker: string,
): Promise<RiskFactorAnalysis | null> {
  try {
    return await apiFetch<RiskFactorAnalysis>(
      `/api/v1/analytics/risk_factors/${ticker.toUpperCase()}`,
    )
  } catch {
    return null
  }
}
