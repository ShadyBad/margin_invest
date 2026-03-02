# Account Page Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the Account page with terminal-card styling, sticky pill nav, GSAP entrance animations, custom confirmation modals, and merged Settings page.

**Architecture:** Refactor existing Account page components in-place. Add two new components (AccountPillNav, ConfirmationModal). Replace `window.prompt()` calls with modal-driven flows. Redirect Settings to Account. All existing functionality and API calls preserved.

**Tech Stack:** Next.js 15, React 19, Tailwind v4, GSAP (dynamic import), Vitest + @testing-library/react

**Design doc:** `docs/plans/2026-03-01-account-page-redesign-design.md`

---

### Task 1: Create ConfirmationModal component

**Files:**
- Create: `web/src/components/account/confirmation-modal.tsx`
- Create: `web/src/components/account/__tests__/confirmation-modal.test.tsx`

**Step 1: Write the failing test**

In `web/src/components/account/__tests__/confirmation-modal.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { ConfirmationModal } from "../confirmation-modal"

describe("ConfirmationModal", () => {
  const onClose = vi.fn()
  const onConfirm = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders title and description", () => {
    render(
      <ConfirmationModal
        open={true}
        title="Remove MFA"
        description="Enter your credentials to continue."
        onClose={onClose}
        onConfirm={onConfirm}
        confirmLabel="Remove MFA"
        confirmVariant="danger"
      />
    )
    expect(screen.getByText("Remove MFA")).toBeInTheDocument()
    expect(screen.getByText("Enter your credentials to continue.")).toBeInTheDocument()
  })

  it("renders nothing when open is false", () => {
    const { container } = render(
      <ConfirmationModal
        open={false}
        title="Remove MFA"
        onClose={onClose}
        onConfirm={onConfirm}
        confirmLabel="Confirm"
      />
    )
    expect(container.innerHTML).toBe("")
  })

  it("renders input fields when provided", () => {
    render(
      <ConfirmationModal
        open={true}
        title="Remove MFA"
        onClose={onClose}
        onConfirm={onConfirm}
        confirmLabel="Remove"
        fields={[
          { name: "password", label: "Current password", type: "password" },
          { name: "totp", label: "TOTP code", type: "text" },
        ]}
      />
    )
    expect(screen.getByLabelText("Current password")).toBeInTheDocument()
    expect(screen.getByLabelText("TOTP code")).toBeInTheDocument()
  })

  it("calls onConfirm with field values when submitted", async () => {
    const user = userEvent.setup()
    render(
      <ConfirmationModal
        open={true}
        title="Remove password"
        onClose={onClose}
        onConfirm={onConfirm}
        confirmLabel="Remove"
        fields={[{ name: "password", label: "Current password", type: "password" }]}
      />
    )
    await user.type(screen.getByLabelText("Current password"), "mypassword123")
    await user.click(screen.getByRole("button", { name: "Remove" }))
    expect(onConfirm).toHaveBeenCalledWith({ password: "mypassword123" })
  })

  it("calls onClose when Cancel is clicked", async () => {
    const user = userEvent.setup()
    render(
      <ConfirmationModal
        open={true}
        title="Test"
        onClose={onClose}
        onConfirm={onConfirm}
        confirmLabel="OK"
      />
    )
    await user.click(screen.getByRole("button", { name: "Cancel" }))
    expect(onClose).toHaveBeenCalled()
  })

  it("calls onClose when backdrop is clicked", async () => {
    const user = userEvent.setup()
    render(
      <ConfirmationModal
        open={true}
        title="Test"
        onClose={onClose}
        onConfirm={onConfirm}
        confirmLabel="OK"
      />
    )
    await user.click(screen.getByTestId("modal-backdrop"))
    expect(onClose).toHaveBeenCalled()
  })

  it("disables confirm button when loading", () => {
    render(
      <ConfirmationModal
        open={true}
        title="Test"
        onClose={onClose}
        onConfirm={onConfirm}
        confirmLabel="Remove"
        loading={true}
      />
    )
    expect(screen.getByRole("button", { name: /removing/i })).toBeDisabled()
  })

  it("shows error message when provided", () => {
    render(
      <ConfirmationModal
        open={true}
        title="Test"
        onClose={onClose}
        onConfirm={onConfirm}
        confirmLabel="OK"
        error="Invalid password"
      />
    )
    expect(screen.getByText("Invalid password")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/account/__tests__/confirmation-modal.test.tsx`
Expected: FAIL — module not found

**Step 3: Write the ConfirmationModal component**

In `web/src/components/account/confirmation-modal.tsx`:

```tsx
"use client"

import { useEffect, useRef, useState } from "react"

export interface ModalField {
  name: string
  label: string
  type: "text" | "password"
}

interface ConfirmationModalProps {
  open: boolean
  title: string
  description?: string
  fields?: ModalField[]
  onClose: () => void
  onConfirm: (values: Record<string, string>) => void
  confirmLabel: string
  confirmVariant?: "accent" | "danger"
  loading?: boolean
  error?: string | null
}

export function ConfirmationModal({
  open,
  title,
  description,
  fields = [],
  onClose,
  onConfirm,
  confirmLabel,
  confirmVariant = "accent",
  loading = false,
  error,
}: ConfirmationModalProps) {
  const [values, setValues] = useState<Record<string, string>>({})
  const dialogRef = useRef<HTMLDivElement>(null)

  // Reset values when modal opens/closes
  useEffect(() => {
    if (open) {
      setValues({})
    }
  }, [open])

  // Focus trap + escape key
  useEffect(() => {
    if (!open) return

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [open, onClose])

  // Focus first input or confirm button on open
  useEffect(() => {
    if (!open || !dialogRef.current) return
    const firstInput = dialogRef.current.querySelector("input")
    const confirmBtn = dialogRef.current.querySelector<HTMLButtonElement>(
      "[data-confirm]"
    )
    if (firstInput) {
      firstInput.focus()
    } else if (confirmBtn) {
      confirmBtn.focus()
    }
  }, [open])

  if (!open) return null

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onConfirm(values)
  }

  const confirmBtnClass =
    confirmVariant === "danger"
      ? "bg-red-500/90 text-white hover:bg-red-500"
      : "bg-accent text-bg-primary hover:bg-accent-hover"

  const loadingLabel = confirmLabel.replace(/^(\w+)/, (match) => {
    if (match.endsWith("e")) return match.slice(0, -1) + "ing"
    return match + "ing"
  })

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        data-testid="modal-backdrop"
        onClick={onClose}
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        className="terminal-card relative z-10 w-full max-w-sm mx-4 p-6 animate-in fade-in slide-in-from-bottom-2 duration-200"
      >
        <h3 id="modal-title" className="text-lg font-semibold text-text-primary mb-1">
          {title}
        </h3>

        {description && (
          <p className="text-sm text-text-secondary mb-4">{description}</p>
        )}

        <form onSubmit={handleSubmit}>
          {fields.length > 0 && (
            <div className="space-y-3 mb-4">
              {fields.map((field) => (
                <div key={field.name}>
                  <label
                    htmlFor={`modal-${field.name}`}
                    className="block text-sm text-text-secondary mb-1"
                  >
                    {field.label}
                  </label>
                  <input
                    id={`modal-${field.name}`}
                    type={field.type}
                    value={values[field.name] ?? ""}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, [field.name]: e.target.value }))
                    }
                    className="w-full px-3 py-2 bg-bg-primary border border-border-primary rounded-lg text-sm text-text-primary focus:border-accent focus:outline-none"
                    required
                  />
                </div>
              ))}
            </div>
          )}

          {error && (
            <p className="text-sm text-red-400 mb-3">{error}</p>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-text-secondary font-medium text-sm hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              data-confirm
              className={`px-4 py-2 font-medium text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${confirmBtnClass}`}
            >
              {loading ? loadingLabel : confirmLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/account/__tests__/confirmation-modal.test.tsx`
Expected: PASS (all 8 tests)

**Step 5: Commit**

```bash
git add web/src/components/account/confirmation-modal.tsx web/src/components/account/__tests__/confirmation-modal.test.tsx
git commit -m "feat(web): add ConfirmationModal component for account page"
```

---

### Task 2: Create AccountPillNav component

**Files:**
- Create: `web/src/components/account/account-pill-nav.tsx`
- Create: `web/src/components/account/__tests__/account-pill-nav.test.tsx`

**Step 1: Write the failing test**

In `web/src/components/account/__tests__/account-pill-nav.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { AccountPillNav } from "../account-pill-nav"

describe("AccountPillNav", () => {
  const sections = ["Profile", "Security", "Billing", "Preferences"]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders all section pills", () => {
    render(<AccountPillNav sections={sections} activeSection="Profile" />)
    for (const section of sections) {
      expect(screen.getByRole("button", { name: section })).toBeInTheDocument()
    }
  })

  it("highlights the active section", () => {
    render(<AccountPillNav sections={sections} activeSection="Security" />)
    const activeBtn = screen.getByRole("button", { name: "Security" })
    expect(activeBtn.className).toContain("text-accent")
  })

  it("calls onNavigate when a pill is clicked", async () => {
    const onNavigate = vi.fn()
    const user = userEvent.setup()
    render(
      <AccountPillNav
        sections={sections}
        activeSection="Profile"
        onNavigate={onNavigate}
      />
    )
    await user.click(screen.getByRole("button", { name: "Billing" }))
    expect(onNavigate).toHaveBeenCalledWith("Billing")
  })

  it("renders with nav role", () => {
    render(<AccountPillNav sections={sections} activeSection="Profile" />)
    expect(screen.getByRole("navigation", { name: /account/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/account/__tests__/account-pill-nav.test.tsx`
Expected: FAIL — module not found

**Step 3: Write the AccountPillNav component**

In `web/src/components/account/account-pill-nav.tsx`:

```tsx
"use client"

interface AccountPillNavProps {
  sections: string[]
  activeSection: string
  onNavigate?: (section: string) => void
}

export function AccountPillNav({
  sections,
  activeSection,
  onNavigate,
}: AccountPillNavProps) {
  return (
    <nav
      aria-label="Account sections"
      className="sticky top-16 z-10 backdrop-blur-lg bg-bg-primary/80 border-b border-border-subtle py-3 -mx-4 px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8 overflow-x-auto"
    >
      <div className="flex gap-1">
        {sections.map((section) => {
          const isActive = section === activeSection
          return (
            <button
              key={section}
              onClick={() => onNavigate?.(section)}
              className={`text-sm font-medium px-4 py-1.5 rounded-full transition-colors whitespace-nowrap ${
                isActive
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {section}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/account/__tests__/account-pill-nav.test.tsx`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add web/src/components/account/account-pill-nav.tsx web/src/components/account/__tests__/account-pill-nav.test.tsx
git commit -m "feat(web): add AccountPillNav sticky navigation component"
```

---

### Task 3: Extend Avatar component to support 80px size

**Files:**
- Modify: `web/src/components/ui/avatar.tsx`
- Modify: `web/src/components/account/__tests__/profile-section.test.tsx`

**Step 1: Update Avatar sizes**

In `web/src/components/ui/avatar.tsx`, change the SIZES const:

```tsx
const SIZES = { sm: 24, md: 32, lg: 48, xl: 80 } as const
```

This adds an `xl` size (80px) while preserving all existing sizes. No test changes needed for avatar itself as tests mock it.

**Step 2: Run existing tests to verify nothing breaks**

Run: `cd web && npx vitest run src/components/account/__tests__/profile-section.test.tsx`
Expected: PASS (all existing tests still pass)

**Step 3: Commit**

```bash
git add web/src/components/ui/avatar.tsx
git commit -m "feat(web): add xl (80px) size to Avatar component"
```

---

### Task 4: Restyle ProfileSection with terminal-card and micro-labels

**Files:**
- Modify: `web/src/components/account/profile-section.tsx`
- Modify: `web/src/components/account/__tests__/profile-section.test.tsx`

**Step 1: Update profile-section.tsx**

Replace the entire `return` JSX in `ProfileSection` with the redesigned layout. Key changes:
- Outer `<section>`: class from `bg-bg-elevated border border-border-primary rounded-sm p-6` → `terminal-card p-6 md:p-8`
- `<h2>`: from `text-lg font-bold text-text-primary mb-4` → `text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-6`
- Avatar: `size="lg"` → `size="xl"`
- Name: add `text-xl font-semibold` (was `text-text-primary font-medium`)
- Provider pill: no change (already good)
- Action buttons: use `gap-3` instead of `gap-2`
- Error text: from `text-red-400` → `text-bearish`

Full replacement for the JSX return:

```tsx
  return (
    <section id="profile" className="terminal-card p-6 md:p-8">
      <h2 className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-6">
        Profile
      </h2>
      {session?.user ? (
        <div className="space-y-4">
          <div className="flex items-center gap-5">
            <Avatar
              name={session.user.name || session.user.email || ""}
              avatarUrl={avatarUrl}
              oauthAvatarUrl={oauthAvatarUrl}
              size="xl"
            />
            <div>
              <div className="text-xl font-semibold text-text-primary">
                {session.user.name || "User"}
              </div>
              <div className="text-sm text-text-secondary mt-0.5">
                {session.user.email}
              </div>
              <span className="inline-block mt-2 px-2 py-0.5 text-xs font-medium rounded-full bg-bg-subtle text-text-secondary border border-border-primary">
                {providerLabel}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="text-sm text-accent hover:text-accent-hover transition-colors disabled:opacity-50"
            >
              {uploading ? "Uploading..." : "Upload photo"}
            </button>
            {avatarUrl && (
              <button
                onClick={handleRemove}
                className="text-sm text-text-secondary hover:text-red-400 transition-colors"
              >
                Remove
              </button>
            )}
          </div>
          {error && (
            <p className="text-sm text-bearish">{error}</p>
          )}
        </div>
      ) : (
        <p className="text-text-secondary">Loading profile information...</p>
      )}
    </section>
  )
```

**Step 2: Update the profile test**

In `web/src/components/account/__tests__/profile-section.test.tsx`, update the heading assertion. The heading text is still "Profile" but the level is still h2, and it's now in uppercase tracking style — the test uses `getByRole("heading", { name: /profile/i })` which still works since the text content is "Profile".

Also update the "Upload Avatar" text to "Upload photo":

```tsx
  it('shows "Upload photo" button', () => {
    mockSession()
    render(<ProfileSection />)
    expect(screen.getByText("Upload photo")).toBeInTheDocument()
  })
```

**Step 3: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/account/__tests__/profile-section.test.tsx`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/components/account/profile-section.tsx web/src/components/account/__tests__/profile-section.test.tsx
git commit -m "feat(web): restyle ProfileSection with terminal-card and micro-labels"
```

---

### Task 5: Restyle SecuritySection with terminal-card and ConfirmationModal

**Files:**
- Modify: `web/src/components/account/security-section.tsx`
- Modify: `web/src/components/account/__tests__/security-section.test.tsx`

**Step 1: Update security-section.tsx**

Key changes:
- Import `ConfirmationModal` and `ModalField`
- Outer `<section>`: class → `terminal-card p-6 md:p-8`
- `<h2>`: → `text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-6`
- Dividers: `border-border-primary` → `border-border-subtle`
- Replace `handleRegenerateCodes` to use modal state instead of `window.prompt`:
  - Add state: `const [regenModalOpen, setRegenModalOpen] = useState(false)`
  - Add state: `const [disableModalOpen, setDisableModalOpen] = useState(false)`
  - Add state: `const [removePasswordModalOpen, setRemovePasswordModalOpen] = useState(false)`
  - Add state: `const [modalError, setModalError] = useState<string | null>(null)`
- Replace `handleRegenerateCodes`:
  ```tsx
  async function handleRegenerateCodes(values: Record<string, string>) {
    const password = values.password
    if (!password) return
    setModalError(null)
    setRegenerating(true)
    try {
      const res = await fetch("/api/v1/auth/mfa/regenerate-recovery-codes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to regenerate recovery codes" }))
        throw new Error(data.detail ?? data.message ?? "Failed to regenerate recovery codes")
      }
      const data = await res.json()
      setNewRecoveryCodes(data.codes)
      setRegenModalOpen(false)
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to regenerate recovery codes")
    } finally {
      setRegenerating(false)
    }
  }
  ```
- Replace `handleDisableMfa`:
  ```tsx
  async function handleDisableMfa(values: Record<string, string>) {
    const password = values.password
    const totpCode = values.totp
    if (!password || !totpCode) return
    setModalError(null)
    setDisabling(true)
    try {
      const res = await fetch("/api/v1/auth/mfa/disable", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password, totp_code: totpCode }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to disable MFA" }))
        throw new Error(data.detail ?? data.message ?? "Failed to disable MFA")
      }
      await update()
      setDisableModalOpen(false)
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to disable MFA")
    } finally {
      setDisabling(false)
    }
  }
  ```
- Update MFA callbacks: `onRegenerateCodes={() => setRegenModalOpen(true)}`, `onDisableMfa={() => setDisableModalOpen(true)}`
- Add modal JSX at the end of the section (before closing `</section>`):
  ```tsx
  <ConfirmationModal
    open={regenModalOpen}
    title="Regenerate Recovery Codes"
    description="Enter your current password to generate new recovery codes."
    fields={[{ name: "password", label: "Current password", type: "password" }]}
    onClose={() => { setRegenModalOpen(false); setModalError(null) }}
    onConfirm={handleRegenerateCodes}
    confirmLabel="Regenerate"
    loading={regenerating}
    error={modalError}
  />
  <ConfirmationModal
    open={disableModalOpen}
    title="Remove MFA"
    description="Enter your credentials to remove multi-factor authentication."
    fields={[
      { name: "password", label: "Current password", type: "password" },
      { name: "totp", label: "TOTP code", type: "text" },
    ]}
    onClose={() => { setDisableModalOpen(false); setModalError(null) }}
    onConfirm={handleDisableMfa}
    confirmLabel="Remove"
    confirmVariant="danger"
    loading={disabling}
    error={modalError}
  />
  ```

**Step 2: Update tests**

In `web/src/components/account/__tests__/security-section.test.tsx`, the existing tests should still pass because the heading text "Security" is still present (just styled differently). The heading role assertion `screen.getByRole("heading", { name: /security/i })` will still work.

Run the tests and fix any assertion mismatches due to styling changes.

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/account/__tests__/security-section.test.tsx`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/components/account/security-section.tsx web/src/components/account/__tests__/security-section.test.tsx
git commit -m "feat(web): restyle SecuritySection with terminal-card and confirmation modals"
```

---

### Task 6: Restyle PasswordSection with terminal-card styling and modal for password removal

**Files:**
- Modify: `web/src/components/account/password-section.tsx`
- Modify: `web/src/components/account/__tests__/password-section.test.tsx`

**Step 1: Update password-section.tsx**

Key changes:
- Add `ConfirmationModal` import
- Add modal state: `const [removeModalOpen, setRemoveModalOpen] = useState(false)`, `const [modalError, setModalError] = useState<string | null>(null)`
- Sub-heading: keep existing `text-sm font-medium text-text-secondary uppercase tracking-wide mb-3`
- Add status indicator (emerald/amber dot) before the heading text
- All input classes: `rounded-sm` → `rounded-lg`
- All button classes: `rounded-sm` → `rounded-lg`
- Replace `handleRemovePassword` to use modal:
  ```tsx
  async function handleRemovePassword(values: Record<string, string>) {
    const password = values.password
    if (!password) return
    setError(null)
    setSuccess(null)
    setModalError(null)
    setRemoving(true)
    try {
      const res = await fetch("/api/v1/auth/remove-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to remove password" }))
        throw new Error(data.detail ?? data.message ?? "Failed to remove password")
      }
      setSuccess("Password removed. You can now sign in with your linked provider only.")
      setRemoveModalOpen(false)
      resetForm()
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to remove password")
    } finally {
      setRemoving(false)
    }
  }
  ```
- Replace `Remove Password` button's `onClick` to `() => setRemoveModalOpen(true)`
- Add modal JSX at the end:
  ```tsx
  <ConfirmationModal
    open={removeModalOpen}
    title="Remove Password"
    description="Enter your current password to remove it. You'll only be able to sign in with your linked provider."
    fields={[{ name: "password", label: "Current password", type: "password" }]}
    onClose={() => { setRemoveModalOpen(false); setModalError(null) }}
    onConfirm={handleRemovePassword}
    confirmLabel="Remove"
    confirmVariant="danger"
    loading={removing}
    error={modalError}
  />
  ```
- Add status dot before heading in both has-password and no-password states:
  ```tsx
  <div className="flex items-center gap-2 mb-3">
    <span className={`w-2 h-2 rounded-full ${hasPassword ? "bg-emerald-500" : "bg-amber-500"}`} />
    <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wide">
      Password
    </h3>
  </div>
  ```

**Step 2: Update tests**

The password-section test file may need updates since the "Remove Password" button now opens a modal instead of calling `window.prompt`. Verify existing tests pass — the button text "Remove Password" is the same, the click just opens a modal now.

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/account/__tests__/password-section.test.tsx`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/components/account/password-section.tsx web/src/components/account/__tests__/password-section.test.tsx
git commit -m "feat(web): restyle PasswordSection with status dots and confirmation modal"
```

---

### Task 7: Restyle MfaStatus with terminal-card styling and pulse animation

**Files:**
- Modify: `web/src/components/account/mfa-status.tsx`
- Modify: `web/src/components/account/__tests__/mfa-status.test.tsx`

**Step 1: Update mfa-status.tsx**

Key changes:
- Status dot for "Enabled" state: add `animate-pulse` to the emerald dot class
- Alert boxes: `rounded-sm` → `rounded-lg`
- "Set Up MFA" link: `rounded-sm` → `rounded-lg`
- Button classes: `rounded-sm` → `rounded-lg`
- Keep all existing logic and conditional rendering unchanged

Specific changes:
- Line with `<span className="w-2 h-2 rounded-full bg-emerald-500"` in State 3 → `<span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"`
- `rounded-sm border border-amber-500/30` → `rounded-lg border border-amber-500/30`
- `rounded-sm border border-red-500/30` → `rounded-lg border border-red-500/30`
- `inline-flex px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm` → `inline-flex px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-lg`
- `px-4 py-2 border border-border-primary text-text-primary font-medium text-sm rounded-sm` → with `rounded-lg`

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/account/__tests__/mfa-status.test.tsx`
Expected: PASS (no behavioral changes, only styling)

**Step 3: Commit**

```bash
git add web/src/components/account/mfa-status.tsx
git commit -m "feat(web): restyle MfaStatus with rounded-lg and pulse animation"
```

---

### Task 8: Restyle ProviderIcons with terminal-card tiles

**Files:**
- Modify: `web/src/components/account/provider-icons.tsx`
- Modify: `web/src/components/account/__tests__/provider-icons.test.tsx`

**Step 1: Update provider-icons.tsx**

Key changes:
- Sub-heading: "Authentication Methods" → "Connected Accounts", style → `text-base font-medium text-text-primary mb-4`
- Provider tile: from `w-12 h-12 rounded-xl border` icon circle to `terminal-card p-4 flex flex-col items-center gap-2 min-w-[100px]` card tile
- Connected state border: `border-emerald-500/40` → `border-accent/30` (using accent token)
- Gap: `gap-4` → `gap-3`
- Remove the separate icon circle div — integrate icon directly in the card
- Keep all provider icons, states, and functionality identical

Replace the ProviderIcon component's JSX:

```tsx
function ProviderIcon({ provider, onConnect, onDisconnect, connecting }: {
  provider: ProviderConfig
  onConnect?: (provider: string) => void
  onDisconnect?: (provider: string) => void
  connecting: boolean
}) {
  const { id, label, state, icon } = provider

  const stateLabel =
    state === "connected" ? "Connected"
    : state === "available" ? "Not connected"
    : "Coming soon"

  const ariaLabel = `${label} \u2014 ${stateLabel}`

  const borderClass =
    state === "connected"
      ? "border-accent/30"
      : ""

  const opacityClass = state === "coming_soon" ? "opacity-40" : ""

  return (
    <div
      className={`terminal-card p-4 flex flex-col items-center gap-2 min-w-[100px] ${borderClass} ${opacityClass}`}
      aria-label={ariaLabel}
      aria-disabled={state === "coming_soon" ? "true" : undefined}
    >
      <div className="text-text-primary">
        {icon}
      </div>
      <span className="text-xs font-medium text-text-primary">{label}</span>
      {state === "connected" && (
        <>
          <span className="text-xs text-emerald-400">Connected</span>
          {onDisconnect && (
            <button
              onClick={() => onDisconnect(id)}
              className="text-xs text-text-secondary hover:text-red-400 transition-colors"
              aria-label={`Disconnect ${label} account`}
            >
              Disconnect
            </button>
          )}
        </>
      )}
      {state === "available" && (
        <>
          <span className="text-xs text-text-secondary">Not connected</span>
          {onConnect && (
            <button
              onClick={() => onConnect(id)}
              disabled={connecting}
              className="text-xs text-accent hover:text-accent-hover transition-colors disabled:opacity-50"
              aria-label={`Connect ${label} account`}
            >
              {connecting ? "Connecting..." : "Connect"}
            </button>
          )}
        </>
      )}
      {state === "coming_soon" && (
        <span className="text-xs text-text-secondary">Coming soon</span>
      )}
    </div>
  )
}
```

Also update the ProviderIcons heading:

```tsx
<h3 className="text-base font-medium text-text-primary mb-4">
  Connected Accounts
</h3>
```

**Step 2: Update provider tests**

In `web/src/components/account/__tests__/provider-icons.test.tsx`, update any assertions that reference "Authentication Methods" to "Connected Accounts".

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/account/__tests__/provider-icons.test.tsx`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/components/account/provider-icons.tsx web/src/components/account/__tests__/provider-icons.test.tsx
git commit -m "feat(web): restyle ProviderIcons as terminal-card tiles"
```

---

### Task 9: Restyle BillingSection with terminal-card and upgrade layout

**Files:**
- Modify: `web/src/components/account/billing-section.tsx`
- Modify: `web/src/components/account/__tests__/billing-section.test.tsx`

**Step 1: Update billing-section.tsx**

Key changes:
- All `<section>` wrappers: `bg-bg-elevated border border-border-primary rounded-sm p-6` → `terminal-card p-6 md:p-8`
- `<h2>`: → `text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-6`
- Add inner card for current plan: `<div className="bg-bg-subtle/50 rounded-lg p-4 mb-4">`
- Button classes: `rounded-sm` → `rounded-lg`
- Alert classes: `rounded-sm` → `rounded-lg`
- Add `id="billing"` to the section element
- Keep all fetching, checkout, portal logic identical

**Step 2: Update tests**

The billing tests search for heading via `screen.getByRole("heading", { name: /billing/i })`. Since the h2 text is still "Billing", the role-based query should still work. Update test assertions for the loading skeleton to use `terminal-card` class if any assertions check the section class.

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/account/__tests__/billing-section.test.tsx`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/components/account/billing-section.tsx web/src/components/account/__tests__/billing-section.test.tsx
git commit -m "feat(web): restyle BillingSection with terminal-card and inner plan card"
```

---

### Task 10: Rewrite Account page with pill nav, GSAP animations, and merged Preferences

**Files:**
- Modify: `web/src/app/account/page.tsx`
- Create: `web/src/components/account/account-page-client.tsx`
- Modify: `web/src/app/settings/page.tsx`

**Step 1: Create client wrapper**

The Account page is currently a server component. The pill nav needs `IntersectionObserver` and GSAP needs `useEffect`, so create a client wrapper component.

In `web/src/components/account/account-page-client.tsx`:

```tsx
"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { AccountPillNav } from "./account-pill-nav"
import { ProfileSection } from "./profile-section"
import { SecuritySection } from "./security-section"
import { BillingSection } from "./billing-section"

const SECTIONS = ["Profile", "Security", "Billing", "Preferences"] as const

export function AccountPageClient() {
  const [activeSection, setActiveSection] = useState<string>("Profile")
  const sectionRefs = useRef<Map<string, HTMLElement>>(new Map())
  const containerRef = useRef<HTMLDivElement>(null)

  const registerRef = useCallback((section: string, el: HTMLElement | null) => {
    if (el) {
      sectionRefs.current.set(section, el)
    } else {
      sectionRefs.current.delete(section)
    }
  }, [])

  // IntersectionObserver to track active section
  useEffect(() => {
    const observers: IntersectionObserver[] = []

    for (const [section, el] of sectionRefs.current.entries()) {
      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              setActiveSection(section)
            }
          }
        },
        { rootMargin: "-20% 0px -70% 0px" }
      )
      observer.observe(el)
      observers.push(observer)
    }

    return () => {
      for (const obs of observers) obs.disconnect()
    }
  }, [])

  // GSAP stagger entrance animation
  useEffect(() => {
    if (!containerRef.current) return

    let cancelled = false

    async function animate() {
      const gsapModule = await import("gsap")
      if (cancelled) return
      const gsap = gsapModule.default
      const sections = containerRef.current?.querySelectorAll("[data-account-section]")
      if (!sections?.length) return

      gsap.set(sections, { opacity: 0, y: 16 })
      gsap.to(sections, {
        opacity: 1,
        y: 0,
        duration: 0.4,
        ease: "power2.out",
        stagger: 0.08,
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
    }
  }, [])

  function handleNavigate(section: string) {
    const el = sectionRefs.current.get(section)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  return (
    <div ref={containerRef}>
      <h1 className="text-4xl font-bold text-text-primary mb-2">Account</h1>
      <p className="text-sm text-text-secondary mb-6">
        Manage your profile, security, and billing settings.
      </p>

      <AccountPillNav
        sections={[...SECTIONS]}
        activeSection={activeSection}
        onNavigate={handleNavigate}
      />

      <div className="space-y-8 mt-8">
        <div
          data-account-section
          ref={(el) => registerRef("Profile", el)}
        >
          <ProfileSection />
        </div>
        <div
          data-account-section
          ref={(el) => registerRef("Security", el)}
        >
          <SecuritySection />
        </div>
        <div
          data-account-section
          ref={(el) => registerRef("Billing", el)}
        >
          <BillingSection />
        </div>
        <div
          data-account-section
          ref={(el) => registerRef("Preferences", el)}
        >
          <section id="preferences" className="terminal-card p-6 md:p-8">
            <h2 className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-6">
              Preferences
            </h2>
            <p className="text-sm text-text-secondary">
              Product preferences coming soon.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Simplify the Account page server component**

In `web/src/app/account/page.tsx`:

```tsx
import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { AccountPageClient } from "@/components/account/account-page-client"

export default async function AccountPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  return (
    <AppShell>
      <AccountPageClient />
    </AppShell>
  )
}
```

**Step 3: Redirect Settings page to Account**

In `web/src/app/settings/page.tsx`:

```tsx
import { redirect } from "next/navigation"

export default function SettingsPage() {
  redirect("/account")
}
```

**Step 4: Run all account tests**

Run: `cd web && npx vitest run src/components/account/`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/app/account/page.tsx web/src/components/account/account-page-client.tsx web/src/app/settings/page.tsx
git commit -m "feat(web): rewrite Account page with pill nav, GSAP animations, merged Preferences"
```

---

### Task 11: Run full test suite and fix any regressions

**Files:**
- Any files with test failures

**Step 1: Run all web tests**

Run: `cd web && npx vitest run`
Expected: PASS (all ~1285 tests)

**Step 2: Fix any failures**

If any tests fail due to the restyling (e.g., snapshot mismatches, class name assertions, text content changes), fix them. Common issues:
- "Upload Avatar" text changed to "Upload photo"
- "Authentication Methods" heading changed to "Connected Accounts"
- Section wrapper class changes from `bg-bg-elevated...` to `terminal-card...`

**Step 3: Commit fixes if any**

```bash
git add -u
git commit -m "fix(web): fix test regressions from account page redesign"
```

---

### Task 12: Visual QA in browser

**Files:** None (verification only)

**Step 1: Start dev server**

Run: `cd web && npm run dev`

**Step 2: Verify in browser**

Navigate to `http://localhost:3000/account` and verify:
- [ ] Page loads with staggered entrance animation
- [ ] Sticky pill nav appears and tracks scroll position
- [ ] Clicking pills smooth-scrolls to sections
- [ ] Profile section shows 80px avatar, name, email, provider badge
- [ ] Security section has terminal-card provider tiles
- [ ] Password status dot is emerald (has password) or amber (no password)
- [ ] MFA enabled shows pulsing emerald dot
- [ ] Clicking "Remove MFA" opens custom modal (not browser prompt)
- [ ] Clicking "Regenerate Recovery Codes" opens custom modal
- [ ] Clicking "Remove Password" opens custom modal
- [ ] Billing section shows plan badge and status pill in inner card
- [ ] Preferences section shows placeholder
- [ ] `/settings` redirects to `/account`
- [ ] Dark mode looks correct
- [ ] Mobile viewport: pill nav scrolls horizontally, sections stack

**Step 3: Fix any visual issues found**

**Step 4: Final commit if needed**

```bash
git add -u
git commit -m "fix(web): visual QA polish for account page redesign"
```
