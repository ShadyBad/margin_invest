# Account Security Section Design

**Date:** 2026-02-21
**Status:** Approved
**Scope:** Account page Security section, unified user model, MFA enforcement, recovery codes, provider linking

## Overview

Redesign the Account > Security section to handle authentication method display, MFA enforcement for password-based accounts, recovery codes, and bidirectional OAuth provider linking. Requires migrating from two user tables to a unified user model.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| User model | Unified single table | Clean foundation for bidirectional linking; avoids permanent dual-lookup complexity |
| Provider linking | Full bidirectional (OAuth <-> password) | Users can add/remove any auth method as long as one remains |
| MFA grace period | 72 hours, uniform across all tiers | Industry median (Stripe, GitHub, Atlassian); covers weekends; balances security with UX |
| Recovery codes | Full implementation (generate, store, redeem) | Required for responsible MFA enforcement |
| GitHub OAuth | Active (not placeholder) | Already implemented and working |

---

## 1. Unified User Model

### Current State

Two tables with overlapping fields:
- `users` — OAuth users (`oauth_id`, `provider`, `email`, `name`, `avatar_url`, `oauth_avatar_url`, stripe fields)
- `credential_users` — Password users (`username`, `email`, `password_hash`, `mfa_enabled`, lockout fields, stripe fields)

### Target State

**One `users` table**, all auth-method fields nullable:

```
users
├── id (int, PK)
├── email (str, unique, not null)
├── name (str, nullable)
├── password_hash (str, nullable)          -- null for OAuth-only users
├── mfa_enabled (bool, default false)
├── mfa_grace_deadline (datetime, nullable) -- set on account creation for credential users
├── failed_login_attempts (int, default 0)
├── locked_until (datetime, nullable)
├── last_totp_counter (int, nullable)
├── password_changed_at (datetime, nullable)
├── avatar_url (str, nullable)             -- user-uploaded
├── oauth_avatar_url (str, nullable)       -- from provider
├── stripe_customer_id (str, nullable)
├── stripe_subscription_id (str, nullable)
├── subscription_plan (str, default "analyst")
├── subscription_status (str, nullable)
├── current_period_end (datetime, nullable)
├── created_at (datetime)
├── updated_at (datetime)
```

**New `linked_providers` table:**

```
linked_providers
├── id (int, PK)
├── user_id (int, FK -> users.id)
├── provider (str, not null)       -- "google", "github", "apple", "amazon", "facebook"
├── oauth_id (str, not null)       -- provider's unique user ID
├── provider_email (str, nullable) -- email from provider (may differ from account email)
├── linked_at (datetime)
├── UNIQUE(provider, oauth_id)     -- one provider account links to one user
├── UNIQUE(user_id, provider)      -- one user can't link same provider twice
```

Existing tables stay unchanged: `totp_secrets`, `webauthn_credentials`, `mfa_challenge_tokens` — they already FK to a user ID; the migration repoints them to the unified `users` table.

### Migration Strategy

1. Create unified `users` table with new schema
2. Migrate all rows from current `users` (OAuth) into new `users`, creating `linked_providers` rows for their OAuth provider
3. Migrate all rows from `credential_users` into new `users`, mapping `username` to `email` (already the same value based on registration flow)
4. Repoint FKs from `totp_secrets`, `webauthn_credentials`, `mfa_challenge_tokens`, `api_keys`
5. Drop old `users` and `credential_users` tables

### Key Rule

A user has credentials if `password_hash IS NOT NULL`. A user has OAuth if they have at least one row in `linked_providers`. Both can be true simultaneously.

---

## 2. Security Section UI Layout + Copy

### Layout Structure

The Security section is a card within `/account` with four stacked subsections:

```
+-- Security --------------------------------------------------+
|                                                               |
|  Authentication Method                                        |
|  +-- provider icons row ------------------------------------+ |
|  | [G] Google  [GH] GitHub  [Ap] Apple  [Am] Amazon  [Fb]  | |
|  +----------------------------------------------------------+ |
|  (active = highlighted + "Connected", others greyed)          |
|                                                               |
|  -- divider --                                                |
|                                                               |
|  Password                                                     |
|  (credentials section -- varies by state)                     |
|                                                               |
|  -- divider --                                                |
|                                                               |
|  Multi-Factor Authentication                                  |
|  (MFA section -- varies by state)                             |
|                                                               |
+---------------------------------------------------------------+
```

### Provider Icons Row

Five provider icons displayed horizontally. Each icon is one of three states:

**Connected (user signed in with this provider):**
- Full-color icon, solid border
- Label: "Connected" in green text below
- No action button

**Available but not connected (Google, GitHub — provider works, user didn't sign in with it):**
- Full-color icon, dashed border
- Label: "Not connected" in muted text
- Button: "Connect" (secondary style)
- On click: initiates OAuth flow to link provider

**Unavailable (Apple, Amazon, Facebook — not yet implemented):**
- Greyed-out icon, `opacity-40`, no border
- Label: "Coming soon" in muted text
- No button, `cursor-not-allowed`
- Tooltip on hover: "{Provider} sign-in is not yet available."

### Copy Blocks -- Provider States

**OAuth-only user (no password set), viewing their connected provider:**

> Your account is secured by {Provider} OAuth. Password and MFA settings are managed through your {Provider} account.

Examples:
- "Your account is secured by Google OAuth. Password and MFA settings are managed through your Google account."
- "Your account is secured by GitHub OAuth. Password and MFA settings are managed through your GitHub account."

This copy appears directly below the provider icons row, attributed to the connected provider.

**OAuth user viewing a disconnected but available provider:** No per-provider copy block. The "Not connected" label and "Connect" button are self-explanatory.

**OAuth user viewing an unavailable provider:** No copy block. The "Coming soon" label and greyed icon are sufficient. Tooltip provides the detail.

### Password Subsection

**State A -- OAuth-only user, no password set:**

> You don't have a password on this account. Add one to sign in with your email and password as an alternative to {Provider}.

Button: "Set Password" (secondary)

On click: inline form -- New Password, Confirm Password, "Save Password" button. Same validation rules as registration (12+ chars, upper, lower, digit, special).

**State B -- User has password set:**

> Password last changed {relative_time}.

Button: "Change Password" (secondary)

On click: existing change-password form (current password, new password, confirm).

**State C -- Credential-only user, no OAuth linked:**

Same as State B, but the "secured by {Provider}" copy above the provider icons row is absent. The password section is the primary auth method display.

### MFA Subsection

**State 1 -- OAuth-only user, no password:**

> Multi-factor authentication is managed through your {Provider} account.

No action buttons. Muted text, informational only.

**State 2 -- User has password, MFA not enabled:**

Status: Yellow dot + "Not configured"

> Multi-factor authentication adds a second layer of verification when you sign in with your password. It's required for password-based accounts.

Button: "Set Up MFA" (primary/accent style)

If within grace period, additional line below in a subtle warning banner:

> You have {X days/hours} remaining to set up MFA. After that, access to sensitive account actions will be restricted.

**State 3 -- User has password, MFA enabled (TOTP):**

Status: Green dot + "Enabled -- Authenticator app"

> Your account is protected by an authenticator app.

Two buttons:
- "Regenerate Recovery Codes" (secondary)
- "Remove MFA" (destructive/red text, requires password confirmation)

**State 4 -- User has password, MFA enabled (WebAuthn, future):**

Status: Green dot + "Enabled -- Security key"

Same pattern as State 3 but with "Security key" label.

**State 5 -- User has both OAuth and password, MFA not enabled on password:**

Same as State 2 -- MFA is required for the password credential regardless of whether OAuth is also linked.

### Visual Specifications

- Section heading: "Security" -- `text-lg font-semibold text-text-primary`
- Subsection headings: "Authentication Method", "Password", "Multi-Factor Authentication" -- `text-sm font-medium text-text-secondary uppercase tracking-wide`
- Copy blocks: `text-sm text-text-secondary`, max-width constrained for readability
- Status dots: 8px circles, inline with status text
- Dividers: `border-border-primary`, subtle 1px
- All provider icons: 32x32px, consistent spacing (`gap-4`)

---

## 3. MFA Enforcement Policy

### Timeline

```
Account Creation          +24h                    +72h
      |                     |                       |
      v                     v                       v
  +--------+  +------------------+  +------------------------+
  | Prompt |  |  Soft Reminder   |  |  Hard Enforcement      |
  |        |  |                  |  |                        |
  | Setup  |  |  Banner persists |  |  Sensitive actions     |
  | screen |  |  on every page   |  |  blocked until MFA     |
  | shown  |  |  load            |  |  is configured         |
  +--------+  +------------------+  +------------------------+
```

**Phase 1 -- Prompt (0-24 hours)**

On first sign-in after account creation, the user is redirected to `/mfa/setup`. They can dismiss it once via a "Skip for now" link which returns them to the dashboard. After dismissal, a persistent but non-blocking top banner appears:

> Set up multi-factor authentication to secure your account. **Set up now ->**

The banner is dismissible per-session (reappears on next sign-in).

**Phase 2 -- Soft Reminder (24-72 hours)**

The top banner becomes non-dismissible. It stays visible on every page load:

> MFA is required for password accounts. You have {time remaining} to complete setup. **Set up now ->**

All features remain accessible. The banner uses a subtle warning style (amber left border, not red).

**Phase 3 -- Hard Enforcement (72+ hours)**

Sensitive actions are blocked. When a user attempts a sensitive action, they see a blocking modal:

> Multi-factor authentication is required to {action description}. Set up MFA to continue.

Button: "Set Up MFA" (primary, links to `/mfa/setup`)
Link: "Go back" (dismisses modal, returns to previous state)

The user can still access read-only features: view dashboard, view scores, browse methodology and guides.

### Sensitive Actions (Blocked After Grace Period)

| Action | Route/Endpoint |
|--------|---------------|
| Change email | `PUT /api/v1/users/me` |
| Change password | `POST /api/v1/auth/change-password` |
| Manage API keys (create/revoke) | `/api/v1/keys/*` |
| Billing changes (upgrade/downgrade/cancel) | `/api/v1/billing/*` |
| Export data | `/api/v1/export/*` |
| Delete account | `DELETE /api/v1/users/me` |
| Connect/disconnect OAuth provider | `/api/v1/auth/link-provider`, `/api/v1/auth/unlink-provider` |
| Remove MFA | `POST /api/v1/auth/mfa/disable` |

### Backend Enforcement

A middleware decorator `@require_mfa` applied to sensitive endpoints:

1. If user has no password (`password_hash IS NULL`): pass through (OAuth-only, MFA managed by provider)
2. If user has password and `mfa_enabled = True`: pass through
3. If user has password, `mfa_enabled = False`, and `mfa_grace_deadline > now()`: pass through (within grace period)
4. If user has password, `mfa_enabled = False`, and `mfa_grace_deadline <= now()`: return `403` with `{"error": "mfa_required", "message": "Multi-factor authentication must be enabled to perform this action."}`

The frontend checks for `error: "mfa_required"` in API responses and shows the blocking modal.

### `mfa_grace_deadline` Lifecycle

- **Set on account creation** (credential signup): `created_at + 72 hours`
- **Set when OAuth user adds a password**: `now() + 72 hours`
- **Cleared when MFA is enabled**: set to `NULL` (no longer relevant)
- **Re-set if MFA is removed**: `now() + 72 hours` (grace period restarts)

### Edge Cases

**Existing credential users (migration):** Users who already have accounts but no MFA get `mfa_grace_deadline = migration_timestamp + 72 hours`. They see the Phase 2 banner on their next sign-in.

**OAuth users:** Never see MFA enforcement. No banner, no grace period, no `@require_mfa` blocking.

**OAuth user adds a password:** Grace period starts at the moment they save their password.

**Credential user links OAuth, then removes password:** `mfa_grace_deadline` is cleared. MFA enforcement no longer applies.

**Account lockout interaction:** If a user is locked out (5 failed attempts, 15-minute cooldown) and their grace period expires while locked out, the grace deadline does not extend.

### Why 72 Hours?

| Grace Period | Pros | Cons |
|---|---|---|
| 24 hours | Fast enforcement, smaller attack window | Users in different timezones may miss it; feels aggressive |
| **72 hours (chosen)** | Covers a weekend; multiple sessions to set up; matches Stripe/GitHub/Atlassian | Slightly longer exposure window |
| 7 days | Very generous; minimal friction | Too long for unprotected password access |

---

## 4. Recovery Codes + Device Loss Flows

### Recovery Code Generation

**When generated:**
- At the end of MFA setup, after TOTP is confirmed (or WebAuthn registered, future)
- On demand via "Regenerate Recovery Codes" button in the Security section

**Format:** 8 single-use codes, 8 alphanumeric characters each, grouped in pairs:

```
abcd-ef12
gh34-jk56
mn78-pq90
rs12-tu34
vw56-xy78
ab90-cd12
ef34-gh56
jk78-mn90
```

Lowercase alphanumeric only. No ambiguous characters (0/O, 1/l/I). Hyphen is cosmetic -- user can enter with or without.

### Storage

Codes are hashed individually with bcrypt. Stored in a new `recovery_codes` table:

```
recovery_codes
├── id (int, PK)
├── user_id (int, FK -> users.id)
├── code_hash (str, not null)
├── used (bool, default false)
├── used_at (datetime, nullable)
├── created_at (datetime)
```

When codes are regenerated, all existing codes for that user are deleted and replaced.

### Display Flow

**Step 1 -- Generation screen (shown once, immediately after MFA confirmation):**

Heading: "Save your recovery codes"

> These codes can be used to sign in if you lose access to your authenticator app. Each code can only be used once. Store them somewhere safe.

Codes displayed in a monospace box with subtle background.

Two action buttons:
- "Copy to clipboard" (secondary)
- "Download as .txt" (secondary) -- downloads `margin-invest-recovery-codes.txt`

Checkbox (required to proceed): "I've saved these codes in a safe place"

Button: "Continue" (primary, disabled until checkbox checked)

**Step 2 -- Confirmation:**

User lands on the Security section of `/account` with success toast: "MFA is now enabled. Your account is protected."

### Recovery Code Redemption (Login Flow)

On `/mfa/verify`, below the TOTP input, add a link:

> Lost your authenticator? **Use a recovery code**

Clicking reveals a single text input:

Label: "Recovery code"
Placeholder: "xxxx-xxxx"
Button: "Verify"

Backend: `POST /api/v1/auth/mfa/verify-recovery`
- Iterates hashed codes for the user, bcrypt-checks each
- Match found and `used = false`: marks `used = true`, sets `used_at`, returns `mfa_token`
- No match or all used: returns `401`

After successful redemption, sign-in completes normally. On next page load, if 2 or fewer unused codes remain, show warning banner:

> You have {N} recovery code{s} remaining. **Regenerate codes ->**

### Regeneration

"Regenerate Recovery Codes" requires password confirmation (modal). On confirmation:

1. `POST /api/v1/auth/mfa/regenerate-recovery-codes`
2. All existing codes deleted
3. 8 new codes generated and returned (plaintext, one time only)
4. Same display flow as initial generation (copy, download, checkbox, continue)

### Device Loss Flow

**User loses phone and has recovery codes:** Use recovery code at login (self-service).

**User loses phone and recovery codes:** No self-service path. On `/mfa/verify`, below recovery code input:

> Lost your recovery codes too? **Contact support**

Links to `/support` with pre-filled subject: "MFA recovery -- lost authenticator and recovery codes".

Expectation-setting copy:

> Account recovery without MFA or recovery codes requires identity verification and may take 1-3 business days. For security, we cannot bypass MFA over email or chat.

**Admin reset endpoint (future, out of scope for this spec):**

`POST /api/v1/admin/users/{id}/reset-mfa` -- clears `mfa_enabled`, deletes `totp_secrets` and `recovery_codes`, sets `mfa_grace_deadline = now() + 72h`. Requires admin role, logged in audit trail.

### MFA Removal (Self-Service)

"Remove MFA" button in Security section (destructive style):

1. Password confirmation modal
2. TOTP code confirmation modal (must prove current authenticator access)
3. On confirm: `POST /api/v1/auth/mfa/disable`
   - Sets `mfa_enabled = false`
   - Deletes `totp_secrets` and `recovery_codes`
   - Sets `mfa_grace_deadline = now() + 72h`
4. Toast: "MFA has been removed. You have 72 hours to set it up again."

Requiring both password and TOTP to remove MFA prevents an attacker with only the password from disabling it.

---

## 5. Provider Linking Flows

### Connect an OAuth Provider

**Entry point:** "Connect" button next to an available but disconnected provider icon.

**Flow:**

1. User clicks "Connect" next to Google or GitHub
2. Confirmation modal: "Connect your {Provider} account? You'll be redirected to {Provider} to authorize access. This lets you sign in with either your password or {Provider}."
   - Buttons: "Connect {Provider}" (primary), "Cancel" (secondary)
3. Redirect to OAuth authorization flow (`/api/v1/auth/link-provider/{provider}`)
4. Provider consent screen
5. Callback returns to `/account`

**Backend: `POST /api/v1/auth/link-provider`**

- Receives OAuth callback with provider token
- Validates OAuth identity
- Checks: does `(provider, oauth_id)` already belong to another user? If yes, return `409`: "This {Provider} account is already linked to a different Margin Invest account. Sign in with that account to manage it."
- If clean: insert row into `linked_providers`, set `oauth_avatar_url` if available

**Success toast:** "{Provider} connected. You can now sign in with {Provider} or your password."

### Disconnect an OAuth Provider

**Entry point:** "Disconnect" button on a connected provider (destructive text style, not prominent).

**Guard rails -- disconnect is blocked when:**

- Only linked provider AND no password: button disabled, tooltip: "You can't disconnect your only sign-in method. Set a password first."
- Has password but MFA not enabled and grace period expired: button disabled, tooltip: "Set up MFA before disconnecting {Provider}. MFA is required for password-based accounts."

**Flow (when allowed):**

1. User clicks "Disconnect"
2. Confirmation modal: "Disconnect {Provider}? You won't be able to sign in with {Provider} anymore. You can reconnect it later."
   - If user has password: "You'll still be able to sign in with your email and password."
   - Buttons: "Disconnect" (destructive), "Cancel" (secondary)
3. `DELETE /api/v1/auth/unlink-provider/{provider}`
4. Toast: "{Provider} disconnected."

### Add a Password (OAuth-Only User)

**Entry point:** "Set Password" button in the Password subsection.

**Flow:**

1. User clicks "Set Password"
2. Inline form: New Password, Confirm Password (same validation as registration)
3. `POST /api/v1/auth/set-password`
4. Backend sets `password_hash`, sets `mfa_grace_deadline = now() + 72h`
5. Toast: "Password set. You can now sign in with your email and password."
6. MFA subsection updates to State 2 (not enabled, grace period active)

### Remove Password (User Has OAuth Linked)

**Entry point:** "Remove Password" in Password subsection (destructive text), shown only when user has at least one linked provider.

**Flow:**

1. User clicks "Remove Password"
2. Confirmation modal: "Remove your password? You'll only be able to sign in with your linked provider{s}. MFA settings for password sign-in will be cleared."
   - Buttons: "Remove Password" (destructive), "Cancel" (secondary)
3. `POST /api/v1/auth/remove-password` (requires current password in request body)
4. Backend: nulls `password_hash`, sets `mfa_enabled = false`, deletes `totp_secrets`, `recovery_codes`, clears `mfa_grace_deadline`
5. Toast: "Password removed. Sign in with {Provider} going forward."
6. Security section re-renders to OAuth-only state

### Login Flow Changes

**OAuth sign-in for user who also has password:** Signs in immediately via OAuth. No MFA challenge. Session `authMethod = "oauth"`, `mfaVerified = true`.

**Password sign-in for user who also has OAuth:** Standard credential flow. MFA challenge if `mfa_enabled = true`. Session `authMethod = "credentials"`, `mfaVerified` depends on MFA completion.

**Key principle:** MFA enforcement is per-authentication-method, not per-account.

### Edge Cases

**Duplicate email across providers:** User signs up with password using `user@gmail.com`, connects Google which returns same email. This is fine -- email matches, link proceeds. If Google returns a different email, store in `linked_providers.provider_email`. Account email unchanged.

**Provider revokes access:** Next sign-in via that provider fails. `linked_providers` row stays until user explicitly disconnects. Error message: "Sign-in with {Provider} failed. You may need to reauthorize access. If you have a password, you can sign in with your email instead."

**Race condition:** `UNIQUE(provider, oauth_id)` constraint handles two users trying to link the same provider account. Second attempt gets `409`.

---

## 6. Acceptance Criteria

### 6.1 -- Security Section Rendering

**AC-1: OAuth-only user sees correct provider state**
```
Given   a user signed in via Google OAuth with no password set
When    they visit /account
Then    the Security section shows:
        - Google icon highlighted with "Connected" label in green
        - GitHub icon with dashed border, "Not connected" label, and "Connect" button
        - Apple, Amazon, Facebook icons greyed out at 40% opacity with "Coming soon" labels
        - Copy: "Your account is secured by Google OAuth. Password and MFA settings
          are managed through your Google account."
        - Password subsection shows "Set Password" button
        - MFA subsection shows "Multi-factor authentication is managed through your
          Google account."
```

**AC-2: GitHub OAuth user sees correct provider state**
```
Given   a user signed in via GitHub OAuth with no password set
When    they visit /account
Then    the Security section shows:
        - GitHub icon highlighted with "Connected" label in green
        - Google icon with dashed border, "Not connected" label, and "Connect" button
        - Apple, Amazon, Facebook icons greyed out with "Coming soon" labels
        - Copy: "Your account is secured by GitHub OAuth. Password and MFA settings
          are managed through your GitHub account."
```

**AC-3: Credential user without MFA sees enforcement prompt**
```
Given   a user signed in with email and password
And     MFA is not enabled
And     the grace period has not expired
When    they visit /account
Then    the Security section shows:
        - No provider icons highlighted (all show "Not connected" or "Coming soon")
        - Password subsection shows "Change Password" button
        - MFA status: yellow dot, "Not configured"
        - Copy: "Multi-factor authentication adds a second layer of verification
          when you sign in with your password. It's required for password-based accounts."
        - "Set Up MFA" button in primary/accent style
        - Grace period banner with time remaining
```

**AC-4: Credential user with MFA enabled**
```
Given   a user signed in with email and password
And     MFA is enabled via TOTP
When    they visit /account
Then    the MFA subsection shows:
        - Green dot, "Enabled -- Authenticator app"
        - Copy: "Your account is protected by an authenticator app."
        - "Regenerate Recovery Codes" button (secondary)
        - "Remove MFA" button (destructive text style)
        - No grace period banner
```

**AC-5: User with both OAuth and password, MFA not enabled**
```
Given   a user with Google OAuth linked AND a password set
And     MFA is not enabled on the password credential
When    they visit /account
Then    Google shows "Connected"
And     MFA subsection shows State 2 (not configured, "Set Up MFA" button)
And     the "secured by Google OAuth" copy does NOT appear
```

### 6.2 -- MFA Enforcement Timeline

**AC-6: Phase 1 -- Prompt on first sign-in**
```
Given   a new credential user who just created an account
When    they complete their first sign-in
Then    they are redirected to /mfa/setup
And     a "Skip for now" link is visible
When    they click "Skip for now"
Then    they land on the dashboard with a dismissible top banner:
        "Set up multi-factor authentication to secure your account. Set up now ->"
```

**AC-7: Phase 2 -- Soft reminder (24-72h)**
```
Given   a credential user who skipped MFA setup
And     more than 24 hours have passed since account creation
When    they sign in
Then    a non-dismissible amber banner appears on every page:
        "MFA is required for password accounts. You have {time remaining} to
        complete setup. Set up now ->"
And     all features remain accessible
```

**AC-8: Phase 3 -- Hard enforcement (72h+)**
```
Given   a credential user with MFA not enabled
And     mfa_grace_deadline has passed
When    they attempt to change their email
Then    a blocking modal appears:
        "Multi-factor authentication is required to change your email.
        Set up MFA to continue."
And     the modal has a "Set Up MFA" button and a "Go back" link
And     the email change does not proceed
```

**AC-9: Sensitive actions all blocked after grace period**
```
Given   a credential user whose grace period has expired and MFA is not enabled
When    they attempt any of: change email, change password, create/revoke API key,
        billing change, export data, delete account, connect/disconnect provider,
        remove MFA
Then    the backend returns 403 with {"error": "mfa_required"}
And     the frontend shows the blocking modal
```

**AC-10: Read-only access preserved after enforcement**
```
Given   a credential user whose grace period has expired and MFA is not enabled
When    they visit /dashboard, /methodology, /guides, or /backtesting
Then    pages load normally with no blocking modal
```

### 6.3 -- Recovery Codes

**AC-11: Codes generated at MFA setup**
```
Given   a user completing TOTP setup on /mfa/setup
When    they enter a valid TOTP code and click "Verify & Enable"
Then    they see "Save your recovery codes" with 8 codes in xxxx-xxxx format
And     "Copy to clipboard" and "Download as .txt" buttons are visible
And     a checkbox "I've saved these codes in a safe place" is visible
And     "Continue" is disabled until the checkbox is checked
```

**AC-12: Recovery code redemption at login**
```
Given   a credential user with MFA enabled and unused recovery codes
When    they are on /mfa/verify and click "Use a recovery code"
Then    a single text input appears with placeholder "xxxx-xxxx"
When    they enter a valid unused code and click "Verify"
Then    the code is marked used in the database
And     sign-in completes successfully
And     the code cannot be reused
```

**AC-13: Low recovery code warning**
```
Given   a user who just signed in using a recovery code
And     they have 2 or fewer unused codes remaining
When    the next page loads
Then    a warning banner appears:
        "You have {N} recovery code{s} remaining. Regenerate codes ->"
```

**AC-14: Regeneration requires password**
```
Given   a user clicks "Regenerate Recovery Codes" in the Security section
When    the confirmation modal appears
Then    it requires their current password
When    they enter a valid password
Then    all existing codes are deleted
And     8 new codes are displayed with copy/download/checkbox flow
```

### 6.4 -- Provider Linking

**AC-15: Connect a provider**
```
Given   a credential user on /account
When    they click "Connect" next to Google
Then    a confirmation modal appears
When    they confirm and complete Google OAuth
Then    Google icon changes to "Connected" with green label
And     a toast shows: "Google connected. You can now sign in with Google or your password."
And     a row is inserted into linked_providers
```

**AC-16: Disconnect blocked when only auth method**
```
Given   an OAuth-only user with Google connected and no password
When    they view the Google provider icon
Then    "Disconnect" is disabled with tooltip:
        "You can't disconnect your only sign-in method. Set a password first."
```

**AC-17: Disconnect blocked without MFA after grace**
```
Given   a user with Google linked and a password set
And     MFA is not enabled and grace period has expired
When    they try to disconnect Google
Then    the button is disabled with tooltip:
        "Set up MFA before disconnecting Google. MFA is required for
        password-based accounts."
```

**AC-18: Add password to OAuth account triggers MFA grace**
```
Given   an OAuth-only user
When    they set a password via the Security section
Then    mfa_grace_deadline is set to now() + 72 hours
And     MFA subsection updates to show "Not configured" with "Set Up MFA" button
And     the grace period banner appears
```

**AC-19: Remove password clears MFA state**
```
Given   a user with both Google linked and a password with MFA enabled
When    they click "Remove Password" and confirm with their current password
Then    password_hash is set to null
And     mfa_enabled is set to false
And     totp_secrets and recovery_codes are deleted
And     MFA subsection shows "Multi-factor authentication is managed through
        your Google account."
```

**AC-20: Duplicate provider linking rejected**
```
Given   user A has linked their Google account (oauth_id: "abc123")
When    user B tries to connect the same Google account
Then    the backend returns 409
And     an error toast shows:
        "This Google account is already linked to a different Margin Invest account."
```

### 6.5 -- MFA Removal

**AC-21: Remove MFA requires password + TOTP**
```
Given   a user with MFA enabled clicks "Remove MFA"
Then    they must enter their current password
And     they must enter a valid TOTP code
When    both are verified
Then    mfa_enabled is set to false, totp_secrets and recovery_codes deleted
And     mfa_grace_deadline is set to now() + 72 hours
And     toast: "MFA has been removed. You have 72 hours to set it up again."
```

### 6.6 -- Accessibility

**AC-22: Provider icons are accessible**
```
Given   a screen reader user navigating the provider icons row
Then    each icon has aria-label: "{Provider} -- {Connected|Not connected|Coming soon}"
And     disabled icons have aria-disabled="true"
And     "Connect" buttons have aria-label: "Connect {Provider} account"
And     focus order follows visual left-to-right order
```

**AC-23: MFA status is accessible**
```
Given   a screen reader user navigating the MFA subsection
Then    the status dot has aria-label: "MFA status: {Enabled|Not configured}"
And     the status uses role="status" for live updates
And     the grace period banner has role="alert"
```

**AC-24: Color contrast meets WCAG AA**
```
Given   the Security section rendered in the dark theme
Then    all text meets WCAG AA contrast ratio (4.5:1 body, 3:1 large text)
And     green/yellow/red indicators meet contrast against bg-elevated (#141B2D)
And     greyed-out icons at 40% opacity are supplemented by text labels
```

### 6.7 -- Migration

**AC-25: Existing users migrated correctly**
```
Given   the unified user table migration runs
Then    all OAuth users exist in new users table with password_hash = null
And     each has a linked_providers row for their OAuth provider
And     all credential users exist with password_hash preserved
And     mfa_enabled, totp_secrets, webauthn_credentials preserved
And     existing credential users without MFA have
        mfa_grace_deadline = migration_time + 72 hours
And     no data is lost (row counts match pre/post migration)
```
