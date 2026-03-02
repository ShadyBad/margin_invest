# Account Page Redesign

## Overview

Redesign the Account page to elevate visual quality, improve usability, and achieve cohesion with the rest of the application. The page merges Account and Settings into a single destination. All existing functionality is preserved.

## Design Direction

Hybrid approach: Refined Minimal base (terminal-card, typography hierarchy, spacing system) with select premium elements (frosted pill nav, GSAP stagger animation, custom confirmation modals).

## Page Structure

Single scrolling page with four sections: Profile, Security, Billing, Preferences.

- Max-width: `max-w-4xl`, centered via AppShell
- Page heading: `heading-2` (36px, 700 weight)
- Entrance animation: GSAP staggered fade-in (translateY 16px → 0, 400ms, power2.out, 80ms stagger between sections). Below-fold sections use ScrollTrigger.

### Sticky Pill Navigation

Sticks below the main navbar on scroll. Uses `IntersectionObserver` to auto-highlight the current section. Clicking a pill smooth-scrolls to the target section.

- Container: `sticky top-16 z-10 backdrop-blur-lg bg-bg-primary/80 border-b border-border-subtle py-3`
- Pills: `text-sm font-medium px-4 py-1.5 rounded-full transition-colors`
- Active: `bg-accent/10 text-accent`
- Inactive: `text-text-secondary hover:text-text-primary`
- Mobile: horizontally scrollable, same frosted glass effect

Four pills: Profile, Security, Billing, Preferences.

## Profile Section

Card: `terminal-card p-6 md:p-8`.

Section header: `PROFILE` in `text-[10px] uppercase tracking-[0.2em] text-text-tertiary`.

Identity row layout:
- Avatar: 80px, using existing Avatar component (extend `lg` size)
- Name: `text-xl font-semibold text-text-primary`
- Email: `text-sm text-text-secondary`
- Provider pill: `px-2 py-0.5 text-xs rounded-full bg-bg-subtle border border-border-primary`
- Upload/remove actions: `text-sm text-accent hover:text-accent-hover transition-colors`, positioned below avatar
- Error state: `text-sm text-bearish`

Changes from current: larger avatar (80→80px), terminal-card styling, micro-label header, better vertical rhythm.

## Security Section

Card: `terminal-card p-6 md:p-8`.

Section header: `SECURITY` in `text-[10px] uppercase tracking-[0.2em] text-text-tertiary`.

Three sub-sections separated by `border-border-subtle` dividers.

### Connected Accounts

Sub-header: `text-base font-medium text-text-primary`.

Provider tiles: `terminal-card p-4 flex flex-col items-center gap-2` with min-width, laid out in `flex flex-wrap gap-3`.

- Connected: `border-accent/30`, emerald "Connected" text, "Disconnect" link in `text-bearish`
- Available: default border, "Connect" link in `text-accent`
- Coming soon: `opacity-40`, "Coming soon" label, no interaction

Five providers: Google, GitHub, Apple (soon), Amazon (soon), Facebook (soon).

### Password

Sub-header: `text-base font-medium text-text-primary`.

Status indicator: 2px dot (`w-2 h-2 rounded-full`) + status text.
- Has password: emerald dot, "Password set", relative time since last change
- No password: amber dot, descriptive text, "Set Password" button

Buttons: Primary accent for positive actions, bordered secondary for neutral, `text-bearish` for destructive.

Password forms: same fields as current, styled inside a subtle inner area (`max-w-md`), inputs with `border border-border-primary rounded-lg focus:border-accent`.

### Multi-Factor Authentication

Sub-header: `text-base font-medium text-text-primary`.

Status indicator with dot:
- Enabled: emerald dot with CSS pulse animation, "Enabled — Authenticator app"
- Not configured: amber dot (static), descriptive text, "Set Up MFA" link

Grace period warnings:
- Active grace: `bg-warning/5 border border-warning/30 rounded-lg p-4`
- Expired: `bg-bearish/5 border border-bearish/30 rounded-lg p-4`

Actions: "Regenerate Recovery Codes" (secondary), "Remove MFA" (text-bearish destructive).

### Confirmation Modal

New `ConfirmationModal` component replaces all `window.prompt()` calls. Used for: password removal, MFA disable, recovery code regeneration.

- Backdrop: `bg-black/50 backdrop-blur-sm`, click to close
- Dialog: `terminal-card max-w-sm mx-auto p-6`, centered vertically + horizontally
- Animation: slide-up (translateY 8px → 0, 200ms ease-out)
- Focus trap inside modal
- Escape key to close
- Title: `text-lg font-semibold`
- Input fields: same styling as password forms
- Buttons: Cancel (secondary) + Action (accent or destructive depending on context)

## Billing Section

Card: `terminal-card p-6 md:p-8`.

Section header: `BILLING` in `text-[10px] uppercase tracking-[0.2em] text-text-tertiary`.

### Paid User (Portfolio/Institutional)

Current plan in subtle inner card (`bg-bg-subtle/50 rounded-lg p-4`):
- Plan badge: existing styles (tier-specific color scheme)
- Status pill: existing styles (Active/Trialing/Past Due/Canceled)
- Renewal text: `text-sm text-text-secondary`
- "Manage subscription" button: secondary bordered, opens Stripe portal

### Free/Analyst User

Current plan card (same inner card styling), plus upgrade options:
- Each upgrade option: row with plan name (font-medium), brief value prop (text-sm text-secondary), upgrade button
- Upgrade buttons: `bg-accent text-bg-primary rounded-lg px-4 py-2 font-medium text-sm`
- Options separated by `border-border-subtle` divider

### Warning States

- Past due: amber alert card (`bg-warning/5 border-warning/30 rounded-lg p-4`)
- Loading: skeleton bars inside terminal-card

## Preferences Section

Card: `terminal-card p-6 md:p-8`.

Section header: `PREFERENCES` in `text-[10px] uppercase tracking-[0.2em] text-text-tertiary`.

Placeholder: "Product preferences coming soon." in `text-sm text-text-secondary`.

## Responsive Behavior

- Desktop (≥768px): `p-8` padding inside cards, full provider grid
- Mobile (<768px): `p-6` padding, pill nav horizontally scrollable, provider tiles wrap, password forms full width
- All sections stack vertically at all breakpoints

## Accessibility

- Focus-visible outlines on all interactive elements
- Modal focus trap with escape-to-close
- Semantic heading hierarchy (h1 → page title, h2 → section headers)
- Status indicators convey information via text, not just color (dot + text label)
- ARIA labels on icon-only buttons

## Files Affected

- `web/src/app/account/page.tsx` — restructure with pill nav, section refs, GSAP
- `web/src/components/account/profile-section.tsx` — terminal-card, larger avatar, micro-label
- `web/src/components/account/security-section.tsx` — terminal-card, dividers, modal integration
- `web/src/components/account/password-section.tsx` — styling updates, modal for remove
- `web/src/components/account/mfa-status.tsx` — pulse animation, modal integration
- `web/src/components/account/provider-icons.tsx` — terminal-card tiles
- `web/src/components/account/billing-section.tsx` — terminal-card, inner cards, upgrade layout
- `web/src/components/account/confirmation-modal.tsx` — new component
- `web/src/components/account/account-pill-nav.tsx` — new component
- `web/src/components/ui/avatar.tsx` — extend size to support 80px
- `web/src/app/settings/page.tsx` — redirect to /account or remove
- Tests: update existing tests, add tests for new components

## What's NOT Changing

- All API endpoints and data flows remain identical
- Session management logic unchanged
- OAuth connect/disconnect flows unchanged
- Password set/change/remove logic unchanged
- MFA setup/disable/regenerate logic unchanged
- Billing checkout and portal flows unchanged
- Recovery codes display component unchanged
