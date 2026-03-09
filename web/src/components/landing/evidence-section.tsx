"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import { ProofSelectivityFunnel } from "./proof-selectivity-funnel"
import { ProofSectorChart } from "./proof-sector-chart"
import { ProofHeatmap } from "./proof-heatmap"
import type { CandidateCard } from "./types"
import { useScrollCanvas } from "./scroll-canvas"

interface EvidenceSectionProps {
  candidates?: CandidateCard[]
}

const HEADER_TEXT = "SYSTEM OUTPUT — Current Scoring Cycle"

export function EvidenceSection({ candidates = [] }: EvidenceSectionProps) {
  const { isSmoothScrolling } = useScrollCanvas()
  const sectionRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const headerRef = useRef<HTMLSpanElement>(null)
  const col1Ref = useRef<HTMLDivElement>(null)
  const col2Ref = useRef<HTMLDivElement>(null)
  const col3Ref = useRef<HTMLDivElement>(null)
  const divider1Ref = useRef<HTMLDivElement>(null)
  const divider2Ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current || !panelRef.current) return

    let cancelled = false
    const cleanups: (() => void)[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const panel = panelRef.current
      const header = headerRef.current
      const col1 = col1Ref.current
      const col2 = col2Ref.current
      const col3 = col3Ref.current
      const div1 = divider1Ref.current
      const div2 = divider2Ref.current
      if (!panel || !header || !col1 || !col2 || !col3 || !div1 || !div2) return

      // ── Mobile / no-smooth path: simple viewport-enter fade-in ──
      if (!isSmoothScrolling) {
        // Show everything immediately with a batch fade-in on viewport enter
        const charSpans = header.querySelectorAll<HTMLSpanElement>(".char-span")
        gsap.set(charSpans, { opacity: 1 })
        gsap.set(div1, { scaleY: 1 })
        gsap.set(div2, { scaleY: 1 })

        // Simple fade-in for the entire panel when it enters viewport
        gsap.set(panel, { opacity: 0, y: 30 })

        const st = ScrollTrigger.create({
          trigger: sectionRef.current,
          start: "top 80%",
          once: true,
          onEnter: () => {
            gsap.to(panel, {
              opacity: 1,
              y: 0,
              duration: 0.8,
              ease: "power2.out",
            })
            // Stagger the columns slightly
            gsap.to([col1, col2, col3], {
              opacity: 1,
              duration: 0.6,
              stagger: 0.15,
              delay: 0.3,
              ease: "power2.out",
            })
          },
        })

        cleanups.push(() => st.kill())
        return
      }

      // ── Desktop / smooth-scroll path: pinned sequential reveal ──

      // Initial states
      gsap.set(panel, { opacity: 0 })
      const charSpans = header.querySelectorAll<HTMLSpanElement>(".char-span")
      gsap.set(charSpans, { opacity: 0 })
      gsap.set(col1, { opacity: 0 })
      gsap.set(col2, { opacity: 0 })
      gsap.set(col3, { opacity: 0 })
      gsap.set(div1, { scaleY: 0, transformOrigin: "top" })
      gsap.set(div2, { scaleY: 0, transformOrigin: "top" })

      // Build the master timeline
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: "+=200%",
          pin: true,
          scrub: 0.5,
          anticipatePin: 1,
        },
      })

      // Phase 1: Container assembly (0-10%)
      // Panel fades in
      tl.to(panel, { opacity: 1, duration: 4, ease: "power2.out" }, 0)
      // Header chars type in with stagger
      tl.to(charSpans, { opacity: 1, duration: 0.5, stagger: 0.15, ease: "none" }, 2)

      // Phase 2: Column 1 — Funnel (10-40%)
      tl.to(col1, { opacity: 1, duration: 8, ease: "power2.out" }, 10)

      // Phase 3: Divider 1 (40-42%)
      tl.to(div1, { scaleY: 1, duration: 2, ease: "power2.inOut" }, 40)

      // Phase 4: Column 2 — Sectors (42-70%)
      tl.to(col2, { opacity: 1, duration: 8, ease: "power2.out" }, 42)
      // Dim column 1 slightly
      tl.to(col1, { opacity: 0.7, duration: 8, ease: "power2.out" }, 42)

      // Phase 5: Divider 2 (70-72%)
      tl.to(div2, { scaleY: 1, duration: 2, ease: "power2.inOut" }, 70)

      // Phase 6: Column 3 — Heatmap (72-95%)
      tl.to(col3, { opacity: 1, duration: 8, ease: "power2.out" }, 72)
      // Restore column 1 brightness
      tl.to(col1, { opacity: 1, duration: 8, ease: "power2.out" }, 72)

      // Phase 7: Hold (95-100%) — all visible, absorption time
      // No new tweens, just extend the total timeline duration
      tl.to({}, { duration: 5 }, 95)

      // Store cleanup
      const st = tl.scrollTrigger
      cleanups.push(() => {
        tl.kill()
        st?.kill()
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      cleanups.forEach((fn) => fn())
    }
  }, [isSmoothScrolling])

  return (
    <section ref={sectionRef} id="evidence" className="px-6">
      <div className="max-w-5xl mx-auto flex items-center min-h-screen py-20">
        <div
          ref={panelRef}
          className="w-full border border-border-subtle rounded-xl overflow-hidden"
          style={{ background: "var(--color-bg-elevated)" }}
        >
          {/* Terminal-style header */}
          <div
            className="px-6 py-3 border-b border-border-subtle"
            style={{ background: "var(--color-bg-subtle)" }}
          >
            <span
              ref={headerRef}
              className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary inline-block"
              aria-label={HEADER_TEXT}
            >
              {HEADER_TEXT.split("").map((char, i) => (
                <span key={i} className="char-span" aria-hidden="true">
                  {char}
                </span>
              ))}
            </span>
          </div>

          {/* 3-column content with individually animated columns and dividers */}
          <div className="hidden md:flex">
            {/* Column 1: Selectivity Funnel */}
            <div ref={col1Ref} className="flex-1 p-6 min-w-0">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Selectivity Funnel
              </div>
              <ProofSelectivityFunnel autoAnimate={false} />
            </div>

            {/* Divider 1 */}
            <div
              ref={divider1Ref}
              className="w-px self-stretch"
              style={{ background: "var(--color-border-subtle)" }}
            />

            {/* Column 2: Sector Breakdown */}
            <div ref={col2Ref} className="flex-1 p-6 min-w-0">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Sector Breakdown
              </div>
              <ProofSectorChart candidates={candidates} autoAnimate={false} />
            </div>

            {/* Divider 2 */}
            <div
              ref={divider2Ref}
              className="w-px self-stretch"
              style={{ background: "var(--color-border-subtle)" }}
            />

            {/* Column 3: Factor Correlation */}
            <div ref={col3Ref} className="flex-1 p-6 min-w-0">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Factor Correlation
              </div>
              <ProofHeatmap autoAnimate={false} />
            </div>
          </div>

          {/* Mobile fallback: stacked columns without GSAP pinning */}
          <div className="md:hidden divide-y divide-border-subtle">
            <div className="p-6">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Selectivity Funnel
              </div>
              <ProofSelectivityFunnel />
            </div>
            <div className="p-6">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Sector Breakdown
              </div>
              <ProofSectorChart candidates={candidates} />
            </div>
            <div className="p-6">
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Factor Correlation
              </div>
              <ProofHeatmap />
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-border-subtle text-center">
            <Link
              href="/methodology"
              className="text-sm text-text-secondary hover:text-accent transition-colors"
            >
              Structure replaces intuition with evidence.{" "}
              <span className="text-accent">See full methodology →</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
