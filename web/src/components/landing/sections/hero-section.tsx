"use client"

import { motion } from "framer-motion"
import { ButtonPrimary } from "../button-primary"
import { ButtonSecondary } from "../button-secondary"

const ease = [0.22, 1, 0.36, 1] as const

export function HeroSection() {
  return (
    <section className="relative">
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1200px",
          paddingLeft: "10vw",
          paddingRight: "10vw",
          paddingTop: "180px",
          paddingBottom: "140px",
        }}
      >
        <div className="col-span-4 md:col-span-8 lg:col-span-8 flex flex-col justify-center lg:mt-[20px]">
          <motion.h1
            className="font-display text-[56px] md:text-[72px] lg:text-[88px] font-normal leading-[1.05] tracking-[-0.04em] text-text-primary"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2, ease }}
          >
            Conviction scoring for serious investors.
          </motion.h1>

          <motion.p
            className="mt-8 text-lg md:text-xl text-text-secondary leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4, ease }}
          >
            A deterministic engine that scores every stock across 6 factors — so you hold with structure, not hope.
          </motion.p>

          <motion.div
            className="mt-12 flex items-center gap-6"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.55, ease }}
          >
            <ButtonPrimary href="/onboarding">Score your first position</ButtonPrimary>
            <ButtonSecondary href="/methodology">See the methodology</ButtonSecondary>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
