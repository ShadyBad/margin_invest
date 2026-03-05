# Header Alignment Fix — Center Search Overlay in Navbar

## Problem

The search overlay (`TickerSearch`) is hardcoded at `top-3` (12px from viewport top), but the navbar starts at `top-4` (16px). This positions the overlay 4px above the navbar's top edge, creating visible vertical misalignment when the search is open.

## Root Cause

The overlay uses a fixed `top-3` value that was an approximation rather than a calculated position based on the navbar's actual geometry.

## Fix

Calculate the correct `top` value from the navbar's known dimensions:

- Navbar top: `top-4` = 16px
- Border-top: 1px
- Padding-top (`py-3`): 12px
- Content band starts at: 29px
- Content height (icons `h-8`): ~32px
- Content vertical center: ~45px
- Search input height (`h-11`): 44px
- Overlay top for centering: 45 - 22 = **23px**

Replace `top-3` with `top-[23px]` on the search overlay div.

## Scope

- **1 file:** `web/src/components/nav/ticker-search.tsx`, line 102
- **1 class change:** `top-3` → `top-[23px]`
- No behavioral changes, no new dependencies
