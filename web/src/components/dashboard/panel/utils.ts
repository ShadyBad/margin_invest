export function getPercentileColor(score: number): string {
  if (score >= 80) return "#10B981"
  if (score >= 60) return "#1C7A5A"
  if (score >= 40) return "#6B7280"
  if (score >= 20) return "#D97706"
  return "#DC2626"
}
