"use client"

import { useEffect, useRef, useState } from "react"
import { HeroSearch } from "./hero-search"

interface FaqEntry {
  question: string
  answer: string
}

const FAQ_ITEMS: FaqEntry[] = [
  {
    question: "What is Margin Invest?",
    answer:
      "A deterministic scoring engine that evaluates every US-listed equity using forensic elimination filters and multi-factor analysis. It has no analysts, no opinions, and no override button. Same inputs, same outputs, every time.",
  },
  {
    question: "Is this investment advice?",
    answer:
      "No. Margin Invest is an analytical tool, not a financial advisor. We don\u2019t make recommendations \u2014 we show you what the math says and let you decide. All scores are informational and educational. You are responsible for your own investment decisions.",
  },
  {
    question: "How is this different from Zacks or Morningstar?",
    answer:
      "Zacks shows you a rank. We show you the formula. Every score links to its calculation, every threshold is published, and every elimination is explained. You can verify any number with a spreadsheet and the same data sources. Transparency is the product.",
  },
  {
    question: "What are the elimination filters?",
    answer:
      "Six forensic screens including: Beneish M-Score (earnings manipulation detection), Altman Z-Score (bankruptcy probability), penny stock exclusion, delisting detection, minimum liquidity thresholds, and data sufficiency requirements. 70%+ of US equities fail at least one filter.",
  },
  {
    question: "What does \u201Csector-neutral\u201D mean?",
    answer:
      "We compare stocks to their sector peers, not to the entire market. A bank with 15% ROIC is excellent \u2014 among banks. A tech company with 15% ROIC is below average \u2014 among tech. Sector-neutral scoring prevents false comparisons.",
  },
  {
    question: "Do you have a track record?",
    answer:
      "We publish every score in real time with timestamps. You can track what the system scored highly and compare it to actual outcomes over time. We\u2019re building the track record live, in public, starting at launch.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      "Yes. Cancel in your account settings. Takes effect immediately. No penalties, no calls with a \u201Cretention specialist.\u201D",
  },
]

function FaqItem({ item }: { item: FaqEntry }) {
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
      {open && (
        <p className="text-sm text-text-secondary pb-5 pr-8 leading-relaxed">
          {item.answer}
        </p>
      )}
    </div>
  )
}

export function FaqSection() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false

    async function animate() {
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
      }

      // Staggered FAQ item reveals
      const items = el.querySelectorAll("[data-faq-item]")
      gsap.set(items, { opacity: 0, y: 12 })
      items.forEach((item, i) => {
        ScrollTrigger.create({
          trigger: item,
          start: `top ${90 - i * 0}%`,
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
      })

      // Closing CTA fade-in
      const cta = el.querySelector("[data-faq-cta]")
      if (cta) {
        gsap.set(cta, { opacity: 0, y: 16 })
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
      }
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
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
