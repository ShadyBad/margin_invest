"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { AccountPillNav } from "./account-pill-nav"
import { ProfileSection } from "./profile-section"
import { SecuritySection } from "./security-section"
import { BillingSection } from "./billing-section"

const SECTIONS = ["Profile", "Security", "Billing", "Preferences"] as const

export function AccountPageClient() {
  const [activeSection, setActiveSection] = useState<string>("Profile")
  const sectionRefs = useRef<Map<string, HTMLElement>>(new Map())
  const containerRef = useRef<HTMLDivElement>(null)

  const registerRef = useCallback((section: string, el: HTMLElement | null) => {
    if (el) {
      sectionRefs.current.set(section, el)
    } else {
      sectionRefs.current.delete(section)
    }
  }, [])

  // IntersectionObserver to track active section
  useEffect(() => {
    const observers: IntersectionObserver[] = []

    for (const [section, el] of sectionRefs.current.entries()) {
      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              setActiveSection(section)
            }
          }
        },
        { rootMargin: "-20% 0px -70% 0px" }
      )
      observer.observe(el)
      observers.push(observer)
    }

    return () => {
      for (const obs of observers) obs.disconnect()
    }
  }, [])

  // GSAP stagger entrance animation
  useEffect(() => {
    if (!containerRef.current) return

    let cancelled = false

    async function animate() {
      const gsapModule = await import("gsap")
      if (cancelled) return
      const gsap = gsapModule.default
      const sections = containerRef.current?.querySelectorAll("[data-account-section]")
      if (!sections?.length) return

      gsap.set(sections, { opacity: 0, y: 16 })
      gsap.to(sections, {
        opacity: 1,
        y: 0,
        duration: 0.4,
        ease: "power2.out",
        stagger: 0.08,
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
    }
  }, [])

  function handleNavigate(section: string) {
    const el = sectionRefs.current.get(section)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  return (
    <div ref={containerRef}>
      <h1 className="text-4xl font-bold text-text-primary mb-2">Account</h1>
      <p className="text-sm text-text-secondary mb-8">
        Manage your profile, security, and billing settings.
      </p>

      <div className="md:grid md:grid-cols-[160px_1fr] md:gap-8">
        <div className="hidden md:block">
          <AccountPillNav
            sections={[...SECTIONS]}
            activeSection={activeSection}
            onNavigate={handleNavigate}
          />
        </div>

        <div className="space-y-8">
        <div data-account-section ref={(el) => registerRef("Profile", el)}>
          <ProfileSection />
        </div>
        <div data-account-section ref={(el) => registerRef("Security", el)}>
          <SecuritySection />
        </div>
        <div data-account-section ref={(el) => registerRef("Billing", el)}>
          <BillingSection />
        </div>
        <div data-account-section ref={(el) => registerRef("Preferences", el)}>
          <section id="preferences" className="terminal-card p-6 md:p-8">
            <h2 className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-6">
              Preferences
            </h2>
            <p className="text-sm text-text-secondary">
              Product preferences coming soon.
            </p>
          </section>
        </div>
        </div>
      </div>
    </div>
  )
}
