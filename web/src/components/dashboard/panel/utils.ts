export function getPercentileColor(score: number): string {
  if (score >= 66) return "var(--color-bullish)"
  if (score >= 33) return "var(--color-warning)"
  return "var(--color-danger)"
}
