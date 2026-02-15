"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const lines = [
  "Most investors react.",
  "Few operate with structure.",
  "Emotion is expensive.",
]

export function FrictionSection() {
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
        <div className="col-span-4 md:col-span-6 lg:col-span-6 flex flex-col gap-8">
          {lines.map((line, i) => (
            <motion.h3
              key={line}
              className="text-[32px] font-semibold text-text-primary leading-tight"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.12, ease }}
            >
              {line}
            </motion.h3>
          ))}
        </div>

        {/* Abstract SVG scatter — desktop only */}
        <div className="hidden lg:block lg:col-start-8 lg:col-span-5">
          <svg
            className="w-full h-full opacity-[0.15]"
            viewBox="0 0 400 300"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <circle cx="60" cy="40" r="3" fill="currentColor" />
            <circle cx="150" cy="80" r="2" fill="currentColor" />
            <circle cx="320" cy="50" r="4" fill="currentColor" />
            <circle cx="240" cy="140" r="2.5" fill="currentColor" />
            <circle cx="100" cy="200" r="3.5" fill="currentColor" />
            <circle cx="350" cy="180" r="2" fill="currentColor" />
            <circle cx="200" cy="250" r="3" fill="currentColor" />
            <circle cx="80" cy="130" r="1.5" fill="currentColor" />
            <circle cx="290" cy="220" r="2.5" fill="currentColor" />
            <circle cx="170" cy="170" r="2" fill="currentColor" />
            <circle cx="50" cy="270" r="3" fill="currentColor" />
            <circle cx="380" cy="100" r="1.5" fill="currentColor" />
          </svg>
        </div>
      </div>
    </section>
  )
}
