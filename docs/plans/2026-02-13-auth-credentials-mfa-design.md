# Auth.js Credentials + MFA Design

**Date:** 2026-02-13
**Status:** Approved

## Overview

Reconfigure Auth.js (NextAuth v5) to remove Microsoft and Facebook OAuth providers, add a CredentialsProvider for username/password login, and enforce mandatory MFA (TOTP + WebAuthn) for all credentials-based users. OAuth users (Google, GitHub) rely on their provider's own MFA.

## Providers

| Provider | Status | Notes |
|----------|--------|-------|
| Google | Keep | No changes |
| ~~Microsoft Entra ID~~ | Remove | Deleted entirely |
| ~~Facebook~~ | Remove | Deleted entirely |
| GitHub | Keep | No changes |
| Credentials | Add | Username + password, MFA-gated |

## Auth.js Callback Logic

### `signIn` Callback

| Condition | Auth Method | MFA Status | Result | Rationale |
|-----------|------------|------------|--------|-----------|
| OAuth login (Google/GitHub) | `oauth` | N/A | `true` (allow) | Provider handles its own MFA |
| Credentials + MFA verified | `credentials` | `verified` | `true` (allow) | Full auth complete |
| Credentials + MFA not configured | `credentials` | `not_configured` | Redirect to `/mfa/setup` | Block login, force MFA enrollment |
| Credentials + MFA configured but not verified | `credentials` | `configured` | Redirect to `/mfa/verify` | Block login, require TOTP/WebAuthn |

### `jwt` Callback

Custom claims added to the token:

- `authMethod`: `"oauth"` | `"credentials"`
- `mfaVerified`: `boolean`
- `userId`: `string`

### `session` Callback

Exposes `authMethod` and `mfaVerified` to client components.

### Security Property

No valid session exists for credentials users until MFA is completed. The `signIn` callback redirects before a session is ever created.

## Two-Phase Credentials Login Flow

```
/login (password) -> API verifies (Argon2id) -> signIn callback checks MFA
  -> /mfa/verify or /mfa/setup -> MFA valid -> session created -> /dashboard
```

**Step 1 (authorize):** Calls `POST /api/v1/auth/verify-credentials` on FastAPI backend. API validates password with Argon2id and returns user + MFA status (`not_configured` | `configured`). Invalid credentials return `null`.

**Step 2 (signIn callback):** Inspects MFA status. If unverified, returns redirect URL string (`/mfa/setup` or `/mfa/verify`). Auth.js treats string return as redirect with no session created.

**Step 3 (MFA page):** User enters TOTP code or authenticates with WebAuthn. On success, `POST /api/v1/auth/mfa/verify` returns a signed short-lived MFA token. Frontend calls `signIn("credentials", ...)` again with the MFA token appended. `signIn` callback sees `mfaVerified: true` and returns `true`.

Two-pass `signIn` is necessary because Auth.js CredentialsProvider does not support multi-step flows natively.

## API Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/api/v1/auth/register` | POST | Create user (Argon2id hash) | No |
| `/api/v1/auth/verify-credentials` | POST | Validate username + password, return user + MFA status | No |
| `/api/v1/auth/mfa/setup-totp` | POST | Generate TOTP secret + provisioning URI | Partial (password-verified token) |
| `/api/v1/auth/mfa/confirm-totp` | POST | Confirm TOTP setup with initial code | Partial |
| `/api/v1/auth/mfa/verify-totp` | POST | Validate TOTP code during login | Password-verified token |
| `/api/v1/auth/mfa/register-webauthn` | POST | Generate WebAuthn registration options | Partial |
| `/api/v1/auth/mfa/confirm-webauthn` | POST | Verify WebAuthn registration, store credential | Partial |
| `/api/v1/auth/mfa/authenticate-webauthn` | POST | Generate + verify WebAuthn authentication | Password-verified token |

## Database Models

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `users` | `id`, `username`, `email`, `password_hash`, `mfa_enabled`, `created_at` | Credential user accounts |
| `totp_secrets` | `id`, `user_id`, `encrypted_secret`, `confirmed`, `created_at` | TOTP secrets (Fernet-encrypted at rest) |
| `webauthn_credentials` | `id`, `user_id`, `credential_id`, `public_key`, `sign_count`, `created_at` | Registered passkeys/hardware keys |
| `mfa_challenge_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `used` | Short-lived tokens proving password verified |

## Security Details

- **Passwords:** Argon2id (memory=65536 KiB, iterations=3, parallelism=4) per OWASP recommendation
- **TOTP secrets:** Fernet symmetric encryption at rest (`MFA_ENCRYPTION_KEY` env var)
- **WebAuthn:** py_webauthn (server), @simplewebauthn/browser (client)
- **Challenge tokens:** SHA-256 hashed in DB, 5-minute TTL, single-use
- **Rate limiting:** 5 failed attempts per username per 15 minutes (lockout)
- **TOTP replay prevention:** Track last validated counter, reject codes at or below it
- **TOTP clock drift:** Validation window of 1 step (+/-30 seconds) per RFC 6238 Section 5

## Frontend Changes

### New Pages

| Route | Purpose |
|-------|---------|
| `/register` | Account creation (username, email, password with strength meter) |
| `/mfa/setup` | First-time MFA enrollment (TOTP QR + WebAuthn registration) |
| `/mfa/verify` | MFA challenge during login (TOTP input + WebAuthn button) |

### Modified Files

| File | Change |
|------|--------|
| `src/lib/auth.ts` | Remove Microsoft + Facebook, add CredentialsProvider, add callbacks |
| `src/app/login/login-buttons.tsx` | Remove Microsoft + Facebook buttons, add credentials form |
| `src/app/login/page.tsx` | Add divider between OAuth and credentials form |
| `src/components/settings/account-section.tsx` | MFA management for credentials users |

### New Client Libraries

- `@simplewebauthn/browser` for WebAuthn browser API
- `qrcode.react` for TOTP provisioning QR codes

## Error Handling

### Custom Error Classes

| Error Class | Code | Trigger |
|-------------|------|---------|
| `InvalidCredentials` | `invalid_credentials` | Wrong username or password |
| `AccountLocked` | `account_locked` | 5+ failed attempts in 15 minutes |
| `MfaRequired` | `mfa_required` | Password valid, MFA not yet verified |
| `MfaNotConfigured` | `mfa_not_configured` | Password valid, user hasn't enrolled MFA |

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Browser closed before MFA setup complete | Next login redirects to `/mfa/setup`, login blocked until done |
| TOTP secret generated but never confirmed | `confirmed=false`, regenerated on next attempt |
| WebAuthn registration abandoned | Challenge token expires (5 min), retry allowed |
| Both TOTP and WebAuthn configured | `/mfa/verify` shows both, user picks one |
| User removes all MFA methods | Blocked: at least one method must remain for credentials users |
| OAuth user visits `/mfa/setup` | Redirect to `/dashboard` |
| Brute force TOTP codes | Rate limited: 5 attempts per token per 5 minutes |
| TOTP code replay | Rejected via counter tracking |

## Testing Strategy

### API Tests (~48 tests)

- User registration (8): valid, duplicate, weak password, email validation
- Credential verification (6): correct/wrong password, nonexistent user, locked account
- TOTP setup (6): secret generation, URI format, confirm valid/invalid
- TOTP verification (8): valid, expired, replay, drift, rate limiting
- WebAuthn registration (6): options, valid/invalid attestation, duplicate
- WebAuthn authentication (5): valid/invalid assertion, sign count
- Challenge tokens (5): creation, expiry, single-use, hash verification
- Rate limiting (4): lockout, expiry, counter reset

### Web Tests (~31 tests)

- auth.ts config (6): 3 providers, credentials flow, callbacks
- Login page (5): 2 OAuth buttons, credentials form, validation
- Register page (5): form, password strength, submission, errors
- MFA setup page (6): QR code, TOTP confirmation, WebAuthn, method selection
- MFA verify page (5): TOTP input, WebAuthn, method switching, errors
- Settings MFA (4): enrolled methods, prevent removing last method

### Integration Tests

- Full TOTP flow: register -> setup TOTP -> logout -> login -> verify -> dashboard
- Full WebAuthn flow: register -> setup passkey -> logout -> login -> authenticate -> dashboard
- OAuth unchanged: Google/GitHub login works without MFA
