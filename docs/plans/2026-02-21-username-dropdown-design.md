# Username in User Dropdown

**Date:** 2026-02-21
**Status:** Approved

## User Story

As an authenticated user, I want to see my username in the user dropdown menu (linked to my account page) so the header is cleaner without a separate "Account" button.

## Overview

Merge the "Account" button into the user menu by replacing the static "Account" label with the user's derived display name. The username row links to `/account` and sits above the divider and "Sign Out" action. No changes to the header bar itself — avatar-only trigger remains.

## Approach

Compute the display name in the `useNavigation` hook via a new `getDisplayName()` utility. The dropdown receives the derived name as a label — no logic in the view layer.

---

## Section 1: Username Derivation

### `getDisplayName(user)` utility — `web/src/lib/user.ts`

**Priority chain:**
1. `user.name` (if present and non-empty after trimming)
2. Email prefix (substring before `@`)
3. Fallback: `"User"`

**Email prefix extraction:**
- Input: `bpshay13@gmail.com` → Output: `bpshay13`
- Input: `@domain.com` → Fallback: `"User"`
- Input: `null` / `undefined` → Fallback: `"User"`

**Truncation:**
- Max 20 characters. Truncate with `…` if longer.
- Full value available via `title` attribute (hover tooltip).

---

## Section 2: Dropdown Structure

### Before

```
Account          → link to /account
────────
Sign Out         → action (red text)
```

### After

```
bpshay13         → link to /account (with title tooltip)
────────
Sign Out         → action (red text)
```

The username row uses the same styling as the current Account link: `text-[13px] text-text-secondary hover:text-text-primary`. No new CSS.

---

## Section 3: Navigation Hook Change

In `useNavigation` (`web/src/hooks/use-navigation.ts`):

- Import `getDisplayName` from `web/src/lib/user.ts`
- Replace hardcoded `"Account"` label with `getDisplayName(session.user)`
- Pass full (untrimmed) display name as a new `title` field on the dropdown item for tooltip

---

## Section 4: Dropdown Component Change

In `UserDropdown` (`web/src/components/nav/user-dropdown.tsx`):

- Add `title` attribute to link-type menu items (uses `item.title` if present, falls back to `item.label`)
- This enables the hover tooltip for truncated usernames

---

## Section 5: Mobile Menu

The mobile menu consumes the same `useNavigation` hook data. No separate changes needed — the username label propagates automatically.

---

## Section 6: Edge Cases

| Case | Behavior |
|------|----------|
| No email on session | Falls back to `"User"` |
| Email prefix empty (`@domain.com`) | Falls back to `"User"` |
| Long prefix (>20 chars) | Truncated with `…`, full value in `title` tooltip |
| `user.name` exists and non-empty | Uses `user.name` over email prefix |
| Unauthenticated | No dropdown rendered (existing behavior, unchanged) |

---

## Section 7: Files Changed

| File | Change |
|------|--------|
| `web/src/lib/user.ts` | **New** — `getDisplayName()` utility |
| `web/src/hooks/use-navigation.ts` | Use `getDisplayName` for dropdown label |
| `web/src/components/nav/user-dropdown.tsx` | Add `title` attr for tooltip on link items |
| `web/src/lib/__tests__/user.test.ts` | **New** — unit tests for `getDisplayName` |
| Existing dropdown tests | Update to expect username instead of `"Account"` |

---

## Section 8: Acceptance Criteria

**Given** an authenticated user with email `bpshay13@gmail.com`,
**When** they click the avatar in the header,
**Then** the dropdown shows `bpshay13` (linked to `/account`) above the divider and `Sign Out`.

**Given** an authenticated user with email `bpshay13@gmail.com`,
**When** they click the username row in the dropdown,
**Then** they navigate to `/account`.

**Given** an authenticated user with `user.name = "Brandon"`,
**When** they click the avatar,
**Then** the dropdown shows `Brandon` (not the email prefix).

**Given** an authenticated user with a 25-character email prefix,
**When** they view the dropdown,
**Then** the username is truncated to 20 chars with `…` and the full name appears on hover.

**Given** an unauthenticated visitor,
**When** they view the header,
**Then** no avatar, dropdown, or username is shown (sign-in/sign-up only).

**Given** a user on mobile,
**When** they open the mobile menu,
**Then** the username appears in place of "Account" with the same behavior.
