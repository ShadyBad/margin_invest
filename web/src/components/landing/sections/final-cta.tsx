"use client"

import { motion } from "framer-motion"
import { ButtonPrimary } from "../button-primary"
import Link from "next/link"

const ease = [0.22, 1, 0.36, 1] as const

export function FinalCTA() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "120px",
          paddingBottom: "160px",
        }}
      >
        <motion.div
          className="text-center max-w-[560px] mx-auto"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h2 className="text-[28px] md:text-[32px] font-bold text-text-primary leading-tight tracking-[-0.3px] mb-3">
            Score your first position.
          </h2>
          <p className="text-[15px] text-text-secondary mb-8">
            See every stock through the lens of conviction.
          </p>
          <ButtonPrimary href="/onboarding">Start free</ButtonPrimary>
        </motion.div>

        <div
          className="mt-16 pt-6 border-t border-divider flex flex-col md:flex-row items-center justify-between gap-4 text-[13px] text-text-secondary"
        >
          <span suppressHydrationWarning>
            &copy; {new Date().getFullYear()} Margin Invest
          </span>
          <div className="flex items-center gap-6">
            <Link href="/methodology" className="hover:text-text-primary transition-colors">
              Methodology
            </Link>
            <Link href="/dashboard" className="hover:text-text-primary transition-colors">
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
