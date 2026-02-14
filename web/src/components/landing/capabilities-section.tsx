"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const capabilities = [
  {
    title: "Sector-neutral ranking eliminates cross-sector distortion.",
    body: "A high-margin software company and a capital-intensive manufacturer can\u2019t be compared on raw metrics. Every asset is ranked within its GICS sector first, then scored on relative positioning.",
    span: "col-span-12 md:col-span-7",
    accentBorder: true,
  },
  {
    title: "Growth stage calibrates what matters.",
    body: "High-growth companies are weighted toward quality and momentum. Mature businesses toward value. The engine detects the stage and adjusts factor weights automatically.",
    span: "col-span-12 md:col-span-5",
    accentBorder: false,
  },
  {
    title: "Elimination runs before scoring begins.",
    body: "Earnings manipulation (Beneish), financial distress (Altman Z\u2032\u2032), and liquidity failures are caught first. Compromised assets never enter the scoring pipeline.",
    span: "col-span-12 md:col-span-5",
    accentBorder: false,
  },
  {
    title: "Determinism means the process is auditable.",
    body: "Every score is reproducible. Same data in, same score out, with a complete factor breakdown showing exactly how the composite was derived. No black box. No discretionary overrides.",
    span: "col-span-12 md:col-span-7",
    accentBorder: true,
  },
]

export function CapabilitiesSection() {
  return (
    <section style={{ padding: "96px 24px" }}>
      <div
        className="mx-auto grid grid-cols-12 gap-x-6 gap-y-12"
        style={{ maxWidth: "1280px" }}
      >
        {capabilities.map((cap, i) => (
          <motion.div
            key={i}
            className={`${cap.span} pt-10 px-8 pb-2`}
            style={{
              borderTop: cap.accentBorder
                ? "1px solid var(--color-accent)"
                : "1px solid var(--color-border-primary)",
            }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.15, ease }}
          >
            <h3 className="text-[24px] md:text-[26px] lg:text-[30px] font-semibold leading-[1.10] tracking-[-0.01em] text-text-primary mb-3">
              {cap.title}
            </h3>
            <p className="text-text-secondary leading-relaxed text-[16px] md:text-[17px] max-w-[640px]">
              {cap.body}
            </p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
