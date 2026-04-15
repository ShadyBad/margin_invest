"use client"

import Link from "next/link"
import { useEffect, useRef } from "react"
import { LogoIcon } from "@/components/ui/logo-icon"

const productLinks = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Explore", href: "/explore" },
  { label: "Methodology", href: "/methodology" },
  { label: "API", href: "/api-docs" },
  { label: "Status", href: "/status" },
]

const companyLinks = [
  { label: "About", href: "/about" },
  { label: "Legal", href: "/legal" },
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
  { label: "Contact", href: "/contact" },
]

export function FooterSection() {
  const footerRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!footerRef.current) return
    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const el = footerRef.current
      if (!el) return
      const content = el.querySelector("[data-footer-content]")
      if (!content) return
      gsap.set(content, { opacity: 0 })
      trigger = ScrollTrigger.create({ trigger: el, start: "top 90%", once: true,
        onEnter: () => { gsap.to(content, { opacity: 1, duration: 0.6, ease: "power2.out" }) },
      })
    }

    animate().catch(() => {})
    return () => { cancelled = true; trigger?.kill() }
  }, [])

  return (
    <footer id="footer" ref={footerRef} style={{ background: "var(--color-surface-container-lowest)" }}>
      <div data-footer-content className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr] gap-10">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <LogoIcon size={20} />
              <span className="text-headline-md" style={{ color: "var(--color-on-surface)", fontSize: "1.125rem" }}>Margin Invest</span>
            </div>
            <p className="text-sm max-w-xs leading-relaxed" style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-display)", fontStyle: "italic" }}>
              A deterministic capital allocation system. Structure replaces narrative.
            </p>
          </div>

          <div>
            <h4 className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>PRODUCT</h4>
            <nav className="flex flex-col gap-2">
              {productLinks.map((link) => (
                <Link key={link.label} href={link.href} className="text-sm transition-colors duration-150" style={{ color: "var(--color-on-surface-variant)" }}>{link.label}</Link>
              ))}
            </nav>
          </div>

          <div>
            <h4 className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>COMPANY</h4>
            <nav className="flex flex-col gap-2">
              {companyLinks.map((link) => (
                <Link key={link.label} href={link.href} className="text-sm transition-colors duration-150" style={{ color: "var(--color-on-surface-variant)" }}>{link.label}</Link>
              ))}
            </nav>
          </div>
        </div>

        <div className="mt-12 pt-6 flex flex-col md:flex-row justify-between items-center gap-3">
          <p className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>&copy; 2026 MARGIN INVEST</p>
          <p className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>DETERMINISTIC BY DESIGN.</p>
        </div>
      </div>
    </footer>
  )
}
