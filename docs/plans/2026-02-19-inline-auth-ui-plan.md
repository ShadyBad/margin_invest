# Inline Auth UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate sign-up into the login card with inline mode toggle, client-side password validation, and live checklist — fixing the false sign-up error bug.

**Architecture:** Extend `LoginCard` with a `mode` state (`"signin" | "signup"`), a segmented control for switching, and a registration handler that calls `POST /api/v1/auth/register`. Client-side password rules mirror the backend exactly. The old `/register` page becomes a redirect.

**Tech Stack:** Next.js 15, React, Vitest, Testing Library, next-auth

**Design doc:** `docs/plans/2026-02-19-inline-auth-ui-design.md`

---

### Task 1: Add password validation utility and tests

**Files:**
- Create: `web/src/lib/password-validation.ts`
- Create: `web/src/lib/__tests__/password-validation.test.ts`

**Step 1: Write the failing tests**

```ts
// web/src/lib/__tests__/password-validation.test.ts
import { describe, it, expect } from "vitest"
import { validatePassword, PASSWORD_RULES } from "../password-validation"

describe("PASSWORD_RULES", () => {
  it("exports 5 rules", () => {
    expect(PASSWORD_RULES).toHaveLength(5)
  })
})

describe("validatePassword", () => {
  it("returns all rules failed for empty string", () => {
    const results = validatePassword("")
    expect(results.every((r) => !r.met)).toBe(true)
  })

  it("returns length met for 12+ chars", () => {
    const results = validatePassword("abcdefghijkl")
    const lengthRule = results.find((r) => r.label === "At least 12 characters")
    expect(lengthRule?.met).toBe(true)
  })

  it("returns length not met for 11 chars", () => {
    const results = validatePassword("abcdefghijk")
    const lengthRule = results.find((r) => r.label === "At least 12 characters")
    expect(lengthRule?.met).toBe(false)
  })

  it("detects uppercase", () => {
    const results = validatePassword("A")
    const rule = results.find((r) => r.label === "One uppercase letter")
    expect(rule?.met).toBe(true)
  })

  it("detects lowercase", () => {
    const results = validatePassword("a")
    const rule = results.find((r) => r.label === "One lowercase letter")
    expect(rule?.met).toBe(true)
  })

  it("detects digit", () => {
    const results = validatePassword("1")
    const rule = results.find((r) => r.label === "One digit")
    expect(rule?.met).toBe(true)
  })

  it("detects special character", () => {
    const results = validatePassword("!")
    const rule = results.find((r) => r.label === "One special character")
    expect(rule?.met).toBe(true)
  })

  it("all rules pass for a strong password", () => {
    const results = validatePassword("MyPassword1!")
    expect(results.every((r) => r.met)).toBe(true)
  })

  it("missing uppercase fails only that rule", () => {
    const results = validatePassword("mypassword1!")
    expect(results.find((r) => r.label === "One uppercase letter")?.met).toBe(false)
    expect(results.find((r) => r.label === "One lowercase letter")?.met).toBe(true)
    expect(results.find((r) => r.label === "One digit")?.met).toBe(true)
    expect(results.find((r) => r.label === "One special character")?.met).toBe(true)
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/lib/__tests__/password-validation.test.ts`
Expected: FAIL — module not found

**Step 3: Write the implementation**

```ts
// web/src/lib/password-validation.ts

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
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/lib/__tests__/password-validation.test.ts`
Expected: PASS (all 9 tests)

**Step 5: Commit**

```bash
git add web/src/lib/password-validation.ts web/src/lib/__tests__/password-validation.test.ts
git commit -m "feat(web): add password validation utility mirroring backend rules"
```

---

### Task 2: Add segmented control and sign-up mode to LoginCard

**Files:**
- Modify: `web/src/components/login/login-card.tsx`
- Modify: `web/src/components/login/__tests__/login-card.test.tsx`

**Step 1: Write failing tests for the segmented control**

Add these tests to the existing `login-card.test.tsx`:

```tsx
// Add to imports at top:
// import { validatePassword } from "@/lib/password-validation"

describe("segmented control", () => {
  it("renders Sign In and Sign Up tabs", () => {
    render(<LoginCard />)
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Sign Up" })).toBeInTheDocument()
  })

  it("defaults to Sign In mode", () => {
    render(<LoginCard />)
    expect(
      screen.getByRole("heading", { name: /sign in to margin invest/i })
    ).toBeInTheDocument()
  })

  it("switches to Sign Up mode when Sign Up tab clicked", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    expect(
      screen.getByRole("heading", { name: /create your account/i })
    ).toBeInTheDocument()
  })

  it("switches back to Sign In mode", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByRole("button", { name: "Sign In" }))
    expect(
      screen.getByRole("heading", { name: /sign in to margin invest/i })
    ).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`
Expected: FAIL — no "Sign Up" button found

**Step 3: Implement segmented control in LoginCard**

In `login-card.tsx`, add `mode` state and segmented control UI. Key changes:

1. Add state: `const [mode, setMode] = useState<"signin" | "signup">("signin")`
2. Add `resetForm()` helper that clears all fields and errors when mode switches
3. Replace heading/subtitle to be mode-dependent
4. Add segmented control between subtitle and OAuth buttons:

```tsx
{/* Segmented Control */}
<div className="flex rounded-xl bg-white/[0.04] border border-white/[0.06] p-1 mb-6">
  <button
    type="button"
    onClick={() => { setMode("signin"); resetForm() }}
    className={`flex-1 py-2 text-[13px] font-medium rounded-lg transition-all duration-200 ${
      mode === "signin"
        ? "bg-accent text-white shadow-sm"
        : "text-text-secondary hover:text-text-primary"
    }`}
  >
    Sign In
  </button>
  <button
    type="button"
    onClick={() => { setMode("signup"); resetForm() }}
    className={`flex-1 py-2 text-[13px] font-medium rounded-lg transition-all duration-200 ${
      mode === "signup"
        ? "bg-accent text-white shadow-sm"
        : "text-text-secondary hover:text-text-primary"
    }`}
  >
    Sign Up
  </button>
</div>
```

5. Remove the old "Don't have an account? Create one" footer link

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`
Expected: PASS (all existing + 4 new tests)

**Step 5: Commit**

```bash
git add web/src/components/login/login-card.tsx web/src/components/login/__tests__/login-card.test.tsx
git commit -m "feat(web): add segmented control for sign-in/sign-up mode toggle"
```

---

### Task 3: Add sign-up form fields (confirm password + live checklist)

**Files:**
- Modify: `web/src/components/login/login-card.tsx`
- Modify: `web/src/components/login/__tests__/login-card.test.tsx`

**Step 1: Write failing tests for sign-up form**

```tsx
describe("sign-up form", () => {
  it("shows confirm password field in sign-up mode", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument()
  })

  it("does not show confirm password in sign-in mode", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByText("Continue with email"))
    expect(screen.queryByLabelText("Confirm Password")).not.toBeInTheDocument()
  })

  it("shows password checklist in sign-up mode", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    expect(screen.getByText("At least 12 characters")).toBeInTheDocument()
    expect(screen.getByText("One uppercase letter")).toBeInTheDocument()
    expect(screen.getByText("One lowercase letter")).toBeInTheDocument()
    expect(screen.getByText("One digit")).toBeInTheDocument()
    expect(screen.getByText("One special character")).toBeInTheDocument()
  })

  it("does not show password checklist in sign-in mode", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByText("Continue with email"))
    expect(screen.queryByText("At least 12 characters")).not.toBeInTheDocument()
  })

  it("shows 'Create Account' button in sign-up mode", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument()
  })

  it("uses type=email for email field in sign-up mode", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    expect(screen.getByLabelText("Email")).toHaveAttribute("type", "email")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`
Expected: FAIL — no "Confirm Password" field found

**Step 3: Implement sign-up form fields**

In `login-card.tsx`:

1. Add state: `confirmPassword`, `confirmPasswordError`, `serverError`, `successMessage`
2. Import `validatePassword` from `@/lib/password-validation`
3. Compute `passwordRules = validatePassword(password)` inline (derived state, no extra useState)
4. In the form, conditionally render based on `mode`:
   - Change email input `type` to `mode === "signup" ? "email" : "text"`
   - After password field (in sign-up mode): render checklist
   - After checklist (in sign-up mode): render confirm password field
   - Change submit button text: `mode === "signin" ? "Sign In" : "Create Account"`
5. Checklist UI:

```tsx
{mode === "signup" && (
  <div className="flex flex-col gap-1.5 -mt-1">
    {passwordRules.map((rule) => (
      <div key={rule.label} className="flex items-center gap-2">
        <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-200 ${
          rule.met ? "bg-green-400" : "bg-white/20"
        }`} />
        <span className={`text-[12px] transition-colors duration-200 ${
          rule.met ? "text-green-400" : "text-text-secondary"
        }`}>
          {rule.label}
        </span>
      </div>
    ))}
  </div>
)}
```

6. Confirm password field (sign-up mode):

```tsx
{mode === "signup" && (
  <div className="flex flex-col gap-1.5">
    <label htmlFor="confirmPassword" className="text-[13px] font-medium text-text-secondary">
      Confirm Password
    </label>
    <input
      id="confirmPassword"
      type="password"
      value={confirmPassword}
      onChange={(e) => { setConfirmPassword(e.target.value); setConfirmPasswordError("") }}
      onBlur={() => {
        if (confirmPassword && confirmPassword !== password) {
          setConfirmPasswordError("Passwords do not match")
        }
      }}
      className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
      placeholder="Re-enter your password"
    />
    {confirmPasswordError && (
      <p className="text-[12px] text-red-400">{confirmPasswordError}</p>
    )}
  </div>
)}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add web/src/components/login/login-card.tsx web/src/components/login/__tests__/login-card.test.tsx
git commit -m "feat(web): add sign-up form fields with password checklist and confirm password"
```

---

### Task 4: Add client-side validation and registration handler

**Files:**
- Modify: `web/src/components/login/login-card.tsx`
- Modify: `web/src/components/login/__tests__/login-card.test.tsx`

**Step 1: Write failing tests for validation and registration**

```tsx
describe("sign-up validation", () => {
  it("shows error when password rules not met on submit", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    await user.type(screen.getByLabelText("Email"), "test@example.com")
    await user.type(screen.getByLabelText("Password", { selector: "input" }), "short")
    await user.type(screen.getByLabelText("Confirm Password"), "short")
    await user.click(screen.getByRole("button", { name: /create account/i }))
    expect(screen.getByText(/password does not meet all requirements/i)).toBeInTheDocument()
  })

  it("shows error when passwords do not match on submit", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    await user.type(screen.getByLabelText("Email"), "test@example.com")
    await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
    await user.type(screen.getByLabelText("Confirm Password"), "MyPassword1!x")
    await user.click(screen.getByRole("button", { name: /create account/i }))
    expect(screen.getByText("Passwords do not match")).toBeInTheDocument()
  })

  it("shows confirm password mismatch error on blur", async () => {
    const user = userEvent.setup()
    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
    await user.type(screen.getByLabelText("Confirm Password"), "different")
    // Tab away to trigger blur
    await user.tab()
    expect(screen.getByText("Passwords do not match")).toBeInTheDocument()
  })
})

describe("sign-up registration", () => {
  it("calls register API and switches to sign-in on success", async () => {
    const user = userEvent.setup()
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 1, username: "test@example.com", email: "test@example.com" }),
    })

    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    await user.type(screen.getByLabelText("Email"), "test@example.com")
    await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
    await user.type(screen.getByLabelText("Confirm Password"), "MyPassword1!!")
    await user.click(screen.getByRole("button", { name: /create account/i }))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "test@example.com",
          email: "test@example.com",
          password: "MyPassword1!!",
        }),
      })
    })

    await waitFor(() => {
      expect(screen.getByText(/account created/i)).toBeInTheDocument()
    })

    // Should switch back to sign-in mode
    expect(
      screen.getByRole("heading", { name: /sign in to margin invest/i })
    ).toBeInTheDocument()
  })

  it("shows server error on failed registration", async () => {
    const user = userEvent.setup()
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: "A user with this email already exists" }),
    })

    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    await user.type(screen.getByLabelText("Email"), "test@example.com")
    await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
    await user.type(screen.getByLabelText("Confirm Password"), "MyPassword1!!")
    await user.click(screen.getByRole("button", { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText("A user with this email already exists")).toBeInTheDocument()
    })
  })

  it("shows network error message when fetch fails", async () => {
    const user = userEvent.setup()
    global.fetch = vi.fn().mockRejectedValue(new Error("Network error"))

    render(<LoginCard />)
    await user.click(screen.getByRole("button", { name: "Sign Up" }))
    await user.click(screen.getByText("Continue with email"))
    await user.type(screen.getByLabelText("Email"), "test@example.com")
    await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
    await user.type(screen.getByLabelText("Confirm Password"), "MyPassword1!!")
    await user.click(screen.getByRole("button", { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/unable to reach the server/i)).toBeInTheDocument()
    })
  })
})
```

Note: Add `import { waitFor } from "@testing-library/react"` to the imports if not already present.

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`
Expected: FAIL — no validation error shown, no fetch called

**Step 3: Implement validation and registration handler**

In `login-card.tsx`:

1. Add `isSubmitting` state to prevent double-submit
2. Add `handleSignUpSubmit` function:

```tsx
const handleSignUpSubmit = async (e: React.FormEvent) => {
  e.preventDefault()
  setServerError("")
  setConfirmPasswordError("")

  // Client-side validation
  if (!isPasswordValid(password)) {
    setServerError("Password does not meet all requirements")
    return
  }
  if (password !== confirmPassword) {
    setConfirmPasswordError("Passwords do not match")
    return
  }

  setIsSubmitting(true)
  try {
    const res = await fetch("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: email, email, password }),
    })

    if (!res.ok) {
      const data = await res.json()
      const detail = data.detail ?? data.message
      if (Array.isArray(detail)) {
        setServerError(detail.map((e: { msg?: string }) => e.msg).join(". "))
      } else {
        setServerError(detail || "Registration failed")
      }
      return
    }

    // Success — switch to sign-in mode with success message
    setMode("signin")
    resetForm()
    setSuccessMessage("Account created — sign in to continue")
  } catch {
    setServerError("Unable to reach the server. Please try again.")
  } finally {
    setIsSubmitting(false)
  }
}
```

3. Update the form's `onSubmit` to dispatch based on mode:

```tsx
<form onSubmit={mode === "signin" ? handleCredentialsSubmit : handleSignUpSubmit}>
```

4. Add error/success banners above the form fields:

```tsx
{serverError && (
  <p className="text-[13px] text-red-400 text-center mb-2">{serverError}</p>
)}
{successMessage && (
  <p className="text-[13px] text-green-400 text-center mb-2">{successMessage}</p>
)}
```

5. Import `isPasswordValid` from `@/lib/password-validation`

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add web/src/components/login/login-card.tsx web/src/components/login/__tests__/login-card.test.tsx
git commit -m "feat(web): add client-side validation and registration handler to LoginCard"
```

---

### Task 5: Add URL param support and redirect register page

**Files:**
- Modify: `web/src/components/login/login-card.tsx` (accept `initialMode` prop)
- Modify: `web/src/app/login/page.tsx` (read `?mode=signup` search param, pass to LoginCard)
- Modify: `web/src/app/register/page.tsx` (replace with redirect)
- Modify: `web/src/app/register/__tests__/page.test.tsx` (update test for redirect)
- Modify: `web/src/app/login/__tests__/page.test.tsx` (may need update)

**Step 1: Write failing tests**

Update register page test:

```tsx
// web/src/app/register/__tests__/page.test.tsx
import { describe, it, expect, vi } from "vitest"

const mockRedirect = vi.fn()

vi.mock("next/navigation", () => ({
  redirect: mockRedirect,
}))

describe("Register Page", () => {
  it("redirects to /login?mode=signup", async () => {
    // The register page is a server component that calls redirect()
    // We test that the redirect import is used correctly
    const { default: RegisterPage } = await import("../page")
    try {
      RegisterPage()
    } catch {
      // redirect() throws in test environment
    }
    expect(mockRedirect).toHaveBeenCalledWith("/login?mode=signup")
  })
})
```

Add LoginCard test for `initialMode`:

```tsx
describe("initialMode prop", () => {
  it("starts in sign-up mode when initialMode is signup", () => {
    render(<LoginCard initialMode="signup" />)
    expect(
      screen.getByRole("heading", { name: /create your account/i })
    ).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/app/register/__tests__/page.test.tsx src/components/login/__tests__/login-card.test.tsx`
Expected: FAIL

**Step 3: Implement changes**

Update `LoginCard` to accept `initialMode` prop:

```tsx
interface LoginCardProps {
  initialMode?: "signin" | "signup"
}

export function LoginCard({ initialMode = "signin" }: LoginCardProps) {
  const [mode, setMode] = useState<"signin" | "signup">(initialMode)
  // ... rest unchanged
}
```

Update `login/page.tsx` to read search params and pass to LoginCard:

```tsx
// web/src/app/login/page.tsx
import type { Metadata } from "next"
import { LoginScene } from "@/components/login/login-scene"
import { LoginCard } from "@/components/login/login-card"

export const metadata: Metadata = {
  title: "Sign In | Margin Invest",
  description: "Sign in to your Margin Invest account.",
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string }>
}) {
  const params = await searchParams
  const initialMode = params.mode === "signup" ? "signup" : "signin"

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-bg-primary overflow-hidden">
      <LoginScene />
      <div className="relative z-10">
        <LoginCard initialMode={initialMode} />
      </div>
    </div>
  )
}
```

Replace `register/page.tsx` with redirect:

```tsx
// web/src/app/register/page.tsx
import { redirect } from "next/navigation"

export default function RegisterPage() {
  redirect("/login?mode=signup")
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/app/register/__tests__/page.test.tsx src/components/login/__tests__/login-card.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/login/login-card.tsx web/src/app/login/page.tsx web/src/app/register/page.tsx web/src/app/register/__tests__/page.test.tsx web/src/components/login/__tests__/login-card.test.tsx
git commit -m "feat(web): redirect /register to /login?mode=signup, add initialMode prop"
```

---

### Task 6: Update existing tests and run full suite

**Files:**
- Modify: `web/src/components/login/__tests__/login-card.test.tsx` (fix any broken old tests)
- Modify: `web/src/app/login/__tests__/page.test.tsx` (update if needed for searchParams prop)

**Step 1: Run the full login-related test suite**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx src/app/login/__tests__/page.test.tsx src/app/register/__tests__/page.test.tsx src/lib/__tests__/password-validation.test.ts`

**Step 2: Fix any failing tests**

The old `login-card.test.tsx` has a test for "renders the register link" that checks for a link to `/register`. This link no longer exists (replaced by segmented control). **Delete this test.**

The `login/page.test.tsx` may need updating if it renders LoginPage — it now expects `searchParams` as a prop. Update accordingly:

```tsx
// If the test renders the page component directly, update to pass searchParams:
render(await LoginPage({ searchParams: Promise.resolve({}) }))
```

**Step 3: Run again and verify all pass**

Run: `cd web && npx vitest run src/components/login/ src/app/login/ src/app/register/ src/lib/__tests__/password-validation.test.ts`
Expected: PASS (all tests)

**Step 4: Commit any test fixes**

```bash
git add web/src/components/login/__tests__/login-card.test.tsx web/src/app/login/__tests__/page.test.tsx
git commit -m "test(web): update auth tests for inline sign-up flow"
```

---

### Task 7: Final verification — run full web test suite

**Step 1: Run the full web test suite**

Run: `cd web && npx vitest run`
Expected: All tests pass, no regressions

**Step 2: If any tests fail, fix them**

Likely failures: tests in other files that reference `/register` as a route. Search for these:

Run: `grep -r '"/register"' web/src/ --include="*.test.*"`

Fix any references.

**Step 3: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix(web): update remaining test references for register redirect"
```
