/**
 * Known financial acronyms that should be rendered in uppercase.
 */
const ACRONYMS = new Set([
  "roic",
  "wacc",
  "eps",
  "ebitda",
  "ev",
  "fcf",
  "sue",
  "pe",
  "pb",
  "roe",
  "roa",
  "dscr",
])

/**
 * Named financial scoring models that use a single-letter designator
 * followed by "score" — rendered as "X-Score".
 * Maps: key pattern → formatted output.
 */
const NAMED_SCORES: Record<string, string> = {
  piotroski_f_score: "Piotroski F-Score",
  beneish_m_score: "Beneish M-Score",
  altman_z_score: "Altman Z-Score",
}

/**
 * Converts a snake_case attribute key to a human-readable Title Case label.
 *
 * - Replaces underscores with spaces
 * - Capitalizes first letter of each word
 * - Preserves known financial acronyms (ROIC, EPS, EBITDA, etc.)
 * - Handles named scoring models (Piotroski F-Score, Beneish M-Score, etc.)
 * - Passes through already-formatted strings unchanged
 */
export function formatAttributeLabel(key: string): string {
  if (!key) return ""

  // Check for exact named-score matches first
  if (key in NAMED_SCORES) return NAMED_SCORES[key]

  return key
    .split("_")
    .map((word) => {
      if (ACRONYMS.has(word.toLowerCase())) return word.toUpperCase()
      // Already capitalized (pass-through for pre-formatted strings)
      if (word[0] === word[0].toUpperCase() && word.length > 1) return word
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    })
    .join(" ")
}
