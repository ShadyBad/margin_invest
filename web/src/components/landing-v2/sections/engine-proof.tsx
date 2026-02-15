"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const panels = [
  { title: "Composite Score", bars: 4 },
  { title: "Risk Breakdown", bars: 3 },
  { title: "Factor Weights", bars: 5 },
]

export function EngineProof() {
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
        {/* Left: heading + body */}
        <motion.div
          className="col-span-4 md:col-span-4 lg:col-span-5 flex flex-col justify-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h2 className="text-[32px] md:text-[40px] lg:text-[48px] font-bold text-text-primary leading-tight tracking-[-0.5px]">
            What the engine produces.
          </h2>
          <p className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed">
            Every equity receives a deterministic composite score, risk profile,
            and factor-weighted breakdown — no narrative, no discretion.
          </p>
        </motion.div>

        {/* Right: mock dashboard panels */}
        <div className="col-span-4 md:col-start-5 md:col-span-4 lg:col-start-7 lg:col-span-6 flex flex-col gap-4">
          {panels.map((panel, i) => (
            <motion.div
              key={panel.title}
              className="border border-border-primary rounded-[6px] p-4"
              style={{ transform: `rotate(${i % 2 === 0 ? -0.5 : 0.5}deg)` }}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.15 * i, ease }}
            >
              <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px]">
                {panel.title}
              </span>
              <div className="mt-3 flex flex-col gap-2">
                {Array.from({ length: panel.bars }).map((_, j) => (
                  <div
                    key={j}
                    className="h-2 rounded-sm bg-bg-subtle"
                    style={{ width: `${40 + Math.random() * 50}%` }}
                  />
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Annotation */}
        <motion.p
          className="col-span-4 md:col-span-8 lg:col-span-12 mt-8 text-[13px] text-text-secondary italic"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.5, ease }}
        >
          WebGL stage morph ends here.
        </motion.p>
      </div>
    </section>
  )
}
