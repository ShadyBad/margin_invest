"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function MethodologyHero() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "160px",
          paddingBottom: "80px",
        }}
      >
        <motion.h1
          className="text-[48px] md:text-[56px] lg:text-[72px] font-bold leading-[0.98] tracking-[-0.5px] text-text-primary max-w-[800px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease }}
        >
          How Margin scores equities.
        </motion.h1>
        <motion.p
          className="mt-6 text-lg md:text-xl text-text-secondary leading-relaxed max-w-[600px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4, ease }}
        >
          A deterministic pipeline that transforms raw market data into
          composite conviction scores — no narrative, no discretion, no human
          judgment.
        </motion.p>
      </div>
    </section>
  )
}
