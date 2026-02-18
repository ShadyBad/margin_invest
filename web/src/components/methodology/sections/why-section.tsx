"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const benefits = [
  {
    title: "Replaces hours of manual research",
    desc: "The engine scores every equity in the universe automatically. You focus on decision-making, not data gathering.",
  },
  {
    title: "Reduces emotional mistakes",
    desc: "A systematic framework removes fear and greed from the analysis. The same process runs whether markets are up 20% or down 20%.",
  },
  {
    title: "Provides a repeatable process",
    desc: "Every week, the same pipeline runs, the same factors are evaluated, and the same scoring logic applies. Consistency compounds.",
  },
  {
    title: "Surfaces what you would miss",
    desc: "Factor alignment across quality, value, and momentum catches opportunities that don't show up in screener filters or headline news.",
  },
  {
    title: "Quantifies conviction",
    desc: "Instead of gut feelings about which stocks are 'good', you get a ranked score with a transparent breakdown of exactly why.",
  },
  {
    title: "Structures position sizing",
    desc: "Allocation guidance ties conviction strength to position size, so your portfolio reflects your highest-confidence ideas.",
  },
]

const comparison = [
  { feature: "Repeatable scoring process", free: false, newsletter: false, margin: true },
  { feature: "Transparent factor breakdown", free: false, newsletter: false, margin: true },
  { feature: "Risk-adjusted conviction", free: false, newsletter: false, margin: true },
  { feature: "Margin of safety framework", free: false, newsletter: false, margin: true },
  { feature: "Allocation guidance", free: false, newsletter: false, margin: true },
  { feature: "No narrative bias", free: true, newsletter: false, margin: true },
]

function Check() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-accent">
      <path d="M3 8.5L6.5 12L13 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Dash() {
  return <span className="block w-4 h-px bg-border-primary" />
}

export function WhySection() {
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
          Why Margin Invest
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-12 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Why this exists.
        </motion.h2>

        {/* Benefits Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">
          {benefits.map((benefit, i) => (
            <motion.div
              key={benefit.title}
              className="flex gap-4"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.06, ease }}
            >
              <div className="flex-shrink-0 mt-1">
                <Check />
              </div>
              <div>
                <h3 className="text-[15px] font-semibold text-text-primary mb-1">
                  {benefit.title}
                </h3>
                <p className="text-[14px] text-text-secondary leading-relaxed">
                  {benefit.desc}
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Comparison Table */}
        <motion.div
          className="border border-border-primary rounded-lg bg-bg-elevated overflow-hidden"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border-primary">
                  <th className="text-left text-text-secondary font-medium py-3 px-4 min-w-[200px]">
                    Capability
                  </th>
                  <th className="text-center text-text-tertiary font-medium py-3 px-4 w-[120px]">
                    Free Screeners
                  </th>
                  <th className="text-center text-text-tertiary font-medium py-3 px-4 w-[120px]">
                    Newsletters
                  </th>
                  <th className="text-center text-accent font-medium py-3 px-4 w-[120px]">
                    Margin Invest
                  </th>
                </tr>
              </thead>
              <tbody>
                {comparison.map((row) => (
                  <tr key={row.feature} className="border-b border-border-subtle last:border-0">
                    <td className="text-text-primary py-3 px-4">{row.feature}</td>
                    <td className="py-3 px-4">
                      <div className="flex justify-center">{row.free ? <Check /> : <Dash />}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-center">{row.newsletter ? <Check /> : <Dash />}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-center">{row.margin ? <Check /> : <Dash />}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
