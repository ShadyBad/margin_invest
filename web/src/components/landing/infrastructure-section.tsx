"use client"

import { useEffect, useRef } from "react"

interface BulletItem {
  icon: React.ReactNode
  text: string
}

const FileIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 2h8l4 4v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1Z" />
    <path d="M12 2v4h4" />
  </svg>
)

const RefreshIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 10a7 7 0 0 1-12.9 3.7" />
    <path d="M3 10a7 7 0 0 1 12.9-3.7" />
    <polyline points="17 4 17 10 11 10" />
    <polyline points="3 16 3 10 9 10" />
  </svg>
)

const LockIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="5" y="9" width="10" height="8" rx="1" />
    <path d="M7 9V6a3 3 0 0 1 6 0v3" />
  </svg>
)

const CalculatorIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="2" width="14" height="16" rx="2" />
    <rect x="6" y="5" width="8" height="3" rx="0.5" />
    <circle cx="7" cy="12" r="0.5" fill="currentColor" />
    <circle cx="10" cy="12" r="0.5" fill="currentColor" />
    <circle cx="13" cy="12" r="0.5" fill="currentColor" />
    <circle cx="7" cy="15" r="0.5" fill="currentColor" />
    <circle cx="10" cy="15" r="0.5" fill="currentColor" />
    <circle cx="13" cy="15" r="0.5" fill="currentColor" />
  </svg>
)

const EyeIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 10s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" />
    <circle cx="10" cy="10" r="3" />
  </svg>
)

const bullets: BulletItem[] = [
  { icon: <FileIcon />, text: "SEC Filings + Earnings Transcripts" },
  { icon: <RefreshIcon />, text: "Market Data Feeds (Daily Refresh)" },
  { icon: <LockIcon />, text: "Encrypted API Key Storage" },
  { icon: <CalculatorIcon />, text: "Deterministic, Audit-Friendly Scoring" },
  { icon: <EyeIcon />, text: "No Hidden Heuristics" },
]

export function InfrastructureSection() {
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!gridRef.current) return

    let cancelled = false
    const triggers: { kill: () => void }[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = gridRef.current
      if (!el) return

      const children = Array.from(el.children) as HTMLElement[]
      children.forEach((child) => gsap.set(child, { opacity: 0, y: 16 }))

      const trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          children.forEach((child, i) => {
            gsap.to(child, {
              opacity: 1,
              y: 0,
              duration: 0.5,
              delay: i * 0.1,
              ease: "power2.out",
            })
          })
        },
      })
      triggers.push(trigger)
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      triggers.forEach((t) => t.kill())
    }
  }, [])

  return (
    <section id="infrastructure" className="py-[100px] px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="font-display text-4xl md:text-[36px] text-center mb-4" style={{ color: 'var(--color-accent-warm)' }}>
          Institutional-Grade Infrastructure
        </h2>
        <p className="text-text-secondary text-center mb-16">
          Built on verified public data and deterministic scoring architecture.
        </p>
        <div
          ref={gridRef}
          className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6"
        >
          {bullets.map((bullet) => (
            <div
              key={bullet.text}
              className="flex items-center gap-4 py-4 border-b border-border-subtle"
            >
              <span className="text-text-tertiary shrink-0">
                {bullet.icon}
              </span>
              <span className="text-sm text-text-secondary">
                {bullet.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
