"use client"

import Link from "next/link"
import { useEffect, useRef } from "react"
import { FAQ_ITEMS, FaqItem } from "./faq-section"
import { HeroSearch } from "../hero-search"

const productLinks = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Guides", href: "/guides" },
  { label: "Methodology", href: "/methodology" },
  { label: "API", href: "/api-docs" },
  { label: "Status", href: "/status" },
]

const companyLinks = [
  { label: "Legal", href: "/legal" },
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
  { label: "Security", href: "/security" },
  { label: "Contact", href: "/contact" },
  { label: "Support", href: "/support" },
]

export function FooterSection() {
  const footerRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!footerRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
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
      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 90%",
        once: true,
        onEnter: () => {
          gsap.to(content, {
            opacity: 1,
            duration: 0.6,
            ease: "power2.out",
          })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [])

  return (
    <footer id="footer" ref={footerRef}>
      <hr className="border-border-subtle" />
      <div data-footer-content>
        {/* CTA section */}
        <div className="max-w-3xl mx-auto px-6 pt-16 pb-12 text-center" data-footer-cta>
          <h2
            className="font-display text-text-primary mb-8"
            style={{ fontSize: "clamp(28px, 4vw, 40px)" }}
          >
            Score your first position.
          </h2>
          <HeroSearch />
        </div>

        {/* FAQ accordion */}
        <div className="max-w-3xl mx-auto px-6 pb-12" data-footer-faq>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-text-tertiary text-center mb-8">
            Common Questions
          </p>
          <div>
            {FAQ_ITEMS.map((item) => (
              <FaqItem key={item.question} item={item} />
            ))}
          </div>
        </div>

        {/* Main footer */}
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr] gap-10">
            {/* Brand column */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="font-display text-lg text-text-primary">Margin Invest</span>
              </div>
              <p className="text-sm text-text-secondary max-w-xs leading-relaxed mb-4">
                A deterministic capital allocation system. Structure replaces narrative. Math
                replaces opinion.
              </p>
              <div className="font-mono text-xs text-text-tertiary">
                Deterministic scoring engine
              </div>
            </div>

            {/* Product column */}
            <div>
              <h4 className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Product
              </h4>
              <nav className="flex flex-col gap-2">
                {productLinks.map((link) => (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-100"
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
            </div>

            {/* Company column */}
            <div>
              <h4 className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Company
              </h4>
              <nav className="flex flex-col gap-2">
                {companyLinks.map((link) => (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-100"
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>

          {/* Bottom bar */}
          <div className="mt-10 pt-6 border-t border-border-subtle flex flex-col md:flex-row justify-between items-center gap-3">
            <p className="text-xs text-text-tertiary">
              &copy; 2026 Margin Invest. All rights reserved.
            </p>
            <p className="text-xs font-mono text-text-tertiary">
              Built on verified public data and deterministic scoring architecture.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
