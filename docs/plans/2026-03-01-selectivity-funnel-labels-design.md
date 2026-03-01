# Selectivity Funnel Label Visibility Design

**Date**: 2026-03-01
**Component**: `web/src/components/landing/proof-selectivity-funnel.tsx`

## Problem

The System Selectivity funnel renders labels inside horizontal bars. When a bar represents a small percentage of the universe (e.g., 12 out of 3,200 = 0.4%), the bar is clamped to a 4% minimum width, and the label text is truncated by the `truncate` CSS class. Users cannot read labels for the bottom funnel stages.

## Solution: External Labels with Hover Tooltip

### Label Positioning

- **Threshold**: 25% bar width
- **Wide bars (>= 25%)**: Labels render inside the bar (current behavior)
- **Narrow bars (< 25%)**: Labels render outside, to the right of the bar on the same row

Layout for narrow bars:
```
[==bar==] left-label                    right-label
```

Layout for wide bars (unchanged):
```
[====== left-label =================== right-label ======]
```

Implementation: Each row is a `flex` container. The colored bar is one flex child (`width: widthPct%`). When labels are external, they are sibling elements in the remaining flex space. The `truncate` class is not applied to external labels.

### Hover Tooltip

All bars (not just narrow ones) show a tooltip on hover with:

1. **Stage name** (e.g., "Exceptional candidates")
2. **Count** (e.g., "12")
3. **Percentage of universe** (e.g., "0.4%")
4. **Percentage of previous stage** (e.g., "25.5% of High+Exceptional")

Implementation: `hoveredIndex` state. Absolute-positioned div above the hovered bar. Uses `terminal-card` styling. On mobile, appears on tap, dismisses on tap-away. Quick `opacity` + `translateY` transition (150ms).

### Animation

- Existing bar grow animation unchanged (width: 0 → full, 0.5s, staggered 100ms)
- External labels fade in (`opacity: 0 → 1`) after the bar animation completes (delay = bar duration)
- Tooltip uses 150ms `opacity` + `translateY(-4px)` pop-in

### Testing Updates

Update `proof-selectivity-funnel.test.tsx`:

1. Wide bar renders labels inside the bar element
2. Narrow bar renders labels outside (sibling to) the bar element
3. Hover triggers tooltip with all four data points
4. External labels do not have the `truncate` class

Existing mock data (`universe=3200, exceptional=12`) naturally produces both wide and narrow bars.

## Alternatives Considered

**B: Tooltip-only for small values** — Condensed label inside + full detail on hover. Rejected: requires interaction to read basic data.

**C: Separate legend** — No text in bars; data table below. Rejected: loses the immediacy of reading directly from the chart.
