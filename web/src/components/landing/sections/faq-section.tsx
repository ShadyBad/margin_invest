"use client"

import { useEffect, useRef, useState } from "react"
import { HeroSearch } from "../hero-search"
import { FAQ_ITEMS } from "@/data/faq-items"
import type { FaqEntry } from "@/data/faq-items"

export { FAQ_ITEMS }
export type { FaqEntry }

export function FaqItem({ item }: { item: FaqEntry }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border-b border-border-subtle" data-faq-item>
      <button
        type="button"
        className="w-full flex items-center justify-between py-5 text-left group"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="text-sm font-medium text-text-primary group-hover:text-accent transition-colors pr-4">
          {item.question}
        </span>
        <span
          className="text-text-tertiary shrink-0 transition-transform duration-200"
          style={{ transform: open ? "rotate(45deg)" : "rotate(0deg)" }}
          aria-hidden="true"
        >
          +
        </span>
      </button>
      <div
        className="grid transition-[grid-template-rows] duration-200 ease-out"
        style={{ gridTemplateRows: open ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <p className="text-sm text-text-secondary pb-5 pr-8 leading-relaxed">
            {item.answer}
          </p>
        </div>
      </div>
    </div>
  )
}

export function FaqSection() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    const triggers: { kill: () => void }[] = []

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      // Label fade-in
      const label = el.querySelector("[data-faq-label]")
      if (label) {
        gsap.set(label, { opacity: 0, y: 20 })
        triggers.push(
          ScrollTrigger.create({
            trigger: label,
            start: "top 90%",
            once: true,
            onEnter: () => {
              gsap.to(label, {
                opacity: 1,
                y: 0,
                duration: 0.5,
                ease: "power2.out",
              })
            },
          })
        )
      }

      // Staggered FAQ item reveals
      const items = el.querySelectorAll("[data-faq-item]")
      gsap.set(items, { opacity: 0, y: 12 })
      items.forEach((item, i) => {
        triggers.push(
          ScrollTrigger.create({
            trigger: item,
            start: "top 90%",
            once: true,
            onEnter: () => {
              gsap.to(item, {
                opacity: 1,
                y: 0,
                duration: 0.4,
                delay: i * 0.08,
                ease: "power2.out",
              })
            },
          })
        )
      })

      // Closing CTA fade-in
      const cta = el.querySelector("[data-faq-cta]")
      if (cta) {
        gsap.set(cta, { opacity: 0, y: 16 })
        triggers.push(
          ScrollTrigger.create({
            trigger: cta,
            start: "top 90%",
            once: true,
            onEnter: () => {
              gsap.to(cta, {
                opacity: 1,
                y: 0,
                duration: 0.5,
                ease: "power2.out",
              })
            },
          })
        )
      }
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      triggers.forEach((t) => t.kill())
    }
  }, [])

  return (
    <section id="faq" ref={sectionRef} className="py-16 px-6">
      <div className="max-w-3xl mx-auto">
        <p
          data-faq-label
          className="font-mono text-xs uppercase tracking-[0.18em] text-text-tertiary text-center mb-12"
        >
          Common Questions
        </p>
        <div>
          {FAQ_ITEMS.map((item) => (
            <FaqItem key={item.question} item={item} />
          ))}
        </div>

        {/* Closing CTA */}
        <div data-faq-cta className="mt-16 text-center">
          <h2 className="font-display text-2xl md:text-3xl text-text-primary mb-8">
            Score your first position.
          </h2>
          <HeroSearch />
        </div>
      </div>
    </section>
  )
}
