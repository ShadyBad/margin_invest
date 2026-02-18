# Navigation Auth Behavior Refactor

Date: 2026-02-17
Approach: Modify `useNavigation()` hook data + minimal component adjustments (Approach 1)

## Problem

The current navigation shows "Login" and "Sign Up" buttons for unauthenticated users, plus center links ("Methodology", "Guides") that shouldn't be visible to everyone. The desired behavior is a single "Dashboard" button that smartly routes based on auth state.

## Requirements

**Unauthenticated users:**
- No "Login" or "Sign Up" buttons
- No center nav links (empty)
- Single "Dashboard" button on the right → links to `/login`
- After login, redirect to `/dashboard`

**Authenticated users:**
- "Guides" as center nav link
- "Dashboard" button on the right (same styling as unauth) → links to `/dashboard`
- UsagePill + UserDropdown remain beside Dashboard button
- No re-authentication prompts

**Both states:**
- Methodology removed from nav entirely (accessible only from landing page CTA)
- No auth loops
- Existing UI styling preserved

## Design

### Hook: `useNavigation()` changes

File: `web/src/hooks/use-navigation.ts`

**Links arrays:**
- `PUBLIC_LINKS` → `[]` (empty)
- `APP_LINKS` → `[{ href: "/guides", label: "Guides" }]`

**CTA field (now set for both states):**
- Unauthenticated: `{ primary: { label: "Dashboard", href: "/login" } }` (no secondary)
- Authenticated: `{ primary: { label: "Dashboard", href: "/dashboard" } }`

The `cta` field is no longer null for authenticated users. This is the key change — it becomes a universal Dashboard button with auth-conditional href.

### Navbar changes

File: `web/src/components/nav/navbar.tsx`

Right-side rendering changes from either/or to additive:

```
Before:  {auth} → UsagePill + UserDropdown  |  {unauth} → NavCTA
After:   NavCTA always + {auth} → UsagePill + UserDropdown
```

`nav.cta` is always truthy, so NavCTA renders unconditionally. Authenticated users additionally see UsagePill and UserDropdown.

### Mobile menu changes

File: `web/src/components/nav/mobile-menu.tsx`

Bottom section changes from either/or to additive:

```
Before:  {auth} → user section  |  {unauth} → cta section
After:   cta always + {auth} → user section below
```

Dashboard button renders for both states. Authenticated users see it followed by their user info and dropdown items.

### No changes needed

- `nav-cta.tsx` — already handles primary-only (secondary is optional)
- `nav-links.tsx` — renders whatever links array it receives
- `nav-logo.tsx`, `user-dropdown.tsx`, `usage-pill.tsx` — unchanged
- Login page — `callbackUrl: "/dashboard"` already wired
- No middleware needed
- No new files

## Files Modified

1. `web/src/hooks/use-navigation.ts` — link arrays, cta logic for both states
2. `web/src/components/nav/navbar.tsx` — right-side rendering order
3. `web/src/components/nav/mobile-menu.tsx` — render cta + user together

## Edge Cases

- **Session loading**: During `useSession()` loading, shows unauth Dashboard button (→ `/login`). Flips to `/dashboard` once session resolves. Same button label, harmless.
- **OAuth redirect**: Login page already sets `callbackUrl: "/dashboard"` for credentials. OAuth flows use NextAuth default redirect behavior.
- **No auth loops**: Dashboard server component redirects to `/login` if no session. Login doesn't redirect authenticated users away (separate concern).
