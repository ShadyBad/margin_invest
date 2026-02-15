"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function InvestorPositioning() {
  return (
    <section className="min-h-screen flex items-center justify-center">
      <div className="text-center max-w-[800px] px-[8vw]">
        <motion.h2
          className="text-[32px] md:text-[40px] lg:text-[48px] font-bold text-text-primary leading-tight tracking-[-0.5px]"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease }}
        >
          You&rsquo;re not trading. You&rsquo;re operating.
        </motion.h2>
        <motion.p
          className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.8, ease }}
        >
          Capital allocation as a repeatable process.
        </motion.p>
      </div>
    </section>
  )
}
