"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const lines = [
  "Most investors react.",
  "Few operate with structure.",
  "Emotion is expensive.",
]

function MarketNoiseViz() {
  const points = [
    { x: 30, y: 20, r: 3.75 },
    { x: 85, y: 55, r: 4.5 },
    { x: 160, y: 30, r: 3 },
    { x: 220, y: 85, r: 5.25 },
    { x: 130, y: 100, r: 3 },
    { x: 300, y: 40, r: 3.75 },
    { x: 250, y: 120, r: 3 },
    { x: 60, y: 140, r: 4.5 },
    { x: 340, y: 90, r: 3.75 },
    { x: 180, y: 160, r: 3 },
    { x: 100, y: 200, r: 4.5 },
    { x: 280, y: 180, r: 3.75 },
    { x: 40, y: 230, r: 3 },
    { x: 200, y: 220, r: 4.5 },
    { x: 320, y: 200, r: 3 },
    { x: 150, y: 250, r: 3.75 },
    { x: 370, y: 150, r: 3 },
    { x: 260, y: 260, r: 4.5 },
  ]

  const connections = [
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 5],
    [6, 7], [8, 9], [10, 11], [12, 13], [14, 15],
    [1, 4], [5, 8], [9, 11], [7, 10], [13, 16],
  ]

  return (
    <svg
      className="w-full h-full"
      viewBox="0 0 400 280"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {connections.map(([a, b], i) => (
        <line
          key={`line-${i}`}
          x1={points[a].x}
          y1={points[a].y}
          x2={points[b].x}
          y2={points[b].y}
          stroke="currentColor"
          strokeWidth="0.8"
          className="text-text-secondary opacity-[0.12]"
        />
      ))}
      {points.map((p, i) => (
        <circle
          key={`point-${i}`}
          cx={p.x}
          cy={p.y}
          r={p.r}
          className="text-text-secondary"
          fill="currentColor"
          opacity={0.15 + (i % 3) * 0.08}
        />
      ))}
      <circle cx={220} cy={85} r={5.25} className="text-accent" fill="currentColor" opacity={0.35} />
      <circle cx={100} cy={200} r={4.5} className="text-accent" fill="currentColor" opacity={0.35} />
    </svg>
  )
}

export function FrictionSection() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "80px",
          paddingBottom: "96px",
        }}
      >
        <div className="col-span-4 md:col-span-4 lg:col-span-6 flex flex-col gap-6">
          {lines.map((line, i) => (
            <motion.h3
              key={line}
              className="text-[28px] md:text-[32px] font-semibold text-text-primary leading-tight"
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.2, ease }}
            >
              {line}
            </motion.h3>
          ))}
          <motion.p
            className="text-[15px] text-text-secondary leading-relaxed max-w-[480px]"
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.6, ease }}
          >
            Behavioral finance research shows that emotional trading costs retail investors
            1.5–4% annually. Structure eliminates the leak.*
          </motion.p>
          <motion.span
            className="text-[11px] text-text-tertiary font-mono"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.3, delay: 0.8 }}
          >
            * Barber & Odean, 2000; Dalbar QAIB, 2023
          </motion.span>
        </div>

        {/* Abstract market noise visualization — tablet + desktop */}
        <motion.div
          className="hidden md:block md:col-start-5 md:col-span-4 lg:col-start-8 lg:col-span-5"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.3, ease }}
        >
          <MarketNoiseViz />
        </motion.div>
      </div>
    </section>
  )
}
