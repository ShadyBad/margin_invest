"use client"

import { useEffect, useRef } from "react"

const ROWS = [
  { label: "Scoring", us: "Sector-neutral percentiles", screeners: "Absolute filters", blackbox: "Opaque composite" },
  { label: "Transparency", us: "Every formula documented", screeners: "Filter-based", blackbox: "Hidden methodology" },
  { label: "Filters", us: "6 forensic (Beneish, Altman)", screeners: "Price/volume only", blackbox: "None" },
  { label: "Auditability", us: "Spreadsheet-verifiable", screeners: "Limited", blackbox: "None" },
  { label: "Bias", us: "Deterministic, zero discretion", screeners: "User-configured", blackbox: "Analyst opinions" },
]

export function ComparisonSection() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const el = sectionRef.current
      if (!el) return
      const rows = el.querySelectorAll("[data-comparison-row]")
      if (rows.length === 0) return
      gsap.set(rows, { opacity: 0, y: 16, filter: "blur(4px)" })
      trigger = ScrollTrigger.create({ trigger: el, start: "top 82%", once: true,
        onEnter: () => { gsap.to(rows, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.5, stagger: 0.08, ease: "power2.out" }) },
      })
    }

    animate().catch(() => {})
    return () => { cancelled = true; trigger?.kill() }
  }, [])

  return (
    <section ref={sectionRef} className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-headline-md uppercase text-center mb-12" style={{ color: "var(--color-on-surface)" }}>
          How We Compare
        </h2>

        {/* Desktop */}
        <div className="hidden md:block rounded-lg overflow-hidden" style={{ border: "1px solid var(--color-ghost-border)" }}>
          <table className="w-full text-left">
            <caption className="sr-only">Comparison of Margin Invest vs Screeners vs Black Box platforms</caption>
            <thead>
              <tr style={{ background: "var(--color-surface-container)" }}>
                <th scope="col" className="px-6 py-4 text-label-sm w-1/6" style={{ color: "var(--color-on-surface-variant)" }} />
                <th scope="col" className="px-6 py-4 text-label-sm w-[28%]" style={{ color: "var(--color-primary)", background: "var(--color-surface-container-high)" }}>MARGIN INVEST</th>
                <th scope="col" className="px-6 py-4 text-label-sm w-[28%]" style={{ color: "var(--color-on-surface-variant)" }}>SCREENERS</th>
                <th scope="col" className="px-6 py-4 text-label-sm w-[28%]" style={{ color: "var(--color-on-surface-variant)" }}>BLACK BOX</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row, i) => (
                <tr key={row.label} data-comparison-row style={{ background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-surface-container-lowest)" }}>
                  <th scope="row" className="px-6 py-4 text-sm font-medium" style={{ color: "var(--color-on-surface)" }}>{row.label}</th>
                  <td className="px-6 py-4 text-sm" style={{ color: "var(--color-on-surface)", background: i % 2 === 0 ? "var(--color-surface-container-high)" : "rgba(22, 50, 32, 0.6)" }}>{row.us}</td>
                  <td className="px-6 py-4 text-sm" style={{ color: "var(--color-text-tertiary)" }}>{row.screeners}</td>
                  <td className="px-6 py-4 text-sm" style={{ color: "var(--color-text-tertiary)" }}>{row.blackbox}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile cards */}
        <div className="md:hidden flex flex-col gap-4">
          {ROWS.map((row) => (
            <div key={row.label} data-comparison-row className="p-5 rounded-lg" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
              <div className="text-label-sm mb-3" style={{ color: "var(--color-on-surface-variant)" }}>{row.label.toUpperCase()}</div>
              <div className="flex flex-col gap-2">
                <div>
                  <span className="text-label-sm" style={{ color: "var(--color-primary)" }}>MARGIN INVEST</span>
                  <p className="text-sm mt-0.5" style={{ color: "var(--color-on-surface)" }}>{row.us}</p>
                </div>
                <div>
                  <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>SCREENERS</span>
                  <p className="text-sm mt-0.5" style={{ color: "var(--color-text-tertiary)" }}>{row.screeners}</p>
                </div>
                <div>
                  <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>BLACK BOX</span>
                  <p className="text-sm mt-0.5" style={{ color: "var(--color-text-tertiary)" }}>{row.blackbox}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
