"use client"

import { useEffect, useRef } from "react"

interface ComparisonRow {
  feature: string
  motleyFool: string
  seekingAlpha: string
  zacks: string
  marginInvest: string
}

const ROWS: ComparisonRow[] = [
  {
    feature: "Human discretion",
    motleyFool: "Yes",
    seekingAlpha: "Yes",
    zacks: "Hidden",
    marginInvest: "None",
  },
  {
    feature: "Shows formulas",
    motleyFool: "No",
    seekingAlpha: "No",
    zacks: "No",
    marginInvest: "Every one",
  },
  {
    feature: "Explains eliminations",
    motleyFool: "N/A",
    seekingAlpha: "N/A",
    zacks: "No",
    marginInvest: "Every one",
  },
  {
    feature: "Deterministic output",
    motleyFool: "No",
    seekingAlpha: "No",
    zacks: "Unknown",
    marginInvest: "Guaranteed",
  },
  {
    feature: "Sector-neutral scoring",
    motleyFool: "No",
    seekingAlpha: "No",
    zacks: "Partial",
    marginInvest: "Yes",
  },
]

export function DifferentiatorSection() {
  const tableRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!tableRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = tableRef.current
      if (!el) return

      gsap.set(el, { opacity: 0, y: 24 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(el, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" })
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
    <section id="differentiator" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="font-display text-3xl md:text-4xl text-text-primary text-center mb-4">
          Other platforms have opinions.
        </h2>
        <p className="text-base text-text-secondary text-center mb-16 max-w-lg mx-auto">
          Analyst picks are opinions. Community ratings are opinions.
          Even &ldquo;quantitative&rdquo; tools that hide their work are injecting judgment you
          can&apos;t verify.
        </p>

        <div ref={tableRef} className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="text-left text-xs uppercase tracking-[0.15em] text-text-tertiary py-3 pr-4 w-[20%]">
                  &nbsp;
                </th>
                <th className="text-center text-xs uppercase tracking-[0.15em] text-text-tertiary py-3 px-2">
                  Motley Fool
                </th>
                <th className="text-center text-xs uppercase tracking-[0.15em] text-text-tertiary py-3 px-2">
                  Seeking Alpha
                </th>
                <th className="text-center text-xs uppercase tracking-[0.15em] text-text-tertiary py-3 px-2">
                  Zacks
                </th>
                <th className="text-center text-xs uppercase tracking-[0.15em] text-accent py-3 px-2">
                  Margin Invest
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.feature} className="border-b border-border-subtle">
                  <td className="text-left text-text-secondary py-3 pr-4 font-medium">
                    {row.feature}
                  </td>
                  <td className="text-center text-text-tertiary py-3 px-2">
                    {row.motleyFool}
                  </td>
                  <td className="text-center text-text-tertiary py-3 px-2">
                    {row.seekingAlpha}
                  </td>
                  <td className="text-center text-text-tertiary py-3 px-2">
                    {row.zacks}
                  </td>
                  <td className="text-center text-accent font-medium py-3 px-2">
                    {row.marginInvest}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
