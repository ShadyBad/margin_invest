"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const frictionPoints = [
  {
    title: "Emotion enters before analysis finishes.",
    body: "Sentiment shifts between checking a position and deciding what to do about it. The process isn\u2019t flawed \u2014 it\u2019s absent.",
  },
  {
    title: "Inconsistent frameworks produce inconsistent results.",
    body: "Switching between screeners, newsletters, and intuition means every decision uses different criteria. There\u2019s no baseline to evaluate against.",
  },
  {
    title: "Retail tools measure activity, not quality.",
    body: "Volume, price movement, trending tickers \u2014 these describe what happened. They don\u2019t tell you whether the underlying business justifies a position.",
  },
]

export function FrictionSection() {
  return (
    <section style={{ padding: "80px 24px 96px" }}>
      <div className="mx-auto grid grid-cols-12 gap-6" style={{ maxWidth: "1280px" }}>
        {/* Left column: cols 1-5 */}
        <div className="col-span-12 md:col-span-5">
          <motion.h2
            className="text-[30px] md:text-[36px] lg:text-[44px] font-bold leading-[1.02] tracking-[-0.02em] text-text-primary"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55, ease }}
          >
            Most investment decisions are made with conviction they haven&apos;t earned.
          </motion.h2>
        </div>

        {/* Spacer: col 6 */}
        <div className="hidden md:block md:col-span-1" />

        {/* Right column: cols 7-12 */}
        <div className="col-span-12 md:col-span-6 space-y-12">
          {frictionPoints.map((point, i) => (
            <motion.div
              key={i}
              className="border-l-2 border-accent/40 pl-6"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.15 * (i + 1), ease }}
            >
              <h3 className="text-[24px] md:text-[26px] lg:text-[30px] font-semibold leading-[1.10] tracking-[-0.01em] text-text-primary mb-2">
                {point.title}
              </h3>
              <p className="text-text-secondary leading-relaxed text-[16px] md:text-[17px] max-w-[640px]">
                {point.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
