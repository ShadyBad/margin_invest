/** Password rule definition matching backend _PASSWORD_RULES in auth.py */
export interface PasswordRule {
  regex: RegExp
  label: string
}

/** Result of checking a single rule */
export interface PasswordRuleResult {
  label: string
  met: boolean
}

/**
 * Password rules mirroring the backend exactly:
 * - api/src/margin_api/services/auth.py lines 20-27
 */
export const PASSWORD_RULES: PasswordRule[] = [
  { regex: /.{12,}/, label: "At least 12 characters" },
  { regex: /[A-Z]/, label: "One uppercase letter" },
  { regex: /[a-z]/, label: "One lowercase letter" },
  { regex: /[0-9]/, label: "One digit" },
  { regex: /[^A-Za-z0-9]/, label: "One special character" },
]

/** Check a password against all rules. Returns array of results. */
export function validatePassword(password: string): PasswordRuleResult[] {
  return PASSWORD_RULES.map((rule) => ({
    label: rule.label,
    met: rule.regex.test(password),
  }))
}

/** Returns true if all password rules are satisfied. */
export function isPasswordValid(password: string): boolean {
  return validatePassword(password).every((r) => r.met)
}
