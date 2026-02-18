"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const notFor = ["Day traders", "Narrative chasers", "Meme cycles"]
const forItems = ["Long-horizon investors", "Portfolio operators", "Capital stewards"]

export function PositioningSection() {
  return (
    <section id="positioning" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.h2
          className="font-display text-4xl md:text-5xl text-text-primary mb-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease }}
        >
          Built for disciplined capital allocators.
        </motion.h2>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2, ease }}
        >
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-text-tertiary mb-6">Not for</p>
            <ul className="space-y-3">
              {notFor.map((item) => (
                <li key={item} className="text-lg text-text-tertiary">{item}</li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-accent mb-6">Built for</p>
            <ul className="space-y-3">
              {forItems.map((item) => (
                <li key={item} className="text-lg text-text-primary">{item}</li>
              ))}
            </ul>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
