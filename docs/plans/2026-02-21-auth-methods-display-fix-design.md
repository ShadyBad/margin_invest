# Fix Auth Methods Display on Account Settings

**Date:** 2026-02-21

## Problem

Authentication methods on the account settings page always show "Not connected" even when the user is connected via an OAuth provider (e.g., Google OIDC). The `linked_providers` database table is empty despite active OAuth users.

## Root Causes

1. **No data backfill in migration** — Migration `7dbb737440b5` (Feb 21) added the `linked_providers` table and dropped the old `users.provider` column, but never populated `linked_providers` for existing OAuth users. The table is empty.

2. **OAuth session never refreshes** — `auth.ts:173` only refreshes security-status for credentials users (`token.authMethod === "credentials"`). OAuth users get `linkedProviders` set once during initial sign-in and never again.

3. **No session refresh on account page** — The SecuritySection component reads `session.linkedProviders` but never triggers a session refresh, so stale JWT data persists.

## Design

### 1. JWT Callback — Refresh Security Status for All Users

**File:** `web/src/lib/auth.ts`

Restructure the JWT callback's token-refresh branch (the `else` block when `user` is falsy) to refresh security-status for ALL users, not just credentials users.

**Before:**
```
if (user) { /* initial sign-in */ }
else if (token.authMethod === "credentials" && token.userId) {
  // password-change check + security-status refresh
}
```

**After:**
```
if (user) { /* initial sign-in — unchanged */ }
else if (token.userId) {
  // Throttled to every 60s:
  //   1. Credentials-only: password-change invalidation check
  //   2. ALL users: security-status refresh
}
```

The password-change check remains credentials-only. The security-status refresh moves outside that conditional to cover all auth methods.

### 2. Session Refresh on Account Page Mount

**File:** `web/src/components/account/security-section.tsx`

Add a `useEffect` that calls NextAuth's `update()` on component mount. This triggers the JWT callback server-side, fetching fresh security-status data. The 60-second throttle in the JWT callback prevents excessive API calls.

### 3. Alembic Data Migration — Backfill LinkedProviders

**New file:** `api/alembic/versions/<hash>_backfill_linked_providers.py`

Insert `linked_providers` rows for existing OAuth-only users:
- Target: users where `oauth_id IS NOT NULL` and no corresponding `linked_providers` row exists
- Set `provider = 'google'` (only configured OAuth provider with existing users)
- Use the user's `oauth_id` from the `users` table as a placeholder; will be updated with the real provider account ID on next login via `oauth-sync`

## What We're NOT Changing

- **oauth-sync endpoint** — Already correctly creates LinkedProvider on each login
- **security-status endpoint** — Already correctly queries linked_providers
- **provider-icons.tsx** — Display logic is correct; just needs the right data
