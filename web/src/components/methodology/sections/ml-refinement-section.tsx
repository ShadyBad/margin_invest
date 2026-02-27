"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const keyPoints = [
  {
    title: "Weekly training cycle",
    detail:
      "Models retrain every Saturday at 2 AM UTC on 90+ days of accumulated scoring data. Short-lived market noise washes out; persistent patterns surface.",
  },
  {
    title: "Quality gate",
    detail:
      "ML models are only activated when their prediction quality (rank IC) exceeds 0.15. Below that threshold, the system runs on deterministic scores alone.",
  },
  {
    title: "Cluster + anomaly detection",
    detail:
      "Cluster models group similar stocks by factor profile. A variational autoencoder (VAE) detects anomalous factor patterns that may signal mispricing or risk.",
  },
  {
    title: "Bounded adjustments",
    detail:
      "ML can adjust scores up or down, but adjustments are bounded and auditable. No black-box overrides — every change is logged with the model version and input features.",
  },
  {
    title: "Graceful degradation",
    detail:
      "The system works fully without ML. If no qualified model exists, deterministic scores flow through unchanged. ML refines — it never replaces.",
  },
]

export function MLRefinementSection() {
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
          Stage 5 · ML Refinement
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Deterministic first. Machine learning second.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          The deterministic scores are now refined by machine learning models
          trained on the system&apos;s own prediction history. AAPL&apos;s
          factor profile is compared against patterns the models have learned
          from thousands of previous scoring cycles.
        </motion.p>

        {/* Key points */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
          {keyPoints.map((point, i) => (
            <motion.div
              key={point.title}
              className="p-5 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.06, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-2">
                {point.title}
              </h3>
              <p className="text-[13px] text-text-secondary leading-relaxed">
                {point.detail}
              </p>
            </motion.div>
          ))}
        </div>

        {/* ML badge callout */}
        <motion.div
          className="p-5 border border-border-primary rounded-lg bg-bg-elevated max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <p className="text-[14px] text-text-primary leading-relaxed">
            <span className="font-mono text-accent text-[13px] mr-2">
              ML Adjusted
            </span>
            When you see this badge on a score, it means the deterministic
            output has been refined by these models. The original deterministic
            score is always available for comparison.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
