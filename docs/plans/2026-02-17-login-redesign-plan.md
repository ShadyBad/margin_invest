# Login Page Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the flat login page with a glassmorphism card floating over a WebGL "Liquidity Flow" background, with icon-only OAuth buttons and a collapsible credentials form.

**Architecture:** Three new components — `LoginScene` (R3F WebGL background loaded via `next/dynamic`), `LoginCard` (glass card with OAuth icons + expandable credentials), and a rewritten `page.tsx` that composes them. The old `login-buttons.tsx` is deleted. CSS `@keyframes` handle page-load animation. No framer-motion.

**Tech Stack:** Next.js 15, React 19, Tailwind CSS 4, Three.js / @react-three/fiber, next-auth

---

### Task 1: LoginCard Component — OAuth Icons & Shell

**Files:**
- Create: `web/src/components/login/login-card.tsx`

**Step 1: Create the component**

This is the glassmorphism card with logo, heading, OAuth icon row, divider, email toggle, and footer. Credentials form expansion is Task 2.

```tsx
"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import Link from "next/link"

function LogoIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 20 20"
      fill="none"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      stroke="currentColor"
      aria-hidden="true"
    >
      <polyline points="2,16 6,6 10,12 14,4 18,16" />
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  )
}

function AppleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.32 2.32-2.11 4.45-3.74 4.25z" />
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}

function EyeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  )
}

export function LoginCard() {
  const [showCredentials, setShowCredentials] = useState(false)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  const handleCredentialsSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    signIn("credentials", {
      username: email,
      password,
      callbackUrl: "/dashboard",
    })
  }

  return (
    <div className="login-card-enter w-[calc(100%-32px)] max-w-[420px] rounded-3xl border border-white/[0.06] bg-[rgba(17,17,19,0.6)] px-8 py-10 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-[16px] backdrop-saturate-[1.2] max-md:px-6 max-md:py-8">
      {/* Logo */}
      <div className="flex justify-center mb-6 text-text-primary opacity-80">
        <LogoIcon />
      </div>

      {/* Heading */}
      <h1 className="text-xl font-semibold tracking-[-0.02em] text-text-primary text-center mb-2">
        Sign in to Margin Invest
      </h1>
      <p className="text-[13px] text-text-secondary text-center mb-8">
        Secure login with bank-grade encryption
      </p>

      {/* OAuth Icons */}
      <div className="flex justify-center gap-4 mb-6">
        <button
          onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
          className="flex items-center justify-center w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.06] text-text-primary hover:bg-white/[0.08] hover:scale-105 transition-all duration-200 ease-out"
          aria-label="Sign in with Google"
        >
          <GoogleIcon />
        </button>
        <button
          disabled
          className="flex items-center justify-center w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.06] text-text-primary opacity-40 cursor-not-allowed"
          aria-label="Sign in with Apple (coming soon)"
          aria-disabled="true"
        >
          <AppleIcon />
        </button>
        <button
          onClick={() => signIn("github", { callbackUrl: "/dashboard" })}
          className="flex items-center justify-center w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.06] text-text-primary hover:bg-white/[0.08] hover:scale-105 transition-all duration-200 ease-out"
          aria-label="Sign in with GitHub"
        >
          <GitHubIcon />
        </button>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex-1 h-px bg-white/[0.06]" />
        <span className="text-[12px] font-normal tracking-[0.05em] uppercase text-text-secondary">or</span>
        <div className="flex-1 h-px bg-white/[0.06]" />
      </div>

      {/* Credentials toggle + form */}
      <div className="grid transition-[grid-template-rows] duration-300 ease-out" style={{ gridTemplateRows: showCredentials ? "1fr" : "0fr" }}>
        <div className="overflow-hidden">
          <form onSubmit={handleCredentialsSubmit} className="flex flex-col gap-4 pb-1">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-[13px] font-medium text-text-secondary">
                Email
              </label>
              <input
                id="email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
                placeholder="you@example.com"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="password" className="text-[13px] font-medium text-text-secondary">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 pr-11 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors duration-200"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              className="h-12 w-full rounded-xl bg-accent text-white text-[15px] font-semibold hover:brightness-110 active:scale-[0.98] transition-all duration-150 ease-out"
            >
              Sign In
            </button>
          </form>
        </div>
      </div>

      {/* Toggle link */}
      <button
        type="button"
        onClick={() => setShowCredentials(!showCredentials)}
        className="w-full text-center text-[13px] font-medium text-text-secondary hover:text-text-primary transition-colors duration-200 mb-6"
      >
        {showCredentials ? "Back to social login" : "Continue with email"}
      </button>

      {/* Footer */}
      <p className="text-[13px] text-text-secondary text-center">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-accent hover:underline">
          Create one
        </Link>
      </p>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/components/login/login-card.tsx
git commit -m "feat(web): add LoginCard glassmorphism component"
```

---

### Task 2: LoginCard Tests

**Files:**
- Create: `web/src/components/login/__tests__/login-card.test.tsx`

**Step 1: Write tests**

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { LoginCard } from "../login-card"

const { mockSignIn } = vi.hoisted(() => ({
  mockSignIn: vi.fn(),
}))

vi.mock("next-auth/react", () => ({
  signIn: mockSignIn,
}))

describe("LoginCard", () => {
  beforeEach(() => {
    mockSignIn.mockClear()
  })

  describe("structure", () => {
    it("renders the heading", () => {
      render(<LoginCard />)
      expect(screen.getByRole("heading", { name: /sign in to margin invest/i })).toBeInTheDocument()
    })

    it("renders the security subtext", () => {
      render(<LoginCard />)
      expect(screen.getByText(/secure login with bank-grade encryption/i)).toBeInTheDocument()
    })

    it("renders the register link", () => {
      render(<LoginCard />)
      const link = screen.getByRole("link", { name: /create one/i })
      expect(link).toHaveAttribute("href", "/register")
    })
  })

  describe("OAuth icons", () => {
    it("renders Google, Apple, and GitHub buttons", () => {
      render(<LoginCard />)
      expect(screen.getByLabelText("Sign in with Google")).toBeInTheDocument()
      expect(screen.getByLabelText(/sign in with apple/i)).toBeInTheDocument()
      expect(screen.getByLabelText("Sign in with GitHub")).toBeInTheDocument()
    })

    it("calls signIn with google on Google click", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByLabelText("Sign in with Google"))
      expect(mockSignIn).toHaveBeenCalledWith("google", { callbackUrl: "/dashboard" })
    })

    it("calls signIn with github on GitHub click", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByLabelText("Sign in with GitHub"))
      expect(mockSignIn).toHaveBeenCalledWith("github", { callbackUrl: "/dashboard" })
    })

    it("Apple button is disabled", () => {
      render(<LoginCard />)
      const appleBtn = screen.getByLabelText(/sign in with apple/i)
      expect(appleBtn).toBeDisabled()
      expect(appleBtn).toHaveAttribute("aria-disabled", "true")
    })

    it("Apple button does not call signIn", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByLabelText(/sign in with apple/i))
      expect(mockSignIn).not.toHaveBeenCalled()
    })
  })

  describe("credentials form", () => {
    it("does not show email input by default", () => {
      render(<LoginCard />)
      expect(screen.queryByLabelText(/email/i)).not.toBeVisible()
    })

    it("shows credentials form when 'Continue with email' is clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      expect(screen.getByLabelText(/email/i)).toBeVisible()
      expect(screen.getByLabelText(/password/i)).toBeVisible()
    })

    it("toggles text to 'Back to social login' when expanded", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      expect(screen.getByText("Back to social login")).toBeInTheDocument()
    })

    it("submits credentials with signIn", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      await user.type(screen.getByLabelText(/email/i), "testuser")
      await user.type(screen.getByLabelText(/password/i), "testpass123")
      await user.click(screen.getByRole("button", { name: /^sign in$/i }))
      expect(mockSignIn).toHaveBeenCalledWith("credentials", {
        username: "testuser",
        password: "testpass123",
        callbackUrl: "/dashboard",
      })
    })

    it("toggles password visibility", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      const passwordInput = screen.getByLabelText(/password/i)
      expect(passwordInput).toHaveAttribute("type", "password")
      await user.click(screen.getByLabelText("Show password"))
      expect(passwordInput).toHaveAttribute("type", "text")
      await user.click(screen.getByLabelText("Hide password"))
      expect(passwordInput).toHaveAttribute("type", "password")
    })
  })
})
```

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`

Expected: All tests pass. The `not.toBeVisible()` test relies on the `grid-template-rows: 0fr` + `overflow-hidden` collapsing the form content to zero height. If this doesn't work in jsdom, change the assertion to check that the grid container has `gridTemplateRows: "0fr"` via style attribute instead.

**Step 3: Commit**

```bash
git add web/src/components/login/__tests__/login-card.test.tsx
git commit -m "test(web): add LoginCard tests"
```

---

### Task 3: WebGL LoginScene Component

**Files:**
- Create: `web/src/components/login/login-scene.tsx`

**Step 1: Create the WebGL scene**

This is a lightweight R3F scene with shader-based gradient orbs and drifting particles. Loaded via `next/dynamic` with `ssr: false`.

```tsx
"use client"

import dynamic from "next/dynamic"

const LoginCanvas = dynamic(() => import("./login-canvas").then((mod) => ({ default: mod.LoginCanvas })), {
  ssr: false,
})

export function LoginScene() {
  return <LoginCanvas />
}
```

Create the canvas component at `web/src/components/login/login-canvas.tsx`:

```tsx
"use client"

import { Canvas, useFrame } from "@react-three/fiber"
import { useMemo, useRef } from "react"
import * as THREE from "three"

// Simplex noise GLSL (inline to avoid dependencies)
const noiseGlsl = `
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
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
  i = mod289(i);
  vec4 p = permute(permute(permute(
    i.z + vec4(0.0, i1.z, i2.z, 1.0))
    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
    + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
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
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}
`

function GradientOrbs() {
  const meshRef = useRef<THREE.Mesh>(null)
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColor1: { value: new THREE.Color("#0A1628") },
      uColor2: { value: new THREE.Color("#0D3B4F") },
      uColor3: { value: new THREE.Color("#121830") },
      uColor4: { value: new THREE.Color("#2A1A0E") },
    }),
    []
  )

  useFrame((_, delta) => {
    uniforms.uTime.value += delta * 0.15
  })

  return (
    <mesh ref={meshRef} position={[0, 0, -2]}>
      <planeGeometry args={[16, 10, 1, 1]} />
      <shaderMaterial
        uniforms={uniforms}
        vertexShader={`
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `}
        fragmentShader={`
          ${noiseGlsl}
          uniform float uTime;
          uniform vec3 uColor1;
          uniform vec3 uColor2;
          uniform vec3 uColor3;
          uniform vec3 uColor4;
          varying vec2 vUv;
          void main() {
            vec2 uv = vUv;
            float n1 = snoise(vec3(uv * 1.5 + uTime * 0.3, uTime * 0.1)) * 0.5 + 0.5;
            float n2 = snoise(vec3(uv * 2.0 - uTime * 0.2, uTime * 0.15 + 10.0)) * 0.5 + 0.5;
            float n3 = snoise(vec3(uv * 1.0 + uTime * 0.1, uTime * 0.08 + 20.0)) * 0.5 + 0.5;
            vec3 color = mix(uColor1, uColor2, n1);
            color = mix(color, uColor3, n2 * 0.6);
            color = mix(color, uColor4, n3 * 0.15);
            // Radial vignette — darken edges, light center
            float vignette = 1.0 - smoothstep(0.2, 0.9, length(uv - 0.5) * 1.4);
            color *= 0.6 + vignette * 0.4;
            gl_FragColor = vec4(color, 1.0);
          }
        `}
      />
    </mesh>
  )
}

function Particles() {
  const pointsRef = useRef<THREE.Points>(null)
  const count = 50

  const { positions, speeds } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const spd = new Float32Array(count)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 14
      pos[i * 3 + 1] = (Math.random() - 0.5) * 10
      pos[i * 3 + 2] = -1 + Math.random() * -1
      spd[i] = 0.3 + Math.random() * 0.5
    }
    return { positions: pos, speeds: spd }
  }, [])

  useFrame((state, delta) => {
    if (!pointsRef.current) return
    const posArray = pointsRef.current.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      posArray[i * 3 + 1] += speeds[i] * delta * 0.5
      posArray[i * 3] += Math.sin(state.clock.elapsedTime * 0.5 + i) * delta * 0.05
      // Reset particle when it goes above viewport
      if (posArray[i * 3 + 1] > 5.5) {
        posArray[i * 3 + 1] = -5.5
        posArray[i * 3] = (Math.random() - 0.5) * 14
      }
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.03} color="#4A6A7A" transparent opacity={0.25} sizeAttenuation />
    </points>
  )
}

export function LoginCanvas() {
  return (
    <Canvas
      dpr={[1, 1.5]}
      frameloop="always"
      gl={{ antialias: false, alpha: false, powerPreference: "low-power" }}
      camera={{ position: [0, 0, 5], fov: 50 }}
      className="login-scene-enter"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
      }}
      aria-hidden="true"
    >
      <GradientOrbs />
      <Particles />
    </Canvas>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/components/login/login-scene.tsx web/src/components/login/login-canvas.tsx
git commit -m "feat(web): add WebGL LoginScene with gradient orbs and particles"
```

---

### Task 4: Rewrite Login Page

**Files:**
- Modify: `web/src/app/login/page.tsx`

**Step 1: Rewrite the page**

Replace the entire contents of `web/src/app/login/page.tsx`:

```tsx
import type { Metadata } from "next"
import { LoginScene } from "@/components/login/login-scene"
import { LoginCard } from "@/components/login/login-card"

export const metadata: Metadata = {
  title: "Sign In | Margin Invest",
  description: "Sign in to your Margin Invest account.",
}

export default function LoginPage() {
  return (
    <div className="relative min-h-screen flex items-center justify-center bg-bg-primary overflow-hidden">
      <LoginScene />
      <div className="relative z-10">
        <LoginCard />
      </div>
    </div>
  )
}
```

**Step 2: Add CSS keyframes to globals.css**

Add these keyframes at the end of `web/src/app/globals.css` (inside the existing file, after all other rules):

```css
@keyframes login-card-enter {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes login-scene-enter {
  from { opacity: 0; }
  to { opacity: 1; }
}

.login-card-enter {
  animation: login-card-enter 500ms ease-out 100ms both;
}

.login-scene-enter {
  animation: login-scene-enter 800ms ease-out both;
}

@media (prefers-reduced-motion: reduce) {
  .login-card-enter,
  .login-scene-enter {
    animation: none;
  }
}
```

**Step 3: Update the page test**

Replace `web/src/app/login/__tests__/page.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import LoginPage from "../page"

// Mock the client components
vi.mock("@/components/login/login-scene", () => ({
  LoginScene: () => <div data-testid="login-scene">Mocked LoginScene</div>,
}))

vi.mock("@/components/login/login-card", () => ({
  LoginCard: () => <div data-testid="login-card">Mocked LoginCard</div>,
}))

describe("Login Page", () => {
  it("renders the LoginCard component", () => {
    render(<LoginPage />)
    expect(screen.getByTestId("login-card")).toBeInTheDocument()
  })

  it("renders the LoginScene component", () => {
    render(<LoginPage />)
    expect(screen.getByTestId("login-scene")).toBeInTheDocument()
  })
})
```

**Step 4: Run tests**

Run: `cd web && npx vitest run src/app/login/__tests__/ src/components/login/__tests__/`

Expected: All tests pass.

**Step 5: Commit**

```bash
git add web/src/app/login/page.tsx web/src/app/globals.css web/src/app/login/__tests__/page.test.tsx
git commit -m "feat(web): rewrite login page with glassmorphism card over WebGL"
```

---

### Task 5: Delete Old Login Components

**Files:**
- Delete: `web/src/app/login/login-buttons.tsx`
- Delete: `web/src/app/login/__tests__/login-buttons.test.tsx`

**Step 1: Delete the files**

```bash
rm web/src/app/login/login-buttons.tsx
rm web/src/app/login/__tests__/login-buttons.test.tsx
```

**Step 2: Run full test suite**

Run: `cd web && npx vitest run`

Expected: All tests pass. No remaining imports reference the deleted files.

**Step 3: Check for stale references**

Run: `grep -r "login-buttons\|LoginButtons" web/src/ --include="*.tsx" --include="*.ts"`

Expected: No matches.

**Step 4: Commit**

```bash
git add -A web/src/app/login/login-buttons.tsx web/src/app/login/__tests__/login-buttons.test.tsx
git commit -m "refactor(web): delete old LoginButtons component"
```

---

### Task 6: Final Verification

**Step 1: Run full web test suite**

Run: `cd web && npx vitest run`

Expected: All tests pass.

**Step 2: Check for TypeScript errors**

Run: `cd web && npx tsc --noEmit 2>&1 | grep -i "login" || echo "No login errors"`

Expected: No login-related errors.

**Step 3: Visual check**

Run: `cd web && npm run dev`

Visit `http://localhost:3000/login` and verify:
- WebGL background animates (slow gradient orbs, drifting particles)
- Glass card fades in with upward slide
- Logo, heading, subtext visible
- Three OAuth icons: Google and GitHub clickable, Apple grayed out
- "Continue with email" expands credentials form
- Password eye toggle works
- "Back to social login" collapses form
- "Create one" links to /register
