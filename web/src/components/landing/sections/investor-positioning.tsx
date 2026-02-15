"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function InvestorPositioning() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "96px",
          paddingBottom: "96px",
        }}
      >
        <motion.div
          className="col-span-4 md:col-span-8 lg:col-span-8"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h2 className="text-[32px] md:text-[40px] lg:text-[48px] font-bold text-text-primary leading-tight tracking-[-0.5px]">
            You&rsquo;re not trading. You&rsquo;re operating.
          </h2>
          <p className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed max-w-[640px]">
            This platform is built for investors who treat capital allocation as a
            repeatable process, not a series of bets.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
