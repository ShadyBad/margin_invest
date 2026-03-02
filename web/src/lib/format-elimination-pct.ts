/**
 * Format an elimination percentage with adaptive precision.
 *
 * - 2 decimal places by default, trailing zeros stripped.
 * - If 2 decimals would round to 100 but the true value is < 100,
 *   expands to 4 decimals (also trailing-zero stripped).
 * - Returns the numeric string WITHOUT the "%" suffix so callers
 *   can position it however they like.
 */
export function formatEliminationPct(eliminated: number, total: number): string {
  if (total === 0) return "0"

  const pct = (eliminated / total) * 100

  // True 100%
  if (eliminated >= total) return "100"

  // Try 2 decimals first
  const twoDecimal = pct.toFixed(2)
  if (parseFloat(twoDecimal) < 100) {
    return stripTrailingZeros(twoDecimal)
  }

  // 2 decimals rounded to 100 but it's not really 100 → use 4
  const fourDecimal = pct.toFixed(4)
  return stripTrailingZeros(fourDecimal)
}

function stripTrailingZeros(s: string): string {
  if (!s.includes(".")) return s
  return s.replace(/\.?0+$/, "")
}
