# Inline Auth UI Design

**Date:** 2026-02-19
**Status:** Approved

## Problem

1. **Disconnected sign-up page**: The register page (`/register`) uses completely different styling from the login page — hardcoded hex colors, no glassmorphism, no OAuth buttons, no background scene. Users navigate away from the polished login experience.
2. **False sign-up errors**: The frontend only enforces `minLength={12}` via HTML5, but the backend requires 4 additional complexity rules (uppercase, lowercase, digit, special character). Users who type a valid-length password get unexpected server errors on submit.

## Solution

Extend `LoginCard` to support both sign-in and sign-up modes inline. Add client-side password validation mirroring the backend rules with a live checklist. Redirect the old register page.

## Root Cause: Sign-Up Error

The backend (`api/src/margin_api/services/auth.py`) validates passwords with 5 rules:
- 12+ characters
- At least one uppercase letter (`/[A-Z]/`)
- At least one lowercase letter (`/[a-z]/`)
- At least one digit (`/[0-9]/`)
- At least one special character (`/[^A-Za-z0-9]/`)

The frontend (`web/src/app/register/page.tsx`) only enforces `minLength={12}` via HTML5. A password like `mypassword12` passes the frontend check but fails the backend check with "Password must contain at least one uppercase letter" — appearing as a post-submit error.

**Fix:** Mirror all 5 backend rules in client-side validation with a live checklist.

## UI Structure

The login card layout in both modes:

1. Logo
2. Heading — "Sign in to Margin Invest" / "Create your account"
3. Subtitle — "Secure login with bank-grade encryption" / "Start analyzing investments today"
4. **Segmented control** — pill-style `[Sign In | Sign Up]`. Active pill: `bg-accent` + white text. Inactive: transparent + `text-text-secondary`.
5. OAuth icon buttons (Google, Apple disabled, GitHub) — always visible in both modes
6. "or" divider
7. Credentials form (expand/collapse via "Continue with email" toggle, unchanged behavior):
   - **Sign-in mode:** Email + Password (with show/hide toggle) + "Sign In" button
   - **Sign-up mode:** Email (`type="email"`) + Password (with show/hide toggle) + Confirm Password + live checklist + "Create Account" button
8. "Continue with email" / "Back to social login" toggle (unchanged)

The old footer "Don't have an account? Create one" is removed — the segmented control handles mode switching.

## Segmented Control

- Positioned below subtitle, above OAuth buttons
- Two options: "Sign In" | "Sign Up"
- Active state: `bg-accent text-white`
- Inactive state: `bg-transparent text-text-secondary`
- Container: `rounded-xl bg-white/[0.04] border border-white/[0.06] p-1`
- Switching modes resets form fields and errors

## Password Validation

**Live checklist (sign-up mode only):**
- Sits below the password field
- Each rule: small circle indicator (green check when satisfied, muted dot when not) + rule text
- `text-[12px]` sizing, compact layout
- Updates in real-time on keystroke (pure regex, no debounce needed)

**Rules:**
| Rule | Regex | Label |
|------|-------|-------|
| Length | `.{12,}` | At least 12 characters |
| Uppercase | `[A-Z]` | One uppercase letter |
| Lowercase | `[a-z]` | One lowercase letter |
| Digit | `[0-9]` | One digit |
| Special | `[^A-Za-z0-9]` | One special character |

**Confirm password:**
- Validates on blur: "Passwords do not match" inline error below field
- Also validated on submit

**Validation triggers:**
- Password rules: real-time for checklist display, formal validation on blur + submit
- Confirm password: on blur + on submit
- Email: HTML5 `type="email"` + on submit
- Error banner: only for server-side errors (duplicate email, network failure)
- Client-side field errors: inline below their respective fields

**Submit behavior:**
- Button always clickable (no disabled state)
- On submit: run all client-side validations first; if any fail, show inline errors, don't call server
- If client-side passes: `POST /api/v1/auth/register` with `{ username: email, email, password }`
- On success: switch to sign-in mode, green success banner "Account created — sign in to continue", clear fields
- On server error: show in error banner at top of form

## Registration Flow

- Uses `username: email` (email serves as the username)
- No backend changes needed: `RegisterRequest` accepts any string 3-150 chars for username
- On success: auto-switch to sign-in mode with success message

## Old Register Page

Replace `/register` page content with a redirect to `/login?mode=signup`. LoginCard reads the `mode` URL param on mount to initialize in sign-up mode if linked directly.

## Files Changed

1. `web/src/components/login/login-card.tsx` — Segmented control, sign-up form, client-side validation, live checklist, registration API handler
2. `web/src/app/register/page.tsx` — Replace with redirect to `/login?mode=signup`

## What Stays Unchanged

- OAuth buttons and handlers
- MFA flow (setup + verify pages)
- NextAuth configuration and callbacks
- All backend endpoints and schemas
- `sessionStorage` credential storage for MFA flow
- Three.js background scene
- Login page wrapper (`login/page.tsx`)

## Tests

- Segmented control toggles between sign-in and sign-up modes
- Sign-up form renders correct fields (email, password, confirm password, checklist)
- Live password checklist updates correctly for each rule
- Client-side validation prevents submit with weak password
- Successful registration calls API and switches to sign-in mode
- Confirm password mismatch shows inline error
- Register page redirects to `/login?mode=signup`
