"use client"

import Link from "next/link"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const withoutSystem = [
  "Hours spent gathering data from multiple sources",
  "Ad-hoc screening with different criteria each time",
  "No consistent framework for comparing candidates",
  "Position sizes based on gut feel",
  "No systematic monitoring for changes",
]

const withSystem = [
  "Full universe scored daily \u2014 candidates surface automatically",
  "Same factors, same weights, same process every cycle",
  "Transparent breakdown so you know exactly why",
  "Position sizing calibrated to conviction strength",
  "Score changes flag when something needs your attention",
]

export function CTASection() {
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
          Why Pay
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-10 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Replace hours of screening with a system that runs every day.
        </motion.h2>

        {/* ROI comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1, ease }}
          >
            <h3 className="text-[15px] font-semibold text-text-tertiary mb-4">
              Without a system
            </h3>
            <ul className="space-y-2">
              {withoutSystem.map((item) => (
                <li
                  key={item}
                  className="text-[14px] text-text-tertiary leading-relaxed flex items-start gap-2"
                >
                  <span className="mt-0.5 flex-shrink-0">{"\u2013"}</span>
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            className="p-6 border border-accent/30 rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.18, ease }}
          >
            <h3 className="text-[15px] font-semibold text-text-primary mb-4">
              With Margin Invest
            </h3>
            <ul className="space-y-2">
              {withSystem.map((item) => (
                <li
                  key={item}
                  className="text-[14px] text-text-secondary leading-relaxed flex items-start gap-2"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    className="text-accent flex-shrink-0 mt-0.5"
                  >
                    <path
                      d="M3 8.5L6.5 12L13 4"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>
        </div>

        {/* CTA */}
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <p className="text-[16px] sm:text-[17px] text-text-secondary mb-8 max-w-lg mx-auto">
            Score your first stock free. See the full factor breakdown, conviction
            score, and price target framework.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/onboarding"
              className="inline-flex items-center justify-center h-12 px-8 text-[14px] font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
            >
              Score your first stock free
            </Link>
            <Link
              href="/#pricing"
              className="inline-flex items-center justify-center h-12 px-6 text-[14px] font-medium text-text-secondary underline underline-offset-4 decoration-border-primary hover:text-text-primary transition-colors"
            >
              Compare plans
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
