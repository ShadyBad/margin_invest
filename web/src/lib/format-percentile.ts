/** Format a percentile value for display. Always an integer, clamped 0-100. */
export function formatPercentile(value: number): string {
  return String(Math.round(Math.min(100, Math.max(0, value))))
}
