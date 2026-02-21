import type { CandidateCard } from "./types"

export interface TiltCounts {
  Value: number
  Blend: number
  Growth: number
}

const TILT_THRESHOLD = 10

export function classifyTilt(candidates: CandidateCard[]): TiltCounts {
  const counts: TiltCounts = { Value: 0, Blend: 0, Growth: 0 }
  for (const c of candidates) {
    const diff = c.growth_percentile - c.value_percentile
    if (diff > TILT_THRESHOLD) {
      counts.Growth++
    } else if (diff < -TILT_THRESHOLD) {
      counts.Value++
    } else {
      counts.Blend++
    }
  }
  return counts
}
