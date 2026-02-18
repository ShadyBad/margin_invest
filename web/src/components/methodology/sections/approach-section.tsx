"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function ApproachSection() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "64px",
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
          The Approach
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-8 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          A systematic engine for asymmetric opportunities.
        </motion.h2>

        <motion.div
          className="max-w-2xl space-y-4 text-[16px] sm:text-[17px] text-text-secondary leading-relaxed"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <p>
            Margin Invest is a deterministic research engine that scores every equity in its
            universe across quality, value, and momentum factors. The same inputs always produce
            the same outputs — no narrative, no discretion, no human judgment in the pipeline.
          </p>
          <p>
            The engine surfaces companies where multiple factors align: strong fundamentals,
            attractive valuation, and positive price momentum. It then quantifies conviction
            and identifies a margin of safety — the gap between price and estimated intrinsic value
            that creates asymmetric risk/reward.
          </p>
          <p>
            The result is a ranked set of candidates with transparent factor breakdowns, not a
            list of tips. You see exactly why each equity scored the way it did, and you decide
            what to do with it.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
