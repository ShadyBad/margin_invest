# Password Reset Design

## Overview

Add email-based password reset to the credentials login flow. Users click "Forgot password?" on the login card, receive an email with a time-limited link, and set a new password.

## Decisions

- **Email service:** Resend (Python SDK)
- **Token mechanism:** Reuse existing `MfaChallengeToken` table with 60-minute TTL
- **MFA handling:** Reset bypasses MFA. Email link proves identity. MFA required on next login if enabled.
- **UI placement:** "Forgot password?" link on the login card. Reset form swaps in-place. Separate `/reset-password` page for the link target.

## User Flow

1. User clicks "Forgot password?" below the password field on the login card
2. Form swaps to an email-only input with "Send reset link" button
3. `POST /api/v1/auth/forgot-password` — always returns 200 (no email enumeration)
4. Backend sends email via Resend: link to `{APP_URL}/reset-password?token=<hex>&userId=<id>`
5. User clicks link → `/reset-password` page with new password + confirm fields
6. `POST /api/v1/auth/reset-password` — verifies token, sets new password
7. Redirect to `/login?resetSuccess=true` with success message

## Backend

### New dependency

`resend` Python SDK added to api package.

### New config

- `RESEND_API_KEY` — Resend API key (empty in dev → log URL to console)
- `APP_URL` — Frontend base URL (e.g., `https://margin-invest.vercel.app`)

### New service: `api/src/margin_api/services/email.py`

`EmailService` with `send_password_reset(to_email, reset_url)`. Uses Resend API. Falls back to console logging when no API key is set (local dev).

### New endpoints

**`POST /api/v1/auth/forgot-password`**

- Request: `{ "email": "user@example.com" }`
- Response: `200 { "message": "If an account exists, a reset link has been sent." }`
- Look up user by email. If found, create challenge token (60 min TTL), send email.
- Rate limit: skip if 3+ unused/unexpired tokens exist for user.

**`POST /api/v1/auth/reset-password`**

- Request: `{ "user_id": int, "token": "hex", "new_password": "string" }`
- Response: `200 { "message": "Password has been reset." }` or `403` / `400`
- Verify challenge token (single-use, 60 min). Validate password rules. Hash with Argon2id.
- Update `password_hash`, `password_changed_at`. Clear `failed_login_attempts`, `locked_until`.

Both endpoints are unauthenticated and served through the existing auth proxy route.

### Auth service changes

New method `reset_password(session, user_id, raw_token, new_password)` that verifies the token and sets the new password. Reuses `verify_challenge_token` and `_validate_password`.

## Frontend

### Login card changes (`login-card.tsx`)

- "Forgot password?" link below password field (sign-in mode only)
- Clicking swaps the form to email input + "Send reset link" button
- Success: green message "Check your email for a reset link"
- "Back to sign in" link to return to normal form
- New `resetSuccess` search param: shows "Password reset successfully. Sign in with your new password."

### New page: `/reset-password`

- `web/src/app/reset-password/page.tsx`
- Reads `token` and `userId` from search params
- New password + confirm password fields with same validation checklist as sign-up
- On submit: calls `/api/v1/auth/reset-password` via proxy
- Success: redirect to `/login?resetSuccess=true`
- Error (expired/invalid): message with link back to login

## Email Content

- From: `noreply@margin-invest.com` (or Resend test domain before verification)
- Subject: "Reset your Margin Invest password"
- Body: brief message, reset link, "This link expires in 1 hour", "If you didn't request this, ignore this email."
- Plain text + simple HTML (no complex templates)

## Security

- **No email enumeration:** forgot-password always returns 200 regardless of account existence
- **Rate limiting:** max 3 unexpired tokens per user (skip sending if exceeded)
- **Token storage:** SHA256 hashed in DB, raw token only in email link
- **Single-use:** token consumed on successful reset
- **60-minute TTL:** expired tokens rejected
- **Password validation:** same rules as registration (12+ chars, complexity)
- **Post-reset cleanup:** clear lockout state, set `password_changed_at` to invalidate existing sessions
- **MFA unaffected:** reset doesn't modify MFA. User goes through normal MFA flow on next login.
