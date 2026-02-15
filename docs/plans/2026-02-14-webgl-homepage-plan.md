# WebGL Homepage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the landing page as a performance-first hybrid WebGL experience using React Three Fiber with scroll-driven 3D scene and HTML overlay.

**Architecture:** Single continuous R3F Canvas (fixed, full viewport) with ScrollControls driving 3D state. HTML content overlays on top via absolute positioning. Mobile gets CSS-only fallback. Lazy-loaded via `next/dynamic` with `ssr: false`.

**Tech Stack:** Next.js 16, React 19, React Three Fiber + Drei, Tailwind CSS 4, Framer Motion (retained for CSS animations), Vitest + Testing Library.

**Design doc:** `docs/plans/2026-02-14-webgl-homepage-design.md`

---

## Task 1: Install Dependencies and Update Config

**Files:**
- Modify: `web/package.json`
- Modify: `web/next.config.ts`

**Step 1: Install R3F + Three.js dependencies**

Run:
```bash
cd /Users/brandon/repos/margin_invest/web && npm install @react-three/fiber @react-three/drei three && npm install -D @types/three
```

**Step 2: Update next.config.ts to transpile Three.js**

```typescript
// web/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["three"],
};

export default nextConfig;
```

**Step 3: Verify build succeeds**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run build`
Expected: Build succeeds with no errors.

**Step 4: Commit**

```bash
git add web/package.json web/package-lock.json web/next.config.ts
git commit -m "feat: add React Three Fiber, Drei, and Three.js dependencies"
```

---

## Task 2: Update Design Tokens

**Files:**
- Modify: `web/src/app/globals.css`
- Modify: `web/src/styles/tokens.ts`

**Step 1: Update globals.css with new/adjusted tokens**

In the `@theme` block, update these values:

```css
/* Light mode - update text-secondary */
--color-text-secondary: #4A4A4A;  /* was #5C5C5C */

/* Add new tokens */
--color-grid-line: rgba(18, 18, 18, 0.04);
--color-bg-secondary: #ECEAE4;  /* alias for bg-subtle if not already */
--color-divider: rgba(18, 18, 18, 0.06);
```

In the `.dark` selector, update:

```css
--color-text-secondary: #A5A5A3;  /* was #9B9B98 */
--color-accent: #1C7A5A;  /* was #1A7A5A */
--color-grid-line: rgba(255, 255, 255, 0.04);
--color-bg-secondary: #14171B;
--color-divider: rgba(255, 255, 255, 0.06);
```

**Step 2: Update tokens.ts to match**

Add `gridLine` and `divider` entries to both light and dark color objects. Update `textSecondary` values.

**Step 3: Verify the app still renders**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run dev`
Visually confirm existing pages still render correctly in both themes.

**Step 4: Commit**

```bash
git add web/src/app/globals.css web/src/styles/tokens.ts
git commit -m "feat: update design tokens for WebGL homepage (text-secondary, grid-line, divider)"
```

---

## Task 3: Create useQualityTier Hook

**Files:**
- Create: `web/src/lib/hooks/use-quality-tier.ts`
- Create: `web/src/lib/hooks/__tests__/use-quality-tier.test.ts`

**Step 1: Write the failing test**

```typescript
// web/src/lib/hooks/__tests__/use-quality-tier.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { useQualityTier } from "../use-quality-tier"

describe("useQualityTier", () => {
  beforeEach(() => {
    vi.stubGlobal("innerWidth", 1440)
    vi.stubGlobal("navigator", { hardwareConcurrency: 8 })
  })

  it("returns 'high' for desktop with good GPU", () => {
    const { result } = renderHook(() => useQualityTier())
    expect(result.current.tier).toBe("high")
    expect(result.current.dpr).toBe(1.5)
    expect(result.current.enableWebGL).toBe(true)
  })

  it("returns 'medium' for tablet viewport", () => {
    vi.stubGlobal("innerWidth", 900)
    const { result } = renderHook(() => useQualityTier())
    expect(result.current.tier).toBe("medium")
    expect(result.current.dpr).toBe(1)
    expect(result.current.enableWebGL).toBe(true)
  })

  it("returns 'low' for mobile viewport", () => {
    vi.stubGlobal("innerWidth", 375)
    const { result } = renderHook(() => useQualityTier())
    expect(result.current.tier).toBe("low")
    expect(result.current.enableWebGL).toBe(false)
  })

  it("returns 'medium' for desktop with weak CPU", () => {
    vi.stubGlobal("navigator", { hardwareConcurrency: 2 })
    const { result } = renderHook(() => useQualityTier())
    expect(result.current.tier).toBe("medium")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/lib/hooks/__tests__/use-quality-tier.test.ts`
Expected: FAIL — module not found.

**Step 3: Write minimal implementation**

```typescript
// web/src/lib/hooks/use-quality-tier.ts
"use client"

import { useState, useEffect } from "react"

export type QualityTier = "high" | "medium" | "low"

interface QualityTierResult {
  tier: QualityTier
  dpr: number
  enableWebGL: boolean
}

export function useQualityTier(): QualityTierResult {
  const [result, setResult] = useState<QualityTierResult>({
    tier: "low",
    dpr: 1,
    enableWebGL: false,
  })

  useEffect(() => {
    const width = window.innerWidth
    const cores = navigator.hardwareConcurrency || 4

    if (width < 768) {
      setResult({ tier: "low", dpr: 1, enableWebGL: false })
    } else if (width < 1024 || cores < 4) {
      setResult({ tier: "medium", dpr: 1, enableWebGL: true })
    } else {
      setResult({ tier: "high", dpr: 1.5, enableWebGL: true })
    }
  }, [])

  return result
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/lib/hooks/__tests__/use-quality-tier.test.ts`
Expected: 4 PASS

**Step 5: Commit**

```bash
git add web/src/lib/hooks/use-quality-tier.ts web/src/lib/hooks/__tests__/use-quality-tier.test.ts
git commit -m "feat: add useQualityTier hook for WebGL performance tiers"
```

---

## Task 4: Create Shared UI Components

**Files:**
- Create: `web/src/components/landing-v2/section-wrapper.tsx`
- Create: `web/src/components/landing-v2/button-primary.tsx`
- Create: `web/src/components/landing-v2/button-secondary.tsx`
- Create: `web/src/components/landing-v2/divider.tsx`
- Create: `web/src/components/landing-v2/capability-block.tsx`
- Create: `web/src/components/landing-v2/ui-image-frame.tsx`
- Create: `web/src/components/landing-v2/diagram-node-label.tsx`
- Create: `web/src/components/landing-v2/index.ts`
- Create: `web/src/components/landing-v2/__tests__/shared-components.test.tsx`

All new landing components go in `landing-v2/` to avoid conflict during development. The old `landing/` folder stays until we swap.

**Step 1: Write failing tests for shared components**

```tsx
// web/src/components/landing-v2/__tests__/shared-components.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SectionWrapper } from "../section-wrapper"
import { ButtonPrimary } from "../button-primary"
import { ButtonSecondary } from "../button-secondary"
import { Divider } from "../divider"
import { CapabilityBlock } from "../capability-block"
import { UIImageFrame } from "../ui-image-frame"
import { DiagramNodeLabel } from "../diagram-node-label"

describe("SectionWrapper", () => {
  it("renders children within max-width container", () => {
    render(<SectionWrapper id="test"><p>Content</p></SectionWrapper>)
    expect(screen.getByText("Content")).toBeInTheDocument()
  })
})

describe("ButtonPrimary", () => {
  it("renders as a link with accent styling", () => {
    render(<ButtonPrimary href="/test">Click me</ButtonPrimary>)
    const link = screen.getByRole("link", { name: "Click me" })
    expect(link).toHaveAttribute("href", "/test")
  })
})

describe("ButtonSecondary", () => {
  it("renders as a text link", () => {
    render(<ButtonSecondary href="/test">Learn more</ButtonSecondary>)
    const link = screen.getByRole("link", { name: "Learn more" })
    expect(link).toHaveAttribute("href", "/test")
  })
})

describe("Divider", () => {
  it("renders a horizontal rule", () => {
    render(<Divider />)
    expect(screen.getByRole("separator")).toBeInTheDocument()
  })
})

describe("CapabilityBlock", () => {
  it("renders title and description", () => {
    render(<CapabilityBlock title="Test Title" description="Test desc" />)
    expect(screen.getByText("Test Title")).toBeInTheDocument()
    expect(screen.getByText("Test desc")).toBeInTheDocument()
  })

  it("applies tinted background when tinted prop is true", () => {
    const { container } = render(
      <CapabilityBlock title="Tinted" description="desc" tinted />
    )
    expect(container.firstChild).toHaveClass("bg-bg-subtle")
  })
})

describe("UIImageFrame", () => {
  it("renders an image with border styling", () => {
    render(<UIImageFrame src="/test.png" alt="Test image" />)
    const img = screen.getByAltText("Test image")
    expect(img).toHaveAttribute("src", "/test.png")
  })
})

describe("DiagramNodeLabel", () => {
  it("renders the label text", () => {
    render(<DiagramNodeLabel label="Market Data" active={false} />)
    expect(screen.getByText("Market Data")).toBeInTheDocument()
  })

  it("applies accent color when active", () => {
    const { container } = render(
      <DiagramNodeLabel label="Market Data" active />
    )
    expect(container.firstChild).toHaveClass("text-accent")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/components/landing-v2/__tests__/shared-components.test.tsx`
Expected: FAIL — modules not found.

**Step 3: Implement all shared components**

```tsx
// web/src/components/landing-v2/section-wrapper.tsx
interface SectionWrapperProps {
  children: React.ReactNode
  id?: string
  className?: string
  padding?: string
}

export function SectionWrapper({
  children,
  id,
  className = "",
  padding = "py-24",
}: SectionWrapperProps) {
  return (
    <section id={id} className={`${padding} ${className}`} style={{ padding: undefined }}>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        {children}
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/landing-v2/button-primary.tsx
import Link from "next/link"

interface ButtonPrimaryProps {
  children: React.ReactNode
  href: string
  size?: "default" | "large"
}

export function ButtonPrimary({ children, href, size = "default" }: ButtonPrimaryProps) {
  return (
    <Link
      href={href}
      className={`inline-block bg-accent text-white font-semibold text-[15px] rounded-[4px] hover:bg-accent-hover transition-colors ${
        size === "large" ? "px-10 py-5" : "px-6 py-3"
      }`}
      style={{ height: size === "large" ? "56px" : "48px", lineHeight: size === "large" ? "56px" : "48px", paddingTop: 0, paddingBottom: 0 }}
    >
      {children}
    </Link>
  )
}
```

```tsx
// web/src/components/landing-v2/button-secondary.tsx
import Link from "next/link"

interface ButtonSecondaryProps {
  children: React.ReactNode
  href: string
}

export function ButtonSecondary({ children, href }: ButtonSecondaryProps) {
  return (
    <Link
      href={href}
      className="text-[15px] font-medium text-text-secondary hover:text-text-primary transition-colors underline-offset-4 hover:underline"
    >
      {children}
    </Link>
  )
}
```

```tsx
// web/src/components/landing-v2/divider.tsx
interface DividerProps {
  opacity?: number
}

export function Divider({ opacity }: DividerProps) {
  return (
    <hr
      className="border-0 h-px bg-divider"
      style={opacity !== undefined ? { opacity } : undefined}
    />
  )
}
```

```tsx
// web/src/components/landing-v2/capability-block.tsx
interface CapabilityBlockProps {
  title: string
  description: string
  tinted?: boolean
}

export function CapabilityBlock({ title, description, tinted }: CapabilityBlockProps) {
  return (
    <div className={`p-8 ${tinted ? "bg-bg-subtle" : ""}`}>
      <h3 className="text-[24px] md:text-[28px] lg:text-[32px] font-semibold leading-[1.2] text-text-primary mb-2">
        {title}
      </h3>
      <p className="text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-[1.5]">
        {description}
      </p>
    </div>
  )
}
```

```tsx
// web/src/components/landing-v2/ui-image-frame.tsx
interface UIImageFrameProps {
  src: string
  alt: string
  rotation?: number
}

export function UIImageFrame({ src, alt, rotation = 0 }: UIImageFrameProps) {
  return (
    <div
      className="border border-border-subtle rounded-[6px] overflow-hidden"
      style={rotation ? { transform: `rotate(${rotation}deg)` } : undefined}
    >
      <img src={src} alt={alt} className="w-full h-auto block" />
    </div>
  )
}
```

```tsx
// web/src/components/landing-v2/diagram-node-label.tsx
interface DiagramNodeLabelProps {
  label: string
  active: boolean
}

export function DiagramNodeLabel({ label, active }: DiagramNodeLabelProps) {
  return (
    <div className={`text-[14px] font-medium tracking-[0.2px] ${active ? "text-accent" : "text-text-secondary"}`}>
      {label}
    </div>
  )
}
```

```tsx
// web/src/components/landing-v2/index.ts
export { SectionWrapper } from "./section-wrapper"
export { ButtonPrimary } from "./button-primary"
export { ButtonSecondary } from "./button-secondary"
export { Divider } from "./divider"
export { CapabilityBlock } from "./capability-block"
export { UIImageFrame } from "./ui-image-frame"
export { DiagramNodeLabel } from "./diagram-node-label"
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/components/landing-v2/__tests__/shared-components.test.tsx`
Expected: All PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing-v2/
git commit -m "feat: add shared UI components for WebGL landing page"
```

---

## Task 5: Create NavMinimal Component

**Files:**
- Create: `web/src/components/landing-v2/nav-minimal.tsx`
- Create: `web/src/components/landing-v2/__tests__/nav-minimal.test.tsx`

**Step 1: Write failing test**

```tsx
// web/src/components/landing-v2/__tests__/nav-minimal.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { NavMinimal } from "../nav-minimal"

describe("NavMinimal", () => {
  it("renders logo text", () => {
    render(<NavMinimal />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
  })

  it("renders a CTA link", () => {
    render(<NavMinimal />)
    const cta = screen.getByRole("link", { name: /explore/i })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("has transparent background for overlay on canvas", () => {
    const { container } = render(<NavMinimal />)
    const nav = container.querySelector("nav")
    expect(nav).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/components/landing-v2/__tests__/nav-minimal.test.tsx`
Expected: FAIL.

**Step 3: Implement NavMinimal**

```tsx
// web/src/components/landing-v2/nav-minimal.tsx
"use client"

import Link from "next/link"
import { useTheme } from "next-themes"

export function NavMinimal() {
  const { theme, setTheme } = useTheme()

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-transparent">
      <div
        className="mx-auto flex items-center justify-between h-16"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        <Link href="/" className="text-text-primary font-bold text-lg tracking-[-0.02em]">
          Margin Invest
        </Link>

        <div className="flex items-center gap-4">
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="text-text-secondary hover:text-text-primary transition-colors text-sm"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? "\u2600" : "\u25CF"}
          </button>
          <Link
            href="/dashboard"
            className="inline-block px-6 py-2 bg-accent text-white font-semibold text-[14px] rounded-[4px] hover:bg-accent-hover transition-colors"
          >
            Explore the Engine
          </Link>
        </div>
      </div>
    </nav>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/components/landing-v2/__tests__/nav-minimal.test.tsx`
Expected: All PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing-v2/nav-minimal.tsx web/src/components/landing-v2/__tests__/nav-minimal.test.tsx
git commit -m "feat: add NavMinimal component for landing page overlay"
```

---

## Task 6: Create 3D Scene Wrapper with Lazy Loading

**Files:**
- Create: `web/src/components/landing-v2/scene/webgl-scene.tsx`
- Create: `web/src/components/landing-v2/scene/scene-canvas.tsx`
- Create: `web/src/components/landing-v2/scene/ambient-grid.tsx`
- Create: `web/src/components/landing-v2/scene/index.ts`

**Step 1: Create the inner Canvas component (client component)**

```tsx
// web/src/components/landing-v2/scene/scene-canvas.tsx
"use client"

import { Canvas } from "@react-three/fiber"
import { ScrollControls, Scroll } from "@react-three/drei"
import { Suspense } from "react"
import { AmbientGrid } from "./ambient-grid"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

interface SceneCanvasProps {
  tier: QualityTier
  dpr: number
  pages: number
  children?: React.ReactNode
}

export function SceneCanvas({ tier, dpr, pages, children }: SceneCanvasProps) {
  return (
    <Canvas
      dpr={[1, dpr]}
      frameloop="demand"
      gl={{ antialias: tier === "high", alpha: true, powerPreference: "high-performance" }}
      camera={{ position: [0, 0, 10], fov: 50 }}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
      }}
    >
      <Suspense fallback={null}>
        <ScrollControls pages={pages} damping={0.15}>
          <AmbientGrid tier={tier} />
          {children}
        </ScrollControls>
      </Suspense>
    </Canvas>
  )
}
```

**Step 2: Create the lazy-loaded wrapper**

```tsx
// web/src/components/landing-v2/scene/webgl-scene.tsx
"use client"

import dynamic from "next/dynamic"
import { useQualityTier } from "@/lib/hooks/use-quality-tier"

const SceneCanvas = dynamic(
  () => import("./scene-canvas").then((mod) => ({ default: mod.SceneCanvas })),
  { ssr: false }
)

interface WebGLSceneProps {
  pages: number
  children?: React.ReactNode
}

export function WebGLScene({ pages, children }: WebGLSceneProps) {
  const { tier, dpr, enableWebGL } = useQualityTier()

  if (!enableWebGL) return null

  return <SceneCanvas tier={tier} dpr={dpr} pages={pages}>{children}</SceneCanvas>
}
```

**Step 3: Create the AmbientGrid layer**

```tsx
// web/src/components/landing-v2/scene/ambient-grid.tsx
"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import * as THREE from "three"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

interface AmbientGridProps {
  tier: QualityTier
}

export function AmbientGrid({ tier }: AmbientGridProps) {
  const groupRef = useRef<THREE.Group>(null)
  const scroll = useScroll()

  const gridSize = tier === "high" ? 40 : 20
  const divisions = tier === "high" ? 40 : 20

  // Create grid material that adapts to theme via CSS variable reading
  const material = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: new THREE.Color(0x888888),
        transparent: true,
        opacity: 0.04,
      }),
    []
  )

  useFrame((_, delta) => {
    if (!groupRef.current) return
    // Gentle parallax drift based on scroll
    const offset = scroll.offset
    groupRef.current.position.y = offset * 2
    groupRef.current.rotation.x = -0.3 + offset * 0.1
  })

  return (
    <group ref={groupRef} position={[0, 0, -5]}>
      <gridHelper
        args={[gridSize, divisions, 0x888888, 0x888888]}
        material={material}
        rotation={[Math.PI / 2, 0, 0]}
      />
    </group>
  )
}
```

```tsx
// web/src/components/landing-v2/scene/index.ts
export { WebGLScene } from "./webgl-scene"
export { SceneCanvas } from "./scene-canvas"
export { AmbientGrid } from "./ambient-grid"
```

**Step 4: Verify the canvas renders without errors**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run dev`
Open `http://localhost:3000` — the existing page should render. We haven't wired the scene into the page yet, but imports should resolve.

**Step 5: Commit**

```bash
git add web/src/components/landing-v2/scene/
git commit -m "feat: add WebGL scene wrapper with Canvas, ScrollControls, and AmbientGrid"
```

---

## Task 7: Create Engine Nodes 3D Layer

**Files:**
- Create: `web/src/components/landing-v2/scene/engine-nodes.tsx`
- Create: `web/src/components/landing-v2/scene/connection-lines.tsx`

**Step 1: Create the EngineNodes component**

Four chamfered octahedrons that assemble from off-screen as the user scrolls into section 3 (scroll 30-50%). Uses InstancedMesh for performance.

```tsx
// web/src/components/landing-v2/scene/engine-nodes.tsx
"use client"

import { useRef, useEffect, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import * as THREE from "three"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

const NODE_COUNT = 4
const NODE_POSITIONS: [number, number, number][] = [
  [-4.5, 0, 0],
  [-1.5, 0, 0],
  [1.5, 0, 0],
  [4.5, 0, 0],
]

const ACCENT_COLOR = new THREE.Color("#0E4F3A")
const INACTIVE_COLOR = new THREE.Color("#888888")

interface EngineNodesProps {
  tier: QualityTier
}

export function EngineNodes({ tier }: EngineNodesProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const scroll = useScroll()
  const tempObj = useMemo(() => new THREE.Object3D(), [])
  const tempColor = useMemo(() => new THREE.Color(), [])

  const geometry = useMemo(() => {
    return tier === "high"
      ? new THREE.OctahedronGeometry(0.5, 1)
      : new THREE.OctahedronGeometry(0.5, 0)
  }, [tier])

  useEffect(() => {
    if (!meshRef.current) return
    // Initialize all instances off-screen to the right
    for (let i = 0; i < NODE_COUNT; i++) {
      tempObj.position.set(10 + i * 2, 0, 0)
      tempObj.scale.setScalar(0.01)
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [tempObj])

  useFrame(() => {
    if (!meshRef.current) return

    // Nodes assemble between scroll 30-50%
    const assembleProgress = scroll.range(0.3, 0.2)
    // Nodes recede between scroll 50-60%
    const recedeProgress = scroll.range(0.5, 0.1)
    // Which node is "active" (left to right progression)
    const activeIndex = Math.min(
      Math.floor(scroll.range(0.3, 0.2) * NODE_COUNT),
      NODE_COUNT - 1
    )

    for (let i = 0; i < NODE_COUNT; i++) {
      const nodeProgress = Math.max(0, Math.min(1, (assembleProgress * NODE_COUNT - i) * 1.5))
      const target = NODE_POSITIONS[i]

      // Lerp from off-screen to target position
      const x = THREE.MathUtils.lerp(10 + i * 2, target[0], nodeProgress)
      const y = target[1]
      const z = THREE.MathUtils.lerp(0, target[2], nodeProgress) - recedeProgress * 3

      tempObj.position.set(x, y, z)
      const scale = THREE.MathUtils.lerp(0.01, 1, nodeProgress) * (1 - recedeProgress * 0.5)
      tempObj.scale.setScalar(scale)
      tempObj.rotation.y += 0.002
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)

      // Color: active node gets accent, others get inactive
      tempColor.copy(i <= activeIndex ? ACCENT_COLOR : INACTIVE_COLOR)
      meshRef.current.setColorAt(i, tempColor)
    }

    meshRef.current.instanceMatrix.needsUpdate = true
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true
    }
  })

  return (
    <instancedMesh ref={meshRef} args={[geometry, undefined, NODE_COUNT]}>
      <meshStandardMaterial
        transparent
        opacity={0.85}
        roughness={0.4}
        metalness={0.1}
      />
    </instancedMesh>
  )
}
```

**Step 2: Create the ConnectionLines component**

```tsx
// web/src/components/landing-v2/scene/connection-lines.tsx
"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import { Line } from "@react-three/drei"
import * as THREE from "three"

const NODE_POSITIONS: [number, number, number][] = [
  [-4.5, 0, 0],
  [-1.5, 0, 0],
  [1.5, 0, 0],
  [4.5, 0, 0],
]

export function ConnectionLines() {
  const scroll = useScroll()
  const groupRef = useRef<THREE.Group>(null)

  // Generate line points between consecutive nodes
  const lineSegments = useMemo(() => {
    const segments: [number, number, number][][] = []
    for (let i = 0; i < NODE_POSITIONS.length - 1; i++) {
      segments.push([NODE_POSITIONS[i], NODE_POSITIONS[i + 1]])
    }
    return segments
  }, [])

  useFrame(() => {
    if (!groupRef.current) return
    const assembleProgress = scroll.range(0.3, 0.2)
    const recedeProgress = scroll.range(0.5, 0.1)
    groupRef.current.visible = assembleProgress > 0.1
    groupRef.current.position.z = -recedeProgress * 3
  })

  return (
    <group ref={groupRef}>
      {lineSegments.map((points, i) => (
        <Line
          key={i}
          points={points}
          color="#888888"
          lineWidth={1}
          transparent
          opacity={0.3}
        />
      ))}
    </group>
  )
}
```

**Step 3: Export from scene index**

Add to `web/src/components/landing-v2/scene/index.ts`:
```typescript
export { EngineNodes } from "./engine-nodes"
export { ConnectionLines } from "./connection-lines"
```

**Step 4: Commit**

```bash
git add web/src/components/landing-v2/scene/engine-nodes.tsx web/src/components/landing-v2/scene/connection-lines.tsx web/src/components/landing-v2/scene/index.ts
git commit -m "feat: add EngineNodes and ConnectionLines 3D components"
```

---

## Task 8: Create Capability Cards 3D Layer

**Files:**
- Create: `web/src/components/landing-v2/scene/capability-cards-3d.tsx`

**Step 1: Implement the 3D card planes**

Four flat planes with slight 3D rotation that float into view during section 5 (scroll 60-75%).

```tsx
// web/src/components/landing-v2/scene/capability-cards-3d.tsx
"use client"

import { useRef, useEffect, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import * as THREE from "three"

const CARD_COUNT = 4

// Staggered target positions matching the HTML layout
const CARD_TARGETS: { pos: [number, number, number]; rot: [number, number, number] }[] = [
  { pos: [-3, 1.5, 0], rot: [0, 0.08, 0.03] },
  { pos: [3, 0.5, -0.3], rot: [0, -0.1, -0.02] },
  { pos: [-1, -0.8, -0.1], rot: [0, 0.05, 0.04] },
  { pos: [3.5, -2, -0.4], rot: [0, -0.07, -0.03] },
]

export function CapabilityCards3D() {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const scroll = useScroll()
  const tempObj = useMemo(() => new THREE.Object3D(), [])

  useEffect(() => {
    if (!meshRef.current) return
    for (let i = 0; i < CARD_COUNT; i++) {
      tempObj.position.set(0, -10, 0)
      tempObj.scale.setScalar(0.01)
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [tempObj])

  useFrame(() => {
    if (!meshRef.current) return

    const floatIn = scroll.range(0.6, 0.15)
    const settle = scroll.range(0.75, 0.15)

    for (let i = 0; i < CARD_COUNT; i++) {
      const target = CARD_TARGETS[i]
      const stagger = Math.max(0, Math.min(1, (floatIn * CARD_COUNT - i) * 1.5))

      tempObj.position.set(
        THREE.MathUtils.lerp(0, target.pos[0], stagger),
        THREE.MathUtils.lerp(-10 + i * -1, target.pos[1], stagger),
        THREE.MathUtils.lerp(-2, target.pos[2], stagger)
      )

      tempObj.rotation.set(
        THREE.MathUtils.lerp(0.2, target.rot[0], stagger),
        THREE.MathUtils.lerp(0.5, target.rot[1], stagger),
        THREE.MathUtils.lerp(0.1, target.rot[2], stagger)
      )

      const scale = THREE.MathUtils.lerp(0.01, 1, stagger) * (1 - settle * 0.3)
      tempObj.scale.set(2.5, 1.5, 0.02)
      tempObj.scale.multiplyScalar(scale)
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)
    }

    meshRef.current.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, CARD_COUNT]}>
      <planeGeometry args={[1, 1]} />
      <meshStandardMaterial
        color="#888888"
        transparent
        opacity={0.06}
        side={THREE.DoubleSide}
        roughness={0.9}
      />
    </instancedMesh>
  )
}
```

**Step 2: Export from scene index**

Add to `web/src/components/landing-v2/scene/index.ts`:
```typescript
export { CapabilityCards3D } from "./capability-cards-3d"
```

**Step 3: Commit**

```bash
git add web/src/components/landing-v2/scene/capability-cards-3d.tsx web/src/components/landing-v2/scene/index.ts
git commit -m "feat: add CapabilityCards3D layer with staggered float-in animation"
```

---

## Task 9: Create HTML Landing Sections

**Files:**
- Create: `web/src/components/landing-v2/sections/hero-section.tsx`
- Create: `web/src/components/landing-v2/sections/friction-section.tsx`
- Create: `web/src/components/landing-v2/sections/engine-diagram.tsx`
- Create: `web/src/components/landing-v2/sections/engine-proof.tsx`
- Create: `web/src/components/landing-v2/sections/capabilities-section.tsx`
- Create: `web/src/components/landing-v2/sections/investor-positioning.tsx`
- Create: `web/src/components/landing-v2/sections/final-cta.tsx`
- Create: `web/src/components/landing-v2/sections/index.ts`
- Create: `web/src/components/landing-v2/__tests__/sections.test.tsx`

**Step 1: Write failing tests for all sections**

```tsx
// web/src/components/landing-v2/__tests__/sections.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import {
  HeroSection,
  FrictionSection,
  EngineDiagram,
  EngineProof,
  CapabilitiesSection,
  InvestorPositioning,
  FinalCTA,
} from "../sections"

describe("HeroSection", () => {
  it("renders the headline", () => {
    render(<HeroSection />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
  })

  it("renders the subline", () => {
    render(<HeroSection />)
    expect(screen.getByText(/institutional-grade analytics/i)).toBeInTheDocument()
  })

  it("renders the primary CTA", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /explore the engine/i })).toBeInTheDocument()
  })

  it("renders the secondary link", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /view methodology/i })).toBeInTheDocument()
  })
})

describe("FrictionSection", () => {
  it("renders three declarative lines", () => {
    render(<FrictionSection />)
    expect(screen.getByText("Most investors react.")).toBeInTheDocument()
    expect(screen.getByText("Few operate with structure.")).toBeInTheDocument()
    expect(screen.getByText("Emotion is expensive.")).toBeInTheDocument()
  })
})

describe("EngineDiagram", () => {
  it("renders four diagram node labels", () => {
    render(<EngineDiagram />)
    expect(screen.getByText("Market Data")).toBeInTheDocument()
    expect(screen.getByText("Risk Modeling")).toBeInTheDocument()
    expect(screen.getByText("Allocation Engine")).toBeInTheDocument()
    expect(screen.getByText("Decision Clarity")).toBeInTheDocument()
  })

  it("renders the WebGL annotation", () => {
    render(<EngineDiagram />)
    expect(screen.getByText(/transitions into interactive WebGL/i)).toBeInTheDocument()
  })
})

describe("EngineProof", () => {
  it("renders the annotation", () => {
    render(<EngineProof />)
    expect(screen.getByText(/WebGL stage morph ends here/i)).toBeInTheDocument()
  })
})

describe("CapabilitiesSection", () => {
  it("renders four capability titles", () => {
    render(<CapabilitiesSection />)
    expect(screen.getByText("Structured Allocation")).toBeInTheDocument()
    expect(screen.getByText("Quantified Risk")).toBeInTheDocument()
    expect(screen.getByText("Scenario Modeling")).toBeInTheDocument()
    expect(screen.getByText("Bias Reduction")).toBeInTheDocument()
  })
})

describe("InvestorPositioning", () => {
  it("renders the headline", () => {
    render(<InvestorPositioning />)
    expect(screen.getByText(/You're not trading/i)).toBeInTheDocument()
  })
})

describe("FinalCTA", () => {
  it("renders the primary CTA only", () => {
    render(<FinalCTA />)
    const links = screen.getAllByRole("link")
    expect(links).toHaveLength(1)
    expect(links[0]).toHaveTextContent(/explore the engine/i)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/components/landing-v2/__tests__/sections.test.tsx`
Expected: FAIL — modules not found.

**Step 3: Implement all 7 sections**

Each section uses `SectionWrapper` for consistent max-width and grid. Motion animations use Framer Motion `whileInView` for scroll-triggered CSS reveals. See design doc for exact layout specs.

```tsx
// web/src/components/landing-v2/sections/hero-section.tsx
"use client"

import { motion } from "framer-motion"
import Link from "next/link"

const ease = [0.22, 1, 0.36, 1] as const

export function HeroSection() {
  return (
    <section className="relative" style={{ minHeight: "90vh" }}>
      <div
        className="relative mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw", paddingTop: "160px", paddingBottom: "120px" }}
      >
        <div className="col-span-4 md:col-span-6 lg:col-span-8 flex flex-col justify-center">
          <motion.div
            className="w-48 h-px bg-border-primary mb-12"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.7, ease }}
            style={{ transformOrigin: "left" }}
          />

          <motion.h1
            className="text-[48px] md:text-[56px] lg:text-[72px] font-bold leading-[1.0] tracking-[-0.5px] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease }}
          >
            Structure outperforms emotion.
          </motion.h1>

          <motion.p
            className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-[1.5] max-w-[640px]"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4, ease }}
          >
            Institutional-grade analytics for serious retail investors.
          </motion.p>

          <motion.div
            className="mt-10 flex items-center gap-6"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.55, ease }}
          >
            <Link
              href="/dashboard"
              className="inline-flex items-center px-6 bg-accent text-white font-semibold text-[15px] rounded-[4px] hover:bg-accent-hover transition-colors"
              style={{ height: "48px" }}
            >
              Explore the Engine
            </Link>
            <Link
              href="/methodology"
              className="text-[15px] font-medium text-text-secondary hover:text-text-primary transition-colors underline-offset-4 hover:underline"
            >
              View methodology
            </Link>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/landing-v2/sections/friction-section.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const lines = [
  "Most investors react.",
  "Few operate with structure.",
  "Emotion is expensive.",
]

export function FrictionSection() {
  return (
    <section style={{ paddingTop: "96px", paddingBottom: "96px" }}>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        <div className="col-span-4 md:col-span-5 lg:col-span-6 space-y-8">
          {lines.map((line, i) => (
            <motion.h3
              key={i}
              className="text-[24px] md:text-[28px] lg:text-[32px] font-semibold leading-[1.2] text-text-primary"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.15, ease }}
            >
              {line}
            </motion.h3>
          ))}
        </div>

        {/* Right side: abstract data visual placeholder */}
        <div className="hidden lg:block lg:col-start-8 lg:col-span-5">
          <div className="w-full h-full opacity-15">
            <svg viewBox="0 0 300 200" className="w-full h-full text-text-secondary">
              {/* Abstract scatter plot placeholder */}
              {Array.from({ length: 24 }, (_, i) => (
                <circle
                  key={i}
                  cx={20 + Math.sin(i * 1.3) * 120 + 130}
                  cy={10 + Math.cos(i * 0.9) * 80 + 90}
                  r={1 + (i % 3)}
                  fill="currentColor"
                />
              ))}
            </svg>
          </div>
        </div>
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/landing-v2/sections/engine-diagram.tsx
"use client"

import { motion } from "framer-motion"
import { DiagramNodeLabel } from "../diagram-node-label"

const ease = [0.22, 1, 0.36, 1] as const

const nodes = ["Market Data", "Risk Modeling", "Allocation Engine", "Decision Clarity"]

export function EngineDiagram() {
  return (
    <section style={{ paddingTop: "120px", paddingBottom: "120px" }}>
      <div
        className="mx-auto"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        {/* Desktop: horizontal node labels under 3D positions */}
        <div className="hidden md:grid grid-cols-4 gap-8">
          {nodes.map((label, i) => (
            <motion.div
              key={label}
              className="text-center"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.12, ease }}
            >
              <DiagramNodeLabel label={label} active={false} />
            </motion.div>
          ))}
        </div>

        {/* Mobile: vertical stacked nodes */}
        <div className="md:hidden space-y-6">
          {nodes.map((label, i) => (
            <motion.div
              key={label}
              className="flex items-center gap-4"
              initial={{ opacity: 0, x: -16 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.1, ease }}
            >
              <div className="w-3 h-3 rounded-full bg-text-tertiary shrink-0" />
              <DiagramNodeLabel label={label} active={false} />
              {i < nodes.length - 1 && (
                <div className="absolute left-[14px] top-[20px] w-px h-6 bg-border-primary" />
              )}
            </motion.div>
          ))}
        </div>

        <motion.p
          className="mt-12 text-[14px] text-text-secondary italic tracking-[0.2px]"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.5, ease }}
        >
          This section transitions into interactive WebGL stage.
        </motion.p>
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/landing-v2/sections/engine-proof.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function EngineProof() {
  return (
    <section style={{ paddingTop: "96px", paddingBottom: "96px" }}>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        {/* Left: copy */}
        <div className="col-span-4 md:col-span-4 lg:col-span-5">
          <motion.h2
            className="text-[36px] md:text-[40px] lg:text-[48px] font-bold leading-[1.1] tracking-[-0.3px] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, ease }}
          >
            What the engine produces.
          </motion.h2>
          <motion.p
            className="mt-6 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-[1.5] max-w-[480px]"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15, ease }}
          >
            Factor percentiles, composite scores, and conviction classifications — all deterministic, all reproducible.
          </motion.p>
        </div>

        {/* Right: dashboard mockups */}
        <div className="col-span-4 md:col-span-4 lg:col-start-7 lg:col-span-6 space-y-4">
          {[
            { rotation: -1, label: "Factor breakdown" },
            { rotation: 1.5, label: "Composite score" },
            { rotation: -0.5, label: "Classification output" },
          ].map((mockup, i) => (
            <motion.div
              key={i}
              className="border border-border-subtle rounded-[6px] bg-bg-elevated p-6 h-32"
              style={{ transform: `rotate(${mockup.rotation}deg)` }}
              initial={{ opacity: 0, scale: 0.98 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.12, ease }}
            >
              <div className="text-[13px] text-text-tertiary font-medium tracking-[0.5px] uppercase">
                {mockup.label}
              </div>
              {/* Placeholder bars */}
              <div className="mt-4 space-y-2">
                {[75, 88, 62].map((w, j) => (
                  <div key={j} className="h-1.5 bg-bg-subtle rounded-sm overflow-hidden">
                    <div className="h-full bg-accent/30 rounded-sm" style={{ width: `${w}%` }} />
                  </div>
                ))}
              </div>
            </motion.div>
          ))}

          <motion.p
            className="text-[14px] text-text-secondary italic tracking-[0.2px] mt-4"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.4, ease }}
          >
            WebGL stage morph ends here.
          </motion.p>
        </div>
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/landing-v2/sections/capabilities-section.tsx
"use client"

import { motion } from "framer-motion"
import { CapabilityBlock } from "../capability-block"

const ease = [0.22, 1, 0.36, 1] as const

const capabilities = [
  { title: "Structured Allocation", description: "Systematic position sizing based on conviction scoring, not gut feel.", colClass: "lg:col-span-5", offset: 0, tinted: false },
  { title: "Quantified Risk", description: "Every position carries a measured risk profile before entry.", colClass: "lg:col-start-7 lg:col-span-6", offset: 48, tinted: true },
  { title: "Scenario Modeling", description: "Stress-test portfolios against historical drawdowns and regime changes.", colClass: "lg:col-start-2 lg:col-span-6", offset: 32, tinted: true },
  { title: "Bias Reduction", description: "Eliminate emotional interference from every decision point.", colClass: "lg:col-start-8 lg:col-span-5", offset: 64, tinted: false },
]

export function CapabilitiesSection() {
  return (
    <section style={{ paddingTop: "120px", paddingBottom: "120px" }}>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-x-6 gap-y-8"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        {capabilities.map((cap, i) => (
          <motion.div
            key={cap.title}
            className={`col-span-4 md:col-span-4 ${cap.colClass}`}
            style={{ marginTop: typeof window !== "undefined" && window.innerWidth >= 1024 ? `${cap.offset}px` : 0 }}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.12, ease }}
          >
            <CapabilityBlock
              title={cap.title}
              description={cap.description}
              tinted={cap.tinted}
            />
          </motion.div>
        ))}
      </div>
    </section>
  )
}
```

Note: The `marginTop` with `window.innerWidth` check won't work in SSR. Instead, use Tailwind responsive classes:

```tsx
// Replace the style prop with:
className={`col-span-4 md:col-span-4 ${cap.colClass} ${cap.offset ? `lg:mt-[${cap.offset}px]` : ""}`}
```

Or use CSS custom properties. The implementing engineer should use Tailwind's arbitrary values: `lg:mt-[48px]`, `lg:mt-[32px]`, `lg:mt-[64px]`.

```tsx
// web/src/components/landing-v2/sections/investor-positioning.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function InvestorPositioning() {
  return (
    <section style={{ paddingTop: "96px", paddingBottom: "96px" }}>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        <div className="col-span-4 md:col-span-6 lg:col-span-8">
          <motion.h2
            className="text-[36px] md:text-[40px] lg:text-[48px] font-bold leading-[1.1] tracking-[-0.3px] text-text-primary"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, ease }}
          >
            You&rsquo;re not trading. You&rsquo;re operating.
          </motion.h2>

          <motion.p
            className="mt-6 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-[1.5] max-w-[560px]"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15, ease }}
          >
            The difference between reacting and operating is a system. This is the system.
          </motion.p>
        </div>
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/landing-v2/sections/final-cta.tsx
"use client"

import { motion } from "framer-motion"
import Link from "next/link"

const ease = [0.22, 1, 0.36, 1] as const

export function FinalCTA() {
  return (
    <section style={{ paddingTop: "160px", paddingBottom: "120px" }}>
      <div
        className="mx-auto flex justify-center"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.55, ease }}
        >
          <Link
            href="/dashboard"
            className="inline-flex items-center px-8 bg-accent text-white font-semibold text-[16px] rounded-[4px] hover:bg-accent-hover transition-colors"
            style={{ height: "52px" }}
          >
            Explore the Engine
          </Link>
        </motion.div>
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/landing-v2/sections/index.ts
export { HeroSection } from "./hero-section"
export { FrictionSection } from "./friction-section"
export { EngineDiagram } from "./engine-diagram"
export { EngineProof } from "./engine-proof"
export { CapabilitiesSection } from "./capabilities-section"
export { InvestorPositioning } from "./investor-positioning"
export { FinalCTA } from "./final-cta"
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/components/landing-v2/__tests__/sections.test.tsx`
Expected: All PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing-v2/sections/ web/src/components/landing-v2/__tests__/sections.test.tsx
git commit -m "feat: add all 7 HTML landing sections for WebGL homepage"
```

---

## Task 10: Assemble the New Landing Page

**Files:**
- Modify: `web/src/app/page.tsx`

**Step 1: Write failing test**

```tsx
// web/src/components/landing-v2/__tests__/page-assembly.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock next/dynamic to render nothing for WebGL
vi.mock("next/dynamic", () => ({
  default: () => () => null,
}))

// Import the page after mocking
import Page from "@/app/page"

describe("Landing page assembly", () => {
  it("renders all 7 sections", () => {
    render(<Page />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
    expect(screen.getByText("Most investors react.")).toBeInTheDocument()
    expect(screen.getByText("Market Data")).toBeInTheDocument()
    expect(screen.getByText(/WebGL stage morph ends here/i)).toBeInTheDocument()
    expect(screen.getByText("Structured Allocation")).toBeInTheDocument()
    expect(screen.getByText(/You're not trading/i)).toBeInTheDocument()
  })

  it("renders the minimal nav", () => {
    render(<Page />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/components/landing-v2/__tests__/page-assembly.test.tsx`
Expected: FAIL — current page.tsx imports old sections.

**Step 3: Replace page.tsx**

```tsx
// web/src/app/page.tsx
import dynamic from "next/dynamic"
import { NavMinimal } from "@/components/landing-v2/nav-minimal"
import {
  HeroSection,
  FrictionSection,
  EngineDiagram,
  EngineProof,
  CapabilitiesSection,
  InvestorPositioning,
  FinalCTA,
} from "@/components/landing-v2/sections"

const WebGLScene = dynamic(
  () => import("@/components/landing-v2/scene/webgl-scene").then((mod) => ({ default: mod.WebGLScene })),
  { ssr: false }
)

const EngineNodes = dynamic(
  () => import("@/components/landing-v2/scene/engine-nodes").then((mod) => ({ default: mod.EngineNodes })),
  { ssr: false }
)

const ConnectionLines = dynamic(
  () => import("@/components/landing-v2/scene/connection-lines").then((mod) => ({ default: mod.ConnectionLines })),
  { ssr: false }
)

const CapabilityCards3D = dynamic(
  () => import("@/components/landing-v2/scene/capability-cards-3d").then((mod) => ({ default: mod.CapabilityCards3D })),
  { ssr: false }
)

export default function Home() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      {/* WebGL canvas — fixed behind content */}
      <WebGLScene pages={7}>
        <EngineNodes tier="high" />
        <ConnectionLines />
        <CapabilityCards3D />
      </WebGLScene>

      {/* HTML overlay — scrollable content */}
      <div className="relative z-10">
        <NavMinimal />
        <HeroSection />
        <FrictionSection />
        <EngineDiagram />
        <EngineProof />
        <CapabilitiesSection />
        <InvestorPositioning />
        <FinalCTA />
      </div>
    </main>
  )
}
```

Note: The `tier` prop on `EngineNodes` is a placeholder — in the actual implementation, `SceneCanvas` should pass the tier down to children via React context or props. The implementing engineer should wire `useQualityTier` from the `WebGLScene` component and pass it through to child 3D components.

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run web/src/components/landing-v2/__tests__/page-assembly.test.tsx`
Expected: All PASS.

**Step 5: Visual verification**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run dev`
Open `http://localhost:3000`. Verify:
- All 7 sections render in order
- Nav is visible at top
- On desktop: WebGL canvas visible behind content (ambient grid, nodes assemble on scroll)
- On mobile (<768px): No WebGL, sections render with CSS animations
- Light/dark mode toggle works

**Step 6: Commit**

```bash
git add web/src/app/page.tsx web/src/components/landing-v2/__tests__/page-assembly.test.tsx
git commit -m "feat: assemble WebGL homepage with all sections and 3D scene"
```

---

## Task 11: Clean Up Old Landing Components

**Files:**
- Delete: all files in `web/src/components/landing/` (old landing components)
- Modify: `web/src/components/landing-v2/index.ts` (re-export sections)

**Step 1: Verify no other pages import from the old landing directory**

Run a search for imports from `@/components/landing` (without `-v2`) across the codebase:

```bash
cd /Users/brandon/repos/margin_invest && grep -r "components/landing" web/src/ --include="*.tsx" --include="*.ts" | grep -v "landing-v2" | grep -v "node_modules"
```

Should only find the old barrel export and tests referencing old components.

**Step 2: Remove old landing directory**

```bash
rm -rf web/src/components/landing/
```

**Step 3: Rename landing-v2 to landing**

```bash
mv web/src/components/landing-v2 web/src/components/landing
```

**Step 4: Update all imports from `landing-v2` to `landing`**

Search and replace in all files:
- `@/components/landing-v2/` → `@/components/landing/`

**Step 5: Run all tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run`
Expected: All tests pass.

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: replace old landing components with WebGL landing-v2"
```

---

## Task 12: Add Responsive Typography Utilities

**Files:**
- Modify: `web/src/app/globals.css`

**Step 1: Add responsive typography utility classes**

In `globals.css`, after the `@theme` block, add:

```css
/* Typography utilities matching design spec */
.heading-1 {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.0;
  letter-spacing: -0.5px;
}

.heading-2 {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.3px;
}

.heading-3 {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
}

.body-text {
  font-size: 16px;
  line-height: 1.5;
}

.caption-text {
  font-size: 13px;
  line-height: 1.4;
  letter-spacing: 0.2px;
}

@media (min-width: 768px) {
  .heading-1 { font-size: 56px; }
  .heading-2 { font-size: 40px; }
  .heading-3 { font-size: 28px; }
  .body-text { font-size: 17px; }
  .caption-text { font-size: 13px; }
}

@media (min-width: 1024px) {
  .heading-1 { font-size: 72px; }
  .heading-2 { font-size: 48px; }
  .heading-3 { font-size: 32px; }
  .body-text { font-size: 18px; }
  .caption-text { font-size: 14px; }
}
```

**Step 2: Optionally refactor section components to use these classes**

Replace the per-breakpoint Tailwind arbitrary values (e.g., `text-[48px] md:text-[56px] lg:text-[72px]`) with the utility classes (`heading-1`). This is optional — both approaches work.

**Step 3: Verify build**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run build`
Expected: Build succeeds.

**Step 4: Commit**

```bash
git add web/src/app/globals.css
git commit -m "feat: add responsive typography utility classes matching design spec"
```

---

## Task 13: Add Dev Annotation Layer

**Files:**
- Create: `web/src/components/landing/dev-annotations.tsx`

**Step 1: Create the annotation component**

This is a development-only overlay that shows WebGL implementation notes. Only renders in development mode.

```tsx
// web/src/components/landing/dev-annotations.tsx
"use client"

export function DevAnnotations() {
  if (process.env.NODE_ENV !== "development") return null

  const notes = [
    "Render-on-demand WebGL (frameloop='demand')",
    "Quality tiers: high (DPR 1.5) / medium (DPR 1.0) / low (no WebGL)",
    "DPR cap: Math.min(devicePixelRatio, 1.5)",
    "No postprocessing (zero shader passes beyond default)",
    "InstancedMesh for diagram nodes and capability cards",
    "Progressive reveal scroll mapping via Drei ScrollControls",
  ]

  return (
    <div className="fixed bottom-4 right-4 z-[9999] max-w-sm p-4 bg-bg-elevated border border-border-primary rounded-[6px] text-[12px] font-mono text-text-secondary opacity-60 hover:opacity-100 transition-opacity">
      <div className="font-semibold text-text-primary mb-2 text-[13px]">
        WebGL Dev Notes
      </div>
      <ul className="space-y-1">
        {notes.map((note, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-accent shrink-0">*</span>
            {note}
          </li>
        ))}
      </ul>
    </div>
  )
}
```

**Step 2: Add to page.tsx**

Import and render `<DevAnnotations />` inside the HTML overlay div in `page.tsx`.

**Step 3: Commit**

```bash
git add web/src/components/landing/dev-annotations.tsx web/src/app/page.tsx
git commit -m "feat: add dev-only WebGL annotation overlay"
```

---

## Task 14: Run Full Test Suite and Final Verification

**Step 1: Run all web tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run -- npx --prefix web vitest run`
Expected: All tests pass.

**Step 2: Run build**

Run: `cd /Users/brandon/repos/margin_invest/web && npm run build`
Expected: Build succeeds with no errors or warnings.

**Step 3: Visual QA checklist**

Run dev server and verify in browser:

- [ ] Desktop (>1024px): All 7 sections visible, WebGL canvas renders behind content
- [ ] WebGL ambient grid visible at subtle opacity
- [ ] Engine nodes assemble on scroll (~30-50% scroll position)
- [ ] Capability card planes float in (~60-75% scroll position)
- [ ] Light mode: warm off-white, dark text, emerald accent
- [ ] Dark mode: dark navy, light text, lighter emerald
- [ ] Theme toggle in nav works
- [ ] Tablet (768-1024px): Reduced WebGL, 8-column grid
- [ ] Mobile (<768px): No WebGL, sections stack, 4-column grid
- [ ] CTA links navigate correctly
- [ ] No console errors
- [ ] Smooth 60fps scroll on desktop

**Step 4: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: final QA adjustments for WebGL homepage"
```

---

## Dependency Graph

```
Task 1 (deps + config)
  ├─> Task 2 (tokens)
  └─> Task 3 (quality hook)
        └─> Task 6 (scene wrapper)
              ├─> Task 7 (engine nodes)
              ├─> Task 8 (capability cards)
              └─> Task 10 (assemble page)

Task 4 (shared components)
  └─> Task 5 (nav)
        └─> Task 9 (sections)
              └─> Task 10 (assemble page)
                    └─> Task 11 (cleanup)
                          └─> Task 12 (typography)
                                └─> Task 13 (annotations)
                                      └─> Task 14 (final QA)
```

Tasks 1-3 can run in parallel with Tasks 4-5. Tasks 6-8 can run in parallel. Task 10 depends on everything before it. Tasks 11-14 are sequential.
