"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const principles = [
  {
    title: "Deterministic",
    desc: "Same inputs produce the same outputs. Enter AAPL today and tomorrow with the same data — the scores will be identical. No randomness, no hidden state, no human override.",
  },
  {
    title: "Published formulas",
    desc: "Every formula used in scoring is documented in our guides. You can verify any factor calculation yourself with publicly available financial data.",
  },
  {
    title: "Known limitations",
    desc: "The engine relies on publicly available data that can be delayed, restated, or incomplete. It cannot capture qualitative factors like management quality, regulatory changes, or geopolitical risk. We document these limitations honestly.",
  },
]

export function TransparencySection() {
  return (
    <section className="border-t border-border-subtle">
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "96px",
          paddingBottom: "96px",
        }}
      >
        <motion.p
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Transparency
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          We show our work because we trust our work.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Most investment tools hide their methodology behind vague
          descriptions. We publish ours in full. If you can&apos;t verify
          how a score was calculated, you shouldn&apos;t trust it.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {principles.map((principle, i) => (
            <motion.div
              key={principle.title}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-3">
                {principle.title}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {principle.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
