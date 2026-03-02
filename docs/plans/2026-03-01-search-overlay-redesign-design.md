# Search Ticker Overlay Redesign

## Objective

Replace the always-visible ticker search input in the navbar with a magnifying glass icon that opens an overlay search dialog. Reduces visual clutter while maintaining full usability.

## Interaction Flow

**Default state:** A 32×32px magnifying glass icon button in the navbar right section, styled identically to ThemeToggle.

**Open triggers:**
- Click the magnifying glass icon
- `Cmd+K` (Mac) / `Ctrl+K` (Windows) from anywhere on the page

**Open state:** A centered overlay appears:
- Semi-transparent backdrop (`bg-black/20`) covers the viewport
- Search input field (~400px wide, capped at `calc(100vw - 48px)`) floats centered, aligned with the navbar vertical position (~`top-3`)
- Magnifying glass as a leading inline icon inside the input
- Entry animation: scale from 95% + fade in, 200ms with `--ease-out-expo`
- Input auto-focuses immediately

**Close triggers:**
1. `Escape` key
2. Click the backdrop
3. Submit a valid ticker (navigates, then closes)
4. Blur when input is empty

**Close animation:** Fade out + scale to 95%, 150ms.

## Visual Design

### Icon Button (collapsed)

- 32×32px, `rounded-lg`
- Inline SVG magnifying glass: 16×16, `strokeWidth={1.5}`, `stroke="currentColor"`
- Colors: `text-text-secondary`, hover `text-text-primary` + `bg-bg-subtle`
- Focus ring: `ring-2 ring-accent ring-offset-2 ring-offset-bg-primary`
- Optional `⌘K` kbd hint: `text-[10px]`, `text-text-tertiary`, `bg-white/[0.06]`, `rounded`, `px-1`

### Overlay

- Backdrop: fixed, full viewport, `bg-black/20`, `aria-hidden="true"`
- Search container: `bg-bg-elevated`, `border border-border-subtle`, `rounded-xl`, `shadow-[0_4px_24px_rgba(0,0,0,0.2)]`
- Positioned: fixed, horizontally centered, `top-3`
- Width: `min(400px, calc(100vw - 48px))`
- Height: 44px
- Leading icon: magnifying glass, 16×16, `text-text-tertiary`
- Input: `text-sm`, `text-text-primary`, `placeholder-text-tertiary`, `pl-10 pr-4`
- Placeholder: "Search any ticker..."

## Keyboard & Accessibility

- `Cmd+K` / `Ctrl+K`: global shortcut to open
- `Escape`: close and return focus to icon button
- `Enter`: submit ticker and navigate
- Icon button: `aria-label="Search ticker"`, `aria-haspopup="dialog"`, `aria-expanded={isOpen}`
- Overlay: `role="dialog"`, `aria-label="Ticker search"`, `aria-modal="true"`
- Input: `aria-label="Ticker symbol"`
- Backdrop: `aria-hidden="true"`
- Focus returns to icon button on Escape close

## Component Architecture

### Files Changed

- `web/src/components/nav/ticker-search.tsx` — rewritten with icon button + overlay
- `web/src/components/nav/__tests__/ticker-search.test.tsx` — updated for new interaction model
- `web/src/components/nav/navbar.tsx` — no changes needed
- `web/src/components/nav/mobile-menu.tsx` — no changes

### State

- `isOpen: boolean` — overlay visibility
- `query: string` — input value
- `buttonRef: RefObject<HTMLButtonElement>` — focus return target
- `inputRef: RefObject<HTMLInputElement>` — auto-focus target

### Event Handling

- Click icon → `setIsOpen(true)`
- Backdrop click → close, return focus
- Escape → close, return focus
- Blur on empty input → close (with `requestAnimationFrame` delay)
- Submit → navigate, clear, close

### Animation

- CSS transitions: `opacity` + `scale` via Tailwind, `duration-200`, `--ease-out-expo`
- Conditional render with brief exit animation

### Responsive

- Desktop: icon button in navbar, overlay on click/shortcut
- Mobile: search stays in mobile menu only (no changes to mobile-menu.tsx)

### Dependencies

None added. All inline SVG, all Tailwind.
