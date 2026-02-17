# Navigation Refactor Design

Date: 2026-02-17
Approach: Headless nav controller (`useNavigation()` hook) + render slot shell

## Problem

The current `FloatingNav` component is a single 200-line file that handles public links, app links, session state, mobile menu, avatar display, and sign out. There is no user dropdown, no footer, and Support/Settings live in the top nav. The component takes a `variant` prop ("public" | "app") that consuming pages must set manually.

## Approach

Separate navigation logic from rendering. A `useNavigation()` hook owns all auth-conditional logic and returns structured slot data. A `<Navbar />` shell renders three zones (left, center, right) from that data. Sub-components are pure presentational.

## Hook: `useNavigation()`

File: `src/hooks/use-navigation.ts`

Calls `useSession()` and `usePathname()`. Returns:

```ts
interface NavLink {
  href: string
  label: string
  isActive: boolean
}

interface UserDropdownItem {
  label: string
  href?: string
  onClick?: () => void
  type: "link" | "action" | "divider"
}

interface NavigationState {
  isAuthenticated: boolean
  links: NavLink[]
  cta: {
    primary: { label: string; href: string }
    secondary?: { label: string; href: string }
  } | null
  user: {
    name: string
    email: string
    avatarUrl?: string
    oauthAvatarUrl?: string
    dropdownItems: UserDropdownItem[]
  } | null
  logoHref: string
}
```

Unauthenticated state:
- `links`: Methodology, Guides
- `cta`: Login (primary), Sign Up (secondary)
- `user`: null

Authenticated state:
- `links`: Dashboard, Mainpage
- `cta`: null
- `user`: session data + dropdownItems (Account, Settings, divider, Sign Out)

## Navbar Shell

File: `src/components/nav/navbar.tsx`

Calls `useNavigation()` once, passes slot data to sub-components as props.

```
[Logo]     [Link] [Link] [Link]     [CTA / Avatar]
 left           center                    right
```

The floating pill visual is preserved exactly (fixed top-4, rounded-2xl, dark bg, shadow).

## File Structure

```
src/hooks/
  use-navigation.ts         # Headless nav controller

src/components/nav/
  navbar.tsx                 # Shell orchestrator
  nav-logo.tsx               # Logo SVG + link
  nav-links.tsx              # Center link list (desktop)
  nav-cta.tsx                # Login/Sign Up (unauthenticated right slot)
  user-dropdown.tsx          # Avatar + dropdown (authenticated right slot)
  mobile-menu.tsx            # Collapsed mobile view
  usage-pill.tsx             # Existing, unchanged
```

## UserDropdown

Triggered by avatar click. Dropdown contents driven by `dropdownItems` from the hook:

- Account (link to /account)
- Settings (link to /settings)
- Divider
- Sign Out (action, visually separated)

Behavior:
- Click avatar to toggle
- Close on outside click (useRef + useEffect)
- Close on Escape key
- Animate: fade + scale 95%->100% in (150ms ease-out), reverse out (100ms ease-in)
- Accessible: aria-expanded, role="menu", role="menuitem", arrow key navigation

No external library. Built with refs and local state.

## Footer

File: `src/components/layout/footer.tsx`

New component. Rendered in root `layout.tsx` — global, identical for all users.

Content: Support | Methodology | Legal | Copyright 2026

Design: single horizontal row, centered, text-text-tertiary, 12-13px, border-t border-border-subtle, py-6. Visually quiet. On mobile, wraps naturally.

No auth logic. Pure presentational.

## Integration

- Root `layout.tsx`: add `<Footer />` after `{children}`
- `AppShell`: replace `<FloatingNav variant="app" />` with `<Navbar />`
- Landing page: replace `<FloatingNav variant="public" />` with `<Navbar />`
- Methodology page: same replacement
- Route protection: unchanged (server-side `auth()` + `redirect("/login")` on /dashboard)

## Deletions

- `floating-nav.tsx` — replaced by new modular files
- `FloatingNavProps` interface with `variant` prop — gone
- Hardcoded `publicLinks` / `appLinks` arrays — moved into hook

## Unchanged

- `avatar.tsx` — used inside UserDropdown
- `usage-pill.tsx` — used inside Navbar (authenticated right slot)
- All auth config (lib/auth.ts, providers, MFA)
- All page content and route structure
- All styling tokens and design language
