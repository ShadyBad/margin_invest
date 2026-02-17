# Fluid Intelligence Landing Page Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current retro/hacker landing page with a premium "Fluid Intelligence" visual system featuring a WebGL fluid shader hero, CSS glass surfaces, horizontal chapter navigation, and portfolio-driven DNA personalization.

**Architecture:** Four-chapter landing page (vertical + horizontal scroll hybrid). WebGL contained to hero only. DNA personalization via CSS custom properties injected from API data. Glass surface design system tokens propagate to future pages.

**Tech Stack:** React Three Fiber + GLSL (hero shader), Framer Motion (scroll/reveal animations), CSS scroll-snap (horizontal chapters), Next.js 16 App Router, FastAPI (DNA endpoint), Tailwind CSS v4 @theme tokens.

---

## Task 1: Evolve Design System Tokens

**Files:**
- Modify: `web/src/styles/tokens.ts`
- Modify: `web/src/app/globals.css`
- Test: `web/src/styles/__tests__/tokens.test.ts`

**Step 1: Write token structure test**

Create `web/src/styles/__tests__/tokens.test.ts`:

```typescript
import { describe, it, expect } from "vitest"
import { colors, fonts, spacing, motion, glass } from "../tokens"

describe("design tokens", () => {
  it("exports evolved color palette with new depth tokens", () => {
    expect(colors.dark.bgDeep).toBe("#0F0D0B")
    expect(colors.dark.warmUnder).toBe("#2A1F14")
    expect(colors.dark.caustic).toBe("rgba(237, 233, 227, 0.12)")
    expect(colors.dark.accentGlow).toBe("rgba(14, 79, 58, 0.15)")
    expect(colors.light.bgSurface).toBe("#F7F4EE")
  })

  it("exports motion tokens with easing curves and durations", () => {
    expect(motion.easeOutExpo).toBe("cubic-bezier(0.16, 1, 0.3, 1)")
    expect(motion.easeInOutSmooth).toBe("cubic-bezier(0.45, 0, 0.55, 1)")
    expect(motion.easeOutBack).toBe("cubic-bezier(0.22, 1, 0.36, 1)")
    expect(motion.durationMicro).toBe("150ms")
    expect(motion.durationReveal).toBe("600ms")
    expect(motion.durationTransition).toBe("1000ms")
    expect(motion.staggerBase).toBe("80ms")
  })

  it("exports glass surface tokens", () => {
    expect(glass.blur).toBe("40px")
    expect(glass.saturation).toBe("1.2")
    expect(glass.borderOpacity).toBe("0.08")
    expect(glass.elevatedBlur).toBe("60px")
  })

  it("preserves existing semantic colors", () => {
    expect(colors.dark.bullish).toBeDefined()
    expect(colors.dark.bearish).toBeDefined()
    expect(colors.light.accent).toBe("#0E4F3A")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/styles/__tests__/tokens.test.ts`
Expected: FAIL — `motion` and `glass` not exported, new color keys missing.

**Step 3: Update tokens.ts with evolved palette + motion + glass tokens**

Modify `web/src/styles/tokens.ts`. Add to the existing `colors` object:

```typescript
export const colors = {
  light: {
    bgPrimary: "#F4F3EF",
    bgSurface: "#F7F4EE",
    bgElevated: "#FFFFFF",
    bgSubtle: "#ECEAE4",
    textPrimary: "#121212",
    textSecondary: "#4A4A4A",
    textTertiary: "#8A8A86",
    accent: "#0E4F3A",
    accentHover: "#0B3E2E",
    accentGlow: "rgba(14, 79, 58, 0.15)",
    warmUnder: "#3A3228",
    caustic: "rgba(18, 18, 18, 0.08)",
    borderPrimary: "#D8D6D0",
    borderSubtle: "rgba(18, 18, 18, 0.04)",
    danger: "#C74B50",
    warning: "#B8860B",
    bullish: "#0E4F3A",
    bearish: "#C74B50",
    gridLine: "rgba(18, 18, 18, 0.04)",
    divider: "rgba(18, 18, 18, 0.06)",
  },
  dark: {
    bgPrimary: "#110F0D",
    bgDeep: "#0F0D0B",
    bgSurface: "#1A1814",
    bgElevated: "#221F1A",
    bgSubtle: "#1A1D24",
    textPrimary: "#EDE9E3",
    textSecondary: "#A5A5A3",
    textTertiary: "#6B6B68",
    accent: "#1C7A5A",
    accentHover: "#1F8F6A",
    accentGlow: "rgba(14, 79, 58, 0.15)",
    warmUnder: "#2A1F14",
    caustic: "rgba(237, 233, 227, 0.12)",
    borderPrimary: "#2A2621",
    borderSubtle: "rgba(255, 255, 255, 0.04)",
    danger: "#D45A5F",
    warning: "#D4A843",
    bullish: "#1A7A5A",
    bearish: "#D45A5F",
    gridLine: "rgba(255, 255, 255, 0.04)",
    divider: "rgba(255, 255, 255, 0.06)",
  },
} as const

export const motion = {
  easeOutExpo: "cubic-bezier(0.16, 1, 0.3, 1)",
  easeInOutSmooth: "cubic-bezier(0.45, 0, 0.55, 1)",
  easeOutBack: "cubic-bezier(0.22, 1, 0.36, 1)",
  durationMicro: "150ms",
  durationReveal: "600ms",
  durationTransition: "1000ms",
  durationAmbient: "10000ms",
  staggerBase: "80ms",
} as const

export const glass = {
  blur: "40px",
  saturation: "1.2",
  borderOpacity: "0.08",
  borderRadius: "16px",
  elevatedBlur: "60px",
  elevatedSaturation: "1.3",
} as const
```

Keep existing `fonts` and `spacing` exports unchanged.

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/styles/__tests__/tokens.test.ts`
Expected: PASS

**Step 5: Update globals.css with new CSS custom properties**

Modify `web/src/app/globals.css`. Update the `@theme` block to add new tokens:

```css
/* Add inside @theme {} block */
--color-bg-deep: #F4F3EF;
--color-bg-surface: #F7F4EE;
--color-accent-glow: rgba(14, 79, 58, 0.15);
--color-warm-under: #3A3228;
--color-caustic: rgba(18, 18, 18, 0.08);

/* Motion tokens */
--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out-smooth: cubic-bezier(0.45, 0, 0.55, 1);
--ease-out-back: cubic-bezier(0.22, 1, 0.36, 1);
--duration-micro: 150ms;
--duration-reveal: 600ms;
--duration-transition: 1000ms;
--duration-ambient: calc(10000ms * var(--dna-tempo, 1));
--stagger-base: 80ms;

/* DNA slots (populated by JS, defaults to empty) */
--dna-base: ;
--dna-mid: ;
--dna-accent: ;
--dna-density: 0.5;
--dna-tempo: 1;
```

Add dark mode overrides in the `.dark` class:

```css
--color-bg-deep: #0F0D0B;
--color-bg-surface: #1A1814;
--color-accent-glow: rgba(14, 79, 58, 0.15);
--color-warm-under: #2A1F14;
--color-caustic: rgba(237, 233, 227, 0.12);
```

Add glass utility classes after the existing styles:

```css
.glass {
  background: rgba(var(--color-bg-surface-rgb, 26, 24, 20), 0.6);
  backdrop-filter: blur(40px) saturate(1.2);
  -webkit-backdrop-filter: blur(40px) saturate(1.2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.glass-elevated {
  background: rgba(var(--color-bg-surface-rgb, 26, 24, 20), 0.75);
  backdrop-filter: blur(60px) saturate(1.3);
  -webkit-backdrop-filter: blur(60px) saturate(1.3);
  border: 1px solid var(--color-accent-glow);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.gradient-mesh {
  background:
    radial-gradient(ellipse at 20% 30%, var(--dna-base, var(--color-warm-under)) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 70%, var(--dna-mid, var(--color-accent)) 0%, transparent 50%),
    var(--color-bg-deep);
  opacity: 0.06;
}
```

**Step 6: Commit**

```bash
git add web/src/styles/tokens.ts web/src/styles/__tests__/tokens.test.ts web/src/app/globals.css
git commit -m "feat(web): evolve design system with motion, glass, and depth tokens"
```

---

## Task 2: DNA Computation Library (Engine-Side)

**Files:**
- Create: `web/src/lib/dna.ts`
- Test: `web/src/lib/__tests__/dna.test.ts`

This is a pure computation module — no API calls. Takes sector weights and portfolio stats, outputs visual DNA variables.

**Step 1: Write failing tests**

Create `web/src/lib/__tests__/dna.test.ts`:

```typescript
import { describe, it, expect } from "vitest"
import {
  computeDNA,
  blendSectorColors,
  SECTOR_COLORS,
  type DNAInput,
  type DNAOutput,
} from "../dna"

describe("SECTOR_COLORS", () => {
  it("maps all 11 GICS sectors to hex colors", () => {
    expect(Object.keys(SECTOR_COLORS)).toHaveLength(11)
    expect(SECTOR_COLORS["Information Technology"]).toBe("#1A3A5C")
    expect(SECTOR_COLORS["Energy"]).toBe("#4A3018")
    expect(SECTOR_COLORS["Health Care"]).toBe("#0E4F4F")
  })
})

describe("blendSectorColors", () => {
  it("returns single sector color when portfolio is concentrated", () => {
    const result = blendSectorColors({ "Information Technology": 1.0 })
    expect(result.base).toBe("#1A3A5C")
  })

  it("blends two sectors by weight", () => {
    const result = blendSectorColors({
      "Information Technology": 0.5,
      "Energy": 0.5,
    })
    // Midpoint between #1A3A5C and #4A3018 = #323A3A approximately
    expect(result.base).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.mid).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.accent).toMatch(/^#[0-9a-f]{6}$/i)
  })

  it("returns default palette for empty input", () => {
    const result = blendSectorColors({})
    expect(result.base).toBe("#0F0D0B")
    expect(result.mid).toBe("#1A5A3E")
    expect(result.accent).toBe("#1A7A5A")
  })
})

describe("computeDNA", () => {
  it("computes full DNA output from portfolio data", () => {
    const input: DNAInput = {
      sectorWeights: { "Information Technology": 0.6, "Health Care": 0.4 },
      tickerCount: 8,
      avgBeta: 1.1,
    }
    const result: DNAOutput = computeDNA(input)
    expect(result.base).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.mid).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.accent).toMatch(/^#[0-9a-f]{6}$/i)
    expect(result.density).toBeGreaterThanOrEqual(0)
    expect(result.density).toBeLessThanOrEqual(1)
    expect(result.tempo).toBeGreaterThanOrEqual(0.5)
    expect(result.tempo).toBeLessThanOrEqual(1.5)
  })

  it("maps low ticker count to low density", () => {
    const result = computeDNA({
      sectorWeights: { "Energy": 1.0 },
      tickerCount: 2,
      avgBeta: 1.0,
    })
    expect(result.density).toBeLessThan(0.3)
  })

  it("maps high beta to faster tempo", () => {
    const result = computeDNA({
      sectorWeights: { "Information Technology": 1.0 },
      tickerCount: 10,
      avgBeta: 1.8,
    })
    expect(result.tempo).toBeGreaterThan(1.0)
  })

  it("maps low beta to slower tempo", () => {
    const result = computeDNA({
      sectorWeights: { "Utilities": 1.0 },
      tickerCount: 10,
      avgBeta: 0.5,
    })
    expect(result.tempo).toBeLessThan(1.0)
  })

  it("returns defaults for empty portfolio", () => {
    const result = computeDNA({
      sectorWeights: {},
      tickerCount: 0,
      avgBeta: 1.0,
    })
    expect(result.base).toBe("#0F0D0B")
    expect(result.density).toBe(0)
    expect(result.tempo).toBe(1.0)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/lib/__tests__/dna.test.ts`
Expected: FAIL — module not found.

**Step 3: Implement DNA computation**

Create `web/src/lib/dna.ts`:

```typescript
export const SECTOR_COLORS: Record<string, string> = {
  "Information Technology": "#1A3A5C",
  "Health Care": "#0E4F4F",
  "Financials": "#0F1E3A",
  "Energy": "#4A3018",
  "Consumer Discretionary": "#5C2A2A",
  "Industrials": "#2A2E33",
  "Materials": "#3A2A14",
  "Utilities": "#2A3A2A",
  "Real Estate": "#3A3228",
  "Communication Services": "#2A1E4A",
  "Consumer Staples": "#4A4038",
}

const DEFAULT_PALETTE = { base: "#0F0D0B", mid: "#1A5A3E", accent: "#1A7A5A" }

export interface DNAInput {
  sectorWeights: Record<string, number>
  tickerCount: number
  avgBeta: number
}

export interface DNAOutput {
  base: string
  mid: string
  accent: string
  density: number
  tempo: number
}

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("")}`
}

function blendColors(colors: { hex: string; weight: number }[]): string {
  if (colors.length === 0) return DEFAULT_PALETTE.base
  let r = 0, g = 0, b = 0
  for (const { hex, weight } of colors) {
    const [cr, cg, cb] = hexToRgb(hex)
    r += cr * weight
    g += cg * weight
    b += cb * weight
  }
  return rgbToHex(r, g, b)
}

export function blendSectorColors(
  sectorWeights: Record<string, number>,
): { base: string; mid: string; accent: string } {
  const entries = Object.entries(sectorWeights).filter(
    ([sector]) => sector in SECTOR_COLORS,
  )
  if (entries.length === 0) return DEFAULT_PALETTE

  const total = entries.reduce((sum, [, w]) => sum + w, 0)
  if (total === 0) return DEFAULT_PALETTE

  const weighted = entries.map(([sector, w]) => ({
    hex: SECTOR_COLORS[sector],
    weight: w / total,
  }))

  const base = blendColors(weighted)

  // Mid: lighten the blend by mixing with emerald
  const [br, bg, bb] = hexToRgb(base)
  const mid = rgbToHex(
    br * 0.5 + 0x1a * 0.5,
    bg * 0.5 + 0x5a * 0.5,
    bb * 0.5 + 0x3e * 0.5,
  )

  // Accent: lighten further
  const accent = rgbToHex(
    br * 0.3 + 0x1a * 0.7,
    bg * 0.3 + 0x7a * 0.7,
    bb * 0.3 + 0x5a * 0.7,
  )

  return { base, mid, accent }
}

export function computeDNA(input: DNAInput): DNAOutput {
  const { sectorWeights, tickerCount, avgBeta } = input
  const palette = blendSectorColors(sectorWeights)

  // Density: 0-1 from ticker count (0 tickers = 0, 30+ = 1)
  const density = Math.min(1, Math.max(0, tickerCount / 30))

  // Tempo: 0.5-1.5 from avg beta (beta 0.5 = tempo 0.7, beta 1.5 = tempo 1.3)
  const tempo = Math.min(1.5, Math.max(0.5, 0.4 + avgBeta * 0.6))

  return { ...palette, density, tempo }
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/lib/__tests__/dna.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/lib/dna.ts web/src/lib/__tests__/dna.test.ts
git commit -m "feat(web): add DNA computation library for portfolio-driven personalization"
```

---

## Task 3: DNA API Endpoint (Backend)

**Files:**
- Create: `api/src/margin_api/schemas/dna.py`
- Create: `api/src/margin_api/routes/dna.py`
- Modify: `api/src/margin_api/app.py` (register router)
- Test: `api/tests/routes/test_dna.py`

**Step 1: Write failing test**

Create `api/tests/routes/test_dna.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport

from margin_api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_dna_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/users/me/dna")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_dna_returns_defaults_for_user_with_no_scores(client: AsyncClient):
    response = await client.get(
        "/api/v1/users/me/dna",
        headers={"X-User-Id": "1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "base" in data
    assert "mid" in data
    assert "accent" in data
    assert "density" in data
    assert "tempo" in data
    assert isinstance(data["density"], (int, float))
    assert isinstance(data["tempo"], (int, float))


@pytest.mark.anyio
async def test_dna_response_has_valid_hex_colors(client: AsyncClient):
    response = await client.get(
        "/api/v1/users/me/dna",
        headers={"X-User-Id": "1"},
    )
    data = response.json()
    import re
    hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    assert hex_pattern.match(data["base"])
    assert hex_pattern.match(data["mid"])
    assert hex_pattern.match(data["accent"])
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/routes/test_dna.py -v`
Expected: FAIL — route not registered.

**Step 3: Create schema**

Create `api/src/margin_api/schemas/dna.py`:

```python
from pydantic import BaseModel, Field


class DNAResponse(BaseModel):
    """Visual DNA parameters derived from user portfolio composition."""

    base: str = Field(description="Deepest background hex color")
    mid: str = Field(description="Mid-layer gradient hex color")
    accent: str = Field(description="Highlight/caustic tint hex color")
    density: float = Field(ge=0, le=1, description="Visual density 0-1")
    tempo: float = Field(ge=0.5, le=1.5, description="Animation speed multiplier")
```

**Step 4: Create route**

Create `api/src/margin_api/routes/dna.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.database import get_db
from margin_api.db.models import Score, Asset
from margin_api.deps import get_current_user_id
from margin_api.schemas.dna import DNAResponse

router = APIRouter(prefix="/api/v1/users/me", tags=["dna"])

SECTOR_COLORS = {
    "Information Technology": "#1A3A5C",
    "Health Care": "#0E4F4F",
    "Financials": "#0F1E3A",
    "Energy": "#4A3018",
    "Consumer Discretionary": "#5C2A2A",
    "Industrials": "#2A2E33",
    "Materials": "#3A2A14",
    "Utilities": "#2A3A2A",
    "Real Estate": "#3A3228",
    "Communication Services": "#2A1E4A",
    "Consumer Staples": "#4A4038",
}

DEFAULT_DNA = DNAResponse(
    base="#0F0D0B", mid="#1A5A3E", accent="#1A7A5A", density=0.5, tempo=1.0
)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    n = int(hex_color[1:], 16)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _blend_colors(colors: list[tuple[str, float]]) -> str:
    r, g, b = 0.0, 0.0, 0.0
    for hex_color, weight in colors:
        cr, cg, cb = _hex_to_rgb(hex_color)
        r += cr * weight
        g += cg * weight
        b += cb * weight
    return _rgb_to_hex(r, g, b)


def compute_dna(
    sector_weights: dict[str, float], ticker_count: int, avg_beta: float
) -> DNAResponse:
    entries = [
        (sector, w)
        for sector, w in sector_weights.items()
        if sector in SECTOR_COLORS
    ]
    if not entries:
        return DEFAULT_DNA

    total = sum(w for _, w in entries)
    if total == 0:
        return DEFAULT_DNA

    weighted = [(SECTOR_COLORS[s], w / total) for s, w in entries]
    base = _blend_colors(weighted)

    br, bg, bb = _hex_to_rgb(base)
    mid = _rgb_to_hex(br * 0.5 + 0x1A * 0.5, bg * 0.5 + 0x5A * 0.5, bb * 0.5 + 0x3E * 0.5)
    accent = _rgb_to_hex(br * 0.3 + 0x1A * 0.7, bg * 0.3 + 0x7A * 0.7, bb * 0.3 + 0x5A * 0.7)

    density = min(1.0, max(0.0, ticker_count / 30))
    tempo = min(1.5, max(0.5, 0.4 + avg_beta * 0.6))

    return DNAResponse(base=base, mid=mid, accent=accent, density=density, tempo=tempo)


@router.get("/dna", response_model=DNAResponse)
async def get_user_dna(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DNAResponse:
    """Compute visual DNA from user's scored ticker portfolio."""
    # Get sector distribution from user's scored assets
    stmt = (
        select(Asset.sector, func.count(Asset.id))
        .join(Score, Score.asset_id == Asset.id)
        .group_by(Asset.sector)
    )
    result = await db.execute(stmt)
    sector_counts = dict(result.all())

    if not sector_counts:
        return DEFAULT_DNA

    total = sum(sector_counts.values())
    sector_weights = {s: c / total for s, c in sector_counts.items()}
    ticker_count = total

    # avg_beta defaults to 1.0 (we don't store beta in DB yet)
    return compute_dna(sector_weights, ticker_count, avg_beta=1.0)
```

**Step 5: Register router in app.py**

Find the router registration section in `api/src/margin_api/app.py` and add:

```python
from margin_api.routes.dna import router as dna_router
app.include_router(dna_router)
```

**Step 6: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/routes/test_dna.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add api/src/margin_api/schemas/dna.py api/src/margin_api/routes/dna.py api/src/margin_api/app.py api/tests/routes/test_dna.py
git commit -m "feat(api): add DNA endpoint computing visual params from portfolio sectors"
```

---

## Task 4: DNA Frontend Proxy Route + Provider

**Files:**
- Create: `web/src/app/api/v1/users/me/dna/route.ts`
- Create: `web/src/components/landing/dna-provider.tsx`
- Test: `web/src/app/api/v1/users/me/dna/__tests__/route.test.ts`
- Test: `web/src/components/landing/__tests__/dna-provider.test.tsx`

**Step 1: Write proxy route test**

Create `web/src/app/api/v1/users/me/dna/__tests__/route.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"

vi.mock("@/lib/auth", () => ({
  auth: vi.fn(),
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { GET } from "../route"
import { auth } from "@/lib/auth"

describe("GET /api/v1/users/me/dna", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns 401 when not authenticated", async () => {
    vi.mocked(auth).mockResolvedValue(null)
    const response = await GET()
    expect(response.status).toBe(401)
  })

  it("proxies DNA data from upstream API", async () => {
    vi.mocked(auth).mockResolvedValue({
      userId: "1",
      user: { email: "test@test.com" },
    } as any)
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          base: "#1A3A5C",
          mid: "#0E4F4F",
          accent: "#1A7A5A",
          density: 0.6,
          tempo: 0.85,
        }),
    })
    const response = await GET()
    expect(response.status).toBe(200)
    const data = await response.json()
    expect(data.base).toBe("#1A3A5C")
    expect(data.density).toBe(0.6)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/app/api/v1/users/me/dna/__tests__/route.test.ts`
Expected: FAIL — route file doesn't exist.

**Step 3: Create proxy route**

Create `web/src/app/api/v1/users/me/dna/route.ts`:

```typescript
import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET() {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  try {
    const response = await fetch(`${API_URL}/api/v1/users/me/dna`, {
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      next: { revalidate: 3600 }, // Cache for 1 hour
    })

    if (!response.ok) {
      const text = await response.text().catch(() => "Upstream error")
      return NextResponse.json({ error: text }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    // Fallback: return defaults if API is down
    return NextResponse.json({
      base: "#0F0D0B",
      mid: "#1A5A3E",
      accent: "#1A7A5A",
      density: 0.5,
      tempo: 1.0,
    })
  }
}
```

**Step 4: Run proxy test**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/app/api/v1/users/me/dna/__tests__/route.test.ts`
Expected: PASS

**Step 5: Write DNA provider test**

Create `web/src/components/landing/__tests__/dna-provider.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"
import { DNAProvider } from "../dna-provider"

describe("DNAProvider", () => {
  it("renders children", () => {
    const { getByText } = render(
      <DNAProvider>
        <div>child content</div>
      </DNAProvider>,
    )
    expect(getByText("child content")).toBeDefined()
  })

  it("injects CSS custom properties on document element when dna prop provided", () => {
    render(
      <DNAProvider
        dna={{
          base: "#1A3A5C",
          mid: "#0E4F4F",
          accent: "#1A7A5A",
          density: 0.6,
          tempo: 0.85,
        }}
      >
        <div>content</div>
      </DNAProvider>,
    )
    const style = document.documentElement.style
    expect(style.getPropertyValue("--dna-base")).toBe("#1A3A5C")
    expect(style.getPropertyValue("--dna-mid")).toBe("#0E4F4F")
    expect(style.getPropertyValue("--dna-accent")).toBe("#1A7A5A")
    expect(style.getPropertyValue("--dna-density")).toBe("0.6")
    expect(style.getPropertyValue("--dna-tempo")).toBe("0.85")
  })

  it("renders without dna prop (unauthenticated)", () => {
    const { getByText } = render(
      <DNAProvider>
        <div>no dna</div>
      </DNAProvider>,
    )
    expect(getByText("no dna")).toBeDefined()
  })
})
```

**Step 6: Run provider test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/dna-provider.test.tsx`
Expected: FAIL — module not found.

**Step 7: Implement DNA provider**

Create `web/src/components/landing/dna-provider.tsx`:

```typescript
"use client"

import { useEffect, type ReactNode } from "react"

export interface DNAValues {
  base: string
  mid: string
  accent: string
  density: number
  tempo: number
}

interface DNAProviderProps {
  dna?: DNAValues | null
  children: ReactNode
}

export function DNAProvider({ dna, children }: DNAProviderProps) {
  useEffect(() => {
    if (!dna) return

    const root = document.documentElement
    root.style.setProperty("--dna-base", dna.base)
    root.style.setProperty("--dna-mid", dna.mid)
    root.style.setProperty("--dna-accent", dna.accent)
    root.style.setProperty("--dna-density", String(dna.density))
    root.style.setProperty("--dna-tempo", String(dna.tempo))

    return () => {
      root.style.removeProperty("--dna-base")
      root.style.removeProperty("--dna-mid")
      root.style.removeProperty("--dna-accent")
      root.style.removeProperty("--dna-density")
      root.style.removeProperty("--dna-tempo")
    }
  }, [dna])

  return <>{children}</>
}
```

**Step 8: Run provider test**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/dna-provider.test.tsx`
Expected: PASS

**Step 9: Commit**

```bash
git add web/src/app/api/v1/users/me/dna/ web/src/components/landing/dna-provider.tsx web/src/components/landing/__tests__/dna-provider.test.tsx
git commit -m "feat(web): add DNA proxy route and CSS variable injection provider"
```

---

## Task 5: Glass Surface UI Component

**Files:**
- Create: `web/src/components/ui/glass-surface.tsx`
- Test: `web/src/components/ui/__tests__/glass-surface.test.tsx`
- Modify: `web/src/components/ui/index.ts` (add export)

**Step 1: Write failing test**

Create `web/src/components/ui/__tests__/glass-surface.test.tsx`:

```typescript
import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { GlassSurface } from "../glass-surface"

describe("GlassSurface", () => {
  it("renders children", () => {
    const { getByText } = render(
      <GlassSurface>Hello</GlassSurface>,
    )
    expect(getByText("Hello")).toBeDefined()
  })

  it("applies glass class by default", () => {
    const { container } = render(
      <GlassSurface>Content</GlassSurface>,
    )
    expect(container.firstElementChild?.classList.contains("glass")).toBe(true)
  })

  it("applies glass-elevated when elevated prop is true", () => {
    const { container } = render(
      <GlassSurface elevated>Content</GlassSurface>,
    )
    expect(container.firstElementChild?.classList.contains("glass-elevated")).toBe(true)
  })

  it("merges custom className", () => {
    const { container } = render(
      <GlassSurface className="p-4">Content</GlassSurface>,
    )
    const el = container.firstElementChild
    expect(el?.classList.contains("glass")).toBe(true)
    expect(el?.classList.contains("p-4")).toBe(true)
  })

  it("renders as specified element via as prop", () => {
    const { container } = render(
      <GlassSurface as="section">Content</GlassSurface>,
    )
    expect(container.firstElementChild?.tagName).toBe("SECTION")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/ui/__tests__/glass-surface.test.tsx`
Expected: FAIL

**Step 3: Implement GlassSurface**

Create `web/src/components/ui/glass-surface.tsx`:

```typescript
import { type ElementType, type HTMLAttributes, type ReactNode } from "react"

interface GlassSurfaceProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode
  elevated?: boolean
  as?: ElementType
}

export function GlassSurface({
  children,
  elevated = false,
  as: Component = "div",
  className = "",
  ...props
}: GlassSurfaceProps) {
  const baseClass = elevated ? "glass-elevated" : "glass"
  return (
    <Component className={`${baseClass} ${className}`.trim()} {...props}>
      {children}
    </Component>
  )
}
```

**Step 4: Run test**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/ui/__tests__/glass-surface.test.tsx`
Expected: PASS

**Step 5: Add to barrel export**

Add to `web/src/components/ui/index.ts`:

```typescript
export { GlassSurface } from "./glass-surface"
```

**Step 6: Commit**

```bash
git add web/src/components/ui/glass-surface.tsx web/src/components/ui/__tests__/glass-surface.test.tsx web/src/components/ui/index.ts
git commit -m "feat(web): add GlassSurface reusable UI primitive"
```

---

## Task 6: Horizontal Scroll Container

**Files:**
- Create: `web/src/components/landing/horizontal-scroll.tsx`
- Test: `web/src/components/landing/__tests__/horizontal-scroll.test.tsx`

**Step 1: Write failing test**

Create `web/src/components/landing/__tests__/horizontal-scroll.test.tsx`:

```typescript
import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { HorizontalScroll } from "../horizontal-scroll"

describe("HorizontalScroll", () => {
  it("renders panels as children", () => {
    const { getByText } = render(
      <HorizontalScroll>
        <div>Panel 1</div>
        <div>Panel 2</div>
      </HorizontalScroll>,
    )
    expect(getByText("Panel 1")).toBeDefined()
    expect(getByText("Panel 2")).toBeDefined()
  })

  it("applies scroll-snap styles to container", () => {
    const { container } = render(
      <HorizontalScroll>
        <div>Panel</div>
      </HorizontalScroll>,
    )
    const scroller = container.querySelector("[data-horizontal-scroll]")
    expect(scroller).toBeDefined()
  })

  it("wraps children in snap-aligned flex items", () => {
    const { container } = render(
      <HorizontalScroll>
        <div>A</div>
        <div>B</div>
        <div>C</div>
      </HorizontalScroll>,
    )
    const panels = container.querySelectorAll("[data-scroll-panel]")
    expect(panels).toHaveLength(3)
  })

  it("renders progress indicator", () => {
    const { container } = render(
      <HorizontalScroll>
        <div>A</div>
        <div>B</div>
      </HorizontalScroll>,
    )
    const indicator = container.querySelector("[data-scroll-progress]")
    expect(indicator).toBeDefined()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/horizontal-scroll.test.tsx`
Expected: FAIL

**Step 3: Implement horizontal scroll container**

Create `web/src/components/landing/horizontal-scroll.tsx`:

```typescript
"use client"

import { Children, useRef, useState, useEffect, type ReactNode } from "react"

interface HorizontalScrollProps {
  children: ReactNode
  className?: string
}

export function HorizontalScroll({ children, className = "" }: HorizontalScrollProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [progress, setProgress] = useState(0)
  const childArray = Children.toArray(children)
  const count = childArray.length

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return

    const handleScroll = () => {
      const maxScroll = el.scrollWidth - el.clientWidth
      if (maxScroll > 0) {
        setProgress(el.scrollLeft / maxScroll)
      }
    }

    el.addEventListener("scroll", handleScroll, { passive: true })
    return () => el.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <section className={`relative h-screen ${className}`}>
      <div
        ref={scrollRef}
        data-horizontal-scroll
        className="flex h-full overflow-x-auto overflow-y-hidden snap-x snap-mandatory"
        style={{ scrollbarWidth: "none" }}
      >
        {childArray.map((child, i) => (
          <div
            key={i}
            data-scroll-panel
            className="w-screen h-full flex-shrink-0 snap-center"
          >
            {child}
          </div>
        ))}
      </div>
      {/* Progress indicator */}
      <div
        data-scroll-progress
        className="absolute bottom-8 left-1/2 -translate-x-1/2 h-0.5 rounded-full overflow-hidden"
        style={{ width: `${count * 24}px`, backgroundColor: "var(--color-border-subtle)" }}
      >
        <div
          className="h-full rounded-full transition-transform duration-150"
          style={{
            width: `${100 / count}%`,
            backgroundColor: "var(--color-accent)",
            transform: `translateX(${progress * (count - 1) * 100}%)`,
          }}
        />
      </div>
    </section>
  )
}
```

**Step 4: Run test**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/horizontal-scroll.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/horizontal-scroll.tsx web/src/components/landing/__tests__/horizontal-scroll.test.tsx
git commit -m "feat(web): add HorizontalScroll container with CSS snap and progress indicator"
```

---

## Task 7: Fluid Shader (Hero WebGL)

**Files:**
- Create: `web/src/components/landing/fluid-shader.tsx`
- Test: `web/src/components/landing/__tests__/fluid-shader.test.tsx`

This is the WebGL hero component. It renders a full-screen quad with a GLSL fragment shader. Testing is limited to render/mount behavior (WebGL internals can't be unit-tested in jsdom).

**Step 1: Write failing test**

Create `web/src/components/landing/__tests__/fluid-shader.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"

// Mock Three.js / R3F — jsdom can't do WebGL
vi.mock("@react-three/fiber", () => ({
  Canvas: ({ children }: any) => <div data-testid="r3f-canvas">{children}</div>,
  useFrame: vi.fn(),
  useThree: () => ({ size: { width: 1920, height: 1080 } }),
}))

vi.mock("three", () => ({
  ShaderMaterial: vi.fn(),
  PlaneGeometry: vi.fn(),
  Vector2: vi.fn().mockImplementation(() => ({ x: 0, y: 0 })),
  Vector3: vi.fn().mockImplementation(() => ({ x: 0, y: 0, z: 0 })),
  Color: vi.fn().mockImplementation(() => ({ r: 0, g: 0, b: 0 })),
}))

import { FluidShader } from "../fluid-shader"

describe("FluidShader", () => {
  it("renders without crashing", () => {
    const { getByTestId } = render(<FluidShader />)
    expect(getByTestId("r3f-canvas")).toBeDefined()
  })

  it("accepts DNA color props", () => {
    const { getByTestId } = render(
      <FluidShader
        baseColor="#1A3A5C"
        midColor="#0E4F4F"
        accentColor="#1A7A5A"
        tempo={0.85}
        density={0.6}
      />,
    )
    expect(getByTestId("r3f-canvas")).toBeDefined()
  })

  it("accepts scrollProgress prop", () => {
    const { getByTestId } = render(
      <FluidShader scrollProgress={0.5} />
    )
    expect(getByTestId("r3f-canvas")).toBeDefined()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/fluid-shader.test.tsx`
Expected: FAIL

**Step 3: Implement FluidShader**

Create `web/src/components/landing/fluid-shader.tsx`:

```typescript
"use client"

import { useRef, useMemo } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { Color, ShaderMaterial, Vector2 } from "three"

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`

const fragmentShader = `
  precision highp float;

  uniform float uTime;
  uniform float uScrollProgress;
  uniform float uTempo;
  uniform float uDensity;
  uniform vec3 uBaseColor;
  uniform vec3 uMidColor;
  uniform vec3 uAccentColor;
  uniform vec2 uResolution;
  uniform vec2 uMouse;

  varying vec2 vUv;

  // Simplex 3D noise
  vec4 permute(vec4 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod(i, 289.0);
    vec4 p = permute(permute(permute(
      i.z + vec4(0.0, i1.z, i2.z, 1.0))
      + i.y + vec4(0.0, i1.y, i2.y, 1.0))
      + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 1.0/7.0;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
  }

  void main() {
    vec2 uv = vUv;
    float aspect = uResolution.x / uResolution.y;
    vec2 st = vec2(uv.x * aspect, uv.y);

    // Mouse parallax (subtle)
    vec2 mouseOffset = (uMouse - 0.5) * 0.05;
    st += mouseOffset;

    float time = uTime * uTempo * 0.08;

    // Layer 1: Large slow movement
    float n1 = snoise(vec3(st * 1.5, time * 0.5)) * 0.5 + 0.5;

    // Layer 2: Medium detail
    float n2 = snoise(vec3(st * 3.0 + 100.0, time * 0.7)) * 0.5 + 0.5;

    // Layer 3: Fine detail (density-controlled)
    float n3 = snoise(vec3(st * 6.0 + 200.0, time)) * 0.5 + 0.5;
    float detailMix = uDensity * 0.3;

    // Blend noise layers
    float noise = n1 * 0.5 + n2 * 0.3 + n3 * detailMix;

    // Color gradient
    vec3 color = mix(uBaseColor, uMidColor, noise);
    color = mix(color, uAccentColor, n2 * 0.3);

    // Caustic highlights
    float caustic = pow(n1 * n2, 3.0) * 1.5;
    color += vec3(0.93, 0.91, 0.89) * caustic * 0.12;

    // Scroll dimming
    float dim = 1.0 - uScrollProgress * 0.8;
    color *= dim;

    // Vignette
    vec2 vigUv = vUv * 2.0 - 1.0;
    float vig = 1.0 - dot(vigUv * 0.5, vigUv * 0.5);
    color *= smoothstep(0.0, 0.7, vig);

    gl_FragColor = vec4(color, 1.0);
  }
`

interface FluidMeshProps {
  baseColor: string
  midColor: string
  accentColor: string
  tempo: number
  density: number
  scrollProgress: number
}

function FluidMesh({
  baseColor,
  midColor,
  accentColor,
  tempo,
  density,
  scrollProgress,
}: FluidMeshProps) {
  const materialRef = useRef<ShaderMaterial>(null)
  const { size } = useThree()
  const mouse = useRef(new Vector2(0.5, 0.5))

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uScrollProgress: { value: 0 },
      uTempo: { value: tempo },
      uDensity: { value: density },
      uBaseColor: { value: new Color(baseColor) },
      uMidColor: { value: new Color(midColor) },
      uAccentColor: { value: new Color(accentColor) },
      uResolution: { value: new Vector2(size.width, size.height) },
      uMouse: { value: new Vector2(0.5, 0.5) },
    }),
    // Only recreate on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  useFrame(({ clock }) => {
    if (!materialRef.current) return
    materialRef.current.uniforms.uTime.value = clock.getElapsedTime()
    materialRef.current.uniforms.uScrollProgress.value = scrollProgress
    materialRef.current.uniforms.uTempo.value = tempo
    materialRef.current.uniforms.uDensity.value = density
    materialRef.current.uniforms.uBaseColor.value.set(baseColor)
    materialRef.current.uniforms.uMidColor.value.set(midColor)
    materialRef.current.uniforms.uAccentColor.value.set(accentColor)
    materialRef.current.uniforms.uResolution.value.set(size.width, size.height)
    materialRef.current.uniforms.uMouse.value.copy(mouse.current)
  })

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
      />
    </mesh>
  )
}

interface FluidShaderProps {
  baseColor?: string
  midColor?: string
  accentColor?: string
  tempo?: number
  density?: number
  scrollProgress?: number
}

export function FluidShader({
  baseColor = "#0F0D0B",
  midColor = "#1A5A3E",
  accentColor = "#1A7A5A",
  tempo = 1.0,
  density = 0.5,
  scrollProgress = 0,
}: FluidShaderProps) {
  return (
    <Canvas
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
      }}
      gl={{ antialias: false, alpha: false }}
      dpr={1}
    >
      <FluidMesh
        baseColor={baseColor}
        midColor={midColor}
        accentColor={accentColor}
        tempo={tempo}
        density={density}
        scrollProgress={scrollProgress}
      />
    </Canvas>
  )
}
```

**Step 4: Run test**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/fluid-shader.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/fluid-shader.tsx web/src/components/landing/__tests__/fluid-shader.test.tsx
git commit -m "feat(web): add FluidShader WebGL hero with simplex noise and DNA color uniforms"
```

---

## Task 8: Chapter Indicator Navigation

**Files:**
- Create: `web/src/components/landing/chapter-indicator.tsx`
- Test: `web/src/components/landing/__tests__/chapter-indicator.test.tsx`

**Step 1: Write failing test**

Create `web/src/components/landing/__tests__/chapter-indicator.test.tsx`:

```typescript
import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { ChapterIndicator } from "../chapter-indicator"

describe("ChapterIndicator", () => {
  it("renders dots for each chapter", () => {
    const { container } = render(
      <ChapterIndicator chapters={4} activeChapter={0} />,
    )
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots).toHaveLength(4)
  })

  it("highlights the active chapter", () => {
    const { container } = render(
      <ChapterIndicator chapters={4} activeChapter={2} />,
    )
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots[2].getAttribute("data-active")).toBe("true")
  })

  it("has correct aria labels", () => {
    const { container } = render(
      <ChapterIndicator
        chapters={4}
        activeChapter={1}
        labels={["The Signal", "The Engine", "The Proof", "The Path"]}
      />,
    )
    const nav = container.querySelector("nav")
    expect(nav?.getAttribute("aria-label")).toBe("Page chapters")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-indicator.test.tsx`
Expected: FAIL

**Step 3: Implement chapter indicator**

Create `web/src/components/landing/chapter-indicator.tsx`:

```typescript
"use client"

interface ChapterIndicatorProps {
  chapters: number
  activeChapter: number
  labels?: string[]
  onNavigate?: (index: number) => void
}

export function ChapterIndicator({
  chapters,
  activeChapter,
  labels,
  onNavigate,
}: ChapterIndicatorProps) {
  return (
    <nav
      aria-label="Page chapters"
      className="fixed right-6 top-1/2 -translate-y-1/2 z-50 hidden lg:flex flex-col gap-3"
    >
      {Array.from({ length: chapters }, (_, i) => (
        <button
          key={i}
          data-chapter-dot
          data-active={i === activeChapter ? "true" : "false"}
          aria-label={labels?.[i] ?? `Chapter ${i + 1}`}
          aria-current={i === activeChapter ? "step" : undefined}
          onClick={() => onNavigate?.(i)}
          className={`w-2 h-2 rounded-full transition-all duration-300 ${
            i === activeChapter
              ? "bg-[var(--color-accent)] scale-125"
              : "bg-[var(--color-text-tertiary)] opacity-40 hover:opacity-70"
          }`}
        />
      ))}
    </nav>
  )
}
```

**Step 4: Run test**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-indicator.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/chapter-indicator.tsx web/src/components/landing/__tests__/chapter-indicator.test.tsx
git commit -m "feat(web): add ChapterIndicator vertical dot navigation"
```

---

## Task 9: Chapter 1 — The Signal (Hero)

**Files:**
- Create: `web/src/components/landing/chapter-hero.tsx`
- Test: `web/src/components/landing/__tests__/chapter-hero.test.tsx`

**Step 1: Write failing test**

Create `web/src/components/landing/__tests__/chapter-hero.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  useScroll: () => ({ scrollYProgress: { get: () => 0 } }),
  useTransform: () => ({ get: () => 1 }),
  useMotionValueEvent: vi.fn(),
}))

import { ChapterHero } from "../chapter-hero"

describe("ChapterHero", () => {
  it("renders headline text", () => {
    const { getByText } = render(<ChapterHero />)
    expect(getByText(/Conviction/i)).toBeDefined()
  })

  it("renders primary CTA button", () => {
    const { getByRole } = render(<ChapterHero />)
    const cta = getByRole("link", { name: /start scoring/i })
    expect(cta).toBeDefined()
  })

  it("renders secondary CTA", () => {
    const { getByRole } = render(<ChapterHero />)
    const secondary = getByRole("link", { name: /see how it works/i })
    expect(secondary).toBeDefined()
  })

  it("renders scroll indicator", () => {
    const { container } = render(<ChapterHero />)
    const indicator = container.querySelector("[data-scroll-indicator]")
    expect(indicator).toBeDefined()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-hero.test.tsx`
Expected: FAIL

**Step 3: Implement hero chapter**

Create `web/src/components/landing/chapter-hero.tsx`:

```typescript
"use client"

import Link from "next/link"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

function WordReveal({ text, delay = 0 }: { text: string; delay?: number }) {
  return (
    <>
      {text.split(" ").map((word, i) => (
        <motion.span
          key={i}
          className="inline-block mr-[0.3em]"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: delay + i * 0.08, ease }}
        >
          {word}
        </motion.span>
      ))}
    </>
  )
}

export function ChapterHero() {
  return (
    <section className="relative h-screen flex items-center justify-center">
      <div className="relative z-10 text-center max-w-3xl mx-auto px-6">
        <motion.h1
          className="font-display text-5xl md:text-7xl lg:text-[88px] leading-[0.95] tracking-[-0.04em] text-[var(--color-text-primary)]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.01 }}
        >
          <WordReveal text="Conviction, Quantified." />
        </motion.h1>

        <motion.p
          className="mt-6 text-lg md:text-xl text-[var(--color-text-secondary)] max-w-xl mx-auto"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 0.6, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5, ease }}
        >
          A deterministic scoring engine that replaces gut feeling with
          structured, quantified investment conviction.
        </motion.p>

        <motion.div
          className="mt-10 flex items-center justify-center gap-4"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7, ease }}
        >
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium tracking-wide transition-colors hover:bg-[var(--color-accent-hover)]"
          >
            Start Scoring
          </Link>
          <Link
            href="#engine"
            className="inline-flex items-center justify-center h-12 px-6 text-sm font-medium text-[var(--color-text-secondary)] underline underline-offset-4 decoration-[var(--color-border-primary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            See How It Works
          </Link>
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        data-scroll-indicator
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.4 }}
        transition={{ delay: 1.2, duration: 0.6 }}
      >
        <motion.div
          className="w-px h-8 bg-[var(--color-text-tertiary)]"
          animate={{ scaleY: [1, 0.5, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      </motion.div>
    </section>
  )
}
```

**Step 4: Run test**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-hero.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/chapter-hero.tsx web/src/components/landing/__tests__/chapter-hero.test.tsx
git commit -m "feat(web): add ChapterHero with word-level reveal animation"
```

---

## Task 10: Chapter 2 — The Engine (Horizontal)

**Files:**
- Create: `web/src/components/landing/chapter-engine.tsx`
- Test: `web/src/components/landing/__tests__/chapter-engine.test.tsx`

**Step 1: Write failing test**

Create `web/src/components/landing/__tests__/chapter-engine.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    li: ({ children, ...props }: any) => <li {...props}>{children}</li>,
  },
  useInView: () => true,
}))

import { ChapterEngine } from "../chapter-engine"

describe("ChapterEngine", () => {
  it("renders three panels", () => {
    const { container } = render(<ChapterEngine />)
    const panels = container.querySelectorAll("[data-engine-panel]")
    expect(panels).toHaveLength(3)
  })

  it("renders Raw Signal panel content", () => {
    const { getByText } = render(<ChapterEngine />)
    expect(getByText(/raw signal/i)).toBeDefined()
  })

  it("renders Structured Analysis panel content", () => {
    const { getByText } = render(<ChapterEngine />)
    expect(getByText(/structured analysis/i)).toBeDefined()
  })

  it("renders Conviction Output panel content", () => {
    const { getByText } = render(<ChapterEngine />)
    expect(getByText(/conviction output/i)).toBeDefined()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-engine.test.tsx`
Expected: FAIL

**Step 3: Implement engine chapter**

Create `web/src/components/landing/chapter-engine.tsx`. This contains three panel sub-components showing the analysis pipeline progression: Raw Signal → Structured Analysis → Conviction Output. Each panel uses glass surfaces and the gradient mesh background. Use the `HorizontalScroll` wrapper from Task 6 around the three panels. Include scroll-triggered animations via Framer Motion `useInView` for element entrances within each panel. The content should be editorial (large serif headings, supporting body text) not technical.

Full implementation should follow the patterns from the existing `engine-diagram.tsx` (named export, "use client", motion components) but with the new glass/gradient visual language.

**Step 4: Run test**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-engine.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/chapter-engine.tsx web/src/components/landing/__tests__/chapter-engine.test.tsx
git commit -m "feat(web): add ChapterEngine horizontal scroll with 3 pipeline panels"
```

---

## Task 11: Chapter 3 — The Proof (Horizontal)

**Files:**
- Create: `web/src/components/landing/chapter-proof.tsx`
- Test: `web/src/components/landing/__tests__/chapter-proof.test.tsx`

Same structure as Task 10. Three panels: Sample Analysis (editorial score output), Factor Depth (animated bar chart for one factor), Portfolio View (ranked watchlist mockup). Uses `HorizontalScroll` wrapper, glass surfaces, Framer Motion scroll reveals.

**Step 1: Write failing test**

Test should verify: renders 3 panels, each contains expected content headings ("sample analysis", "factor depth", "portfolio view").

**Step 2-5: Implement, test, commit**

Follow same TDD pattern as Task 10.

```bash
git commit -m "feat(web): add ChapterProof horizontal scroll with analysis example panels"
```

---

## Task 12: Chapter 4 — The Path (Pricing + CTA)

**Files:**
- Create: `web/src/components/landing/chapter-path.tsx`
- Test: `web/src/components/landing/__tests__/chapter-path.test.tsx`

Vertical section. Reuses pricing data from existing `pricing-section.tsx` but with new glass surface treatment. Three pricing cards in `GlassSurface` components (middle card uses `elevated` variant). Final CTA block below.

**Step 1: Write failing test**

Test should verify: renders three pricing tiers (Scout, Operator, Allocator), renders CTA button, middle card has elevated glass treatment.

**Step 2-5: Implement, test, commit**

```bash
git commit -m "feat(web): add ChapterPath with glass pricing cards and final CTA"
```

---

## Task 13: Page Assembly

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/components/landing/index.ts` (update barrel exports)
- Test: `web/src/components/landing/__tests__/page-assembly.test.tsx` (update existing)

**Step 1: Update barrel exports**

Update `web/src/components/landing/index.ts` to export new chapter components and remove old section exports.

**Step 2: Rewrite page.tsx**

Replace the current 8-section page with the 4-chapter structure:

```typescript
import dynamic from "next/dynamic"
import { auth } from "@/lib/auth"
import { Navbar } from "@/components/nav"
import { DNAProvider } from "@/components/landing/dna-provider"
import { ChapterHero } from "@/components/landing/chapter-hero"
import { ChapterEngine } from "@/components/landing/chapter-engine"
import { ChapterProof } from "@/components/landing/chapter-proof"
import { ChapterPath } from "@/components/landing/chapter-path"
import { ChapterIndicator } from "@/components/landing/chapter-indicator"

const FluidShader = dynamic(
  () => import("@/components/landing/fluid-shader").then((m) => ({ default: m.FluidShader })),
  { ssr: false },
)

async function getDNA() {
  try {
    const session = await auth()
    if (!session) return null
    const res = await fetch(`${process.env.API_URL || "http://localhost:8000"}/api/v1/users/me/dna`, {
      headers: {
        "X-User-Id": String(session.userId || ""),
        "X-User-Email": session.user?.email || "",
      },
      next: { revalidate: 3600 },
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function Home() {
  const dna = await getDNA()

  return (
    <DNAProvider dna={dna}>
      <main>
        <FluidShader
          baseColor={dna?.base}
          midColor={dna?.mid}
          accentColor={dna?.accent}
          tempo={dna?.tempo}
          density={dna?.density}
        />
        <Navbar />
        <div className="relative z-10">
          <ChapterHero />
          <div className="h-[50vh]" /> {/* Chapter break */}
          <section id="engine">
            <ChapterEngine />
          </section>
          <div className="h-[50vh]" />
          <ChapterProof />
          <div className="h-[50vh]" />
          <ChapterPath />
        </div>
        <ChapterIndicator
          chapters={4}
          activeChapter={0}
          labels={["The Signal", "The Engine", "The Proof", "The Path"]}
        />
      </main>
    </DNAProvider>
  )
}
```

**Step 3: Update page assembly test**

Update existing test to verify new chapter structure renders.

**Step 4: Run all landing tests**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add web/src/app/page.tsx web/src/components/landing/index.ts web/src/components/landing/__tests__/page-assembly.test.tsx
git commit -m "feat(web): assemble 4-chapter landing page with fluid shader and DNA"
```

---

## Task 14: Remove Old Components

**Files:**
- Delete: `web/src/components/landing/scene-canvas.tsx`
- Delete: `web/src/components/landing/ambient-grid.tsx`
- Delete: `web/src/components/landing/engine-nodes.tsx`
- Delete: `web/src/components/landing/connection-lines.tsx`
- Delete: `web/src/components/landing/capability-cards-3d.tsx`
- Delete: `web/src/components/landing/postprocessing-stack.tsx`
- Delete: `web/src/components/landing/constellation-narrative.tsx`
- Delete: `web/src/components/landing/constellation-data.ts`
- Delete: `web/src/components/landing/landing-scene.tsx`
- Delete: `web/src/components/landing/webgl-scene.tsx`
- Delete: Old section files replaced by chapters (hero-section, friction-section, engine-diagram, engine-proof, capabilities-section, investor-positioning, final-cta, metrics-strip)
- Modify: `web/src/components/landing/index.ts` (remove old exports)

**Step 1: Verify no imports of old components remain**

Run grep for each deleted component name across the web/src directory. If any imports remain outside the deleted files, update them first.

**Step 2: Delete files**

Remove all listed files.

**Step 3: Update barrel exports**

Clean `web/src/components/landing/index.ts` to only export new chapter components.

**Step 4: Run all tests**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/`
Expected: ALL PASS (old tests for deleted components should also be removed)

**Step 5: Commit**

```bash
git add -A web/src/components/landing/
git commit -m "refactor(web): remove old WebGL scene and section components"
```

---

## Task 15: Visual QA & Accessibility Pass

**Files:** Various landing components

**Step 1: Verify reduced-motion support**

Add to `web/src/app/globals.css`:

```css
@media (prefers-reduced-motion: reduce) {
  .glass, .glass-elevated {
    backdrop-filter: blur(20px);
  }
}
```

Verify all Framer Motion animations respect `useReducedMotion()` or use `layout` animations that auto-respect the media query.

**Step 2: Verify WCAG contrast**

Check all text colors against glass surface backgrounds meet AA contrast ratio (4.5:1 for body text, 3:1 for large text).

**Step 3: Keyboard navigation**

Verify: Tab navigates through CTAs, horizontal scroll responds to arrow keys, chapter indicator is keyboard-accessible, focus rings are visible.

**Step 4: Mobile check**

Verify: No WebGL renders below 768px, horizontal chapters stack vertically, all text is readable, touch scrolling is smooth.

**Step 5: Commit any fixes**

```bash
git commit -m "fix(web): accessibility and reduced-motion pass for landing redesign"
```

---

## Task 16: Run Full Test Suite

**Step 1: Run all web tests**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/`
Expected: ALL PASS

**Step 2: Run API tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/ -v`
Expected: ALL PASS (including new DNA tests)

**Step 3: Run engine tests (should be unaffected)**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest engine/tests/ -v`
Expected: ALL PASS (no engine changes)

**Step 4: Build check**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next build`
Expected: Build succeeds with no TypeScript errors.

**Step 5: Final commit if any fixes needed**

```bash
git commit -m "fix(web): resolve test and build issues from landing redesign"
```
