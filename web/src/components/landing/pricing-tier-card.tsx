"use client"

import Link from "next/link"
import { motion, useReducedMotion } from "framer-motion"

export interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  highlighted?: boolean
}

const CTA_TEXT: Record<string, string> = {
  Scout: "Search Any Ticker",
  Analyst: "Start Analyzing",
  Portfolio: "Start Building",
}

interface PricingTierCardProps {
  tier: Tier
}

const spring = { stiffness: 400, damping: 25 }

export function PricingTierCard({ tier }: PricingTierCardProps) {
  const prefersReducedMotion = useReducedMotion()

  const card = (
    <motion.div
      className="terminal-card rounded-xl p-6 md:p-8 flex flex-col h-full relative overflow-hidden focus-visible:outline-2 focus-visible:outline-accent/40 focus-visible:outline-offset-2 hover:-translate-y-0.5 hover:border-[var(--color-accent-medium)] transition-all duration-200"
      style={
        tier.highlighted
          ? {
              borderColor: "color-mix(in srgb, var(--color-accent-warm) 50%, var(--color-border-subtle))",
              boxShadow: "0 0 40px rgba(201,150,59,0.12), 0 8px 24px rgba(0,0,0,0.3)",
              transform: "scale(1.02)",
            }
          : tier.name === "Scout"
            ? { opacity: 0.85 }
            : undefined
      }
      whileHover={
        prefersReducedMotion
          ? {}
          : { boxShadow: tier.highlighted
              ? "0 0 48px rgba(201,150,59,0.20), 0 8px 24px rgba(0,0,0,0.3)"
              : "0 2px 8px rgba(0,0,0,0.3)"
            }
      }
      whileTap={
        prefersReducedMotion
          ? {}
          : { y: -1, scale: 0.995 }
      }
      transition={spring}
      whileFocus={
        prefersReducedMotion
          ? {}
          : { boxShadow: tier.highlighted
              ? "0 0 48px rgba(201,150,59,0.20), 0 8px 24px rgba(0,0,0,0.3)"
              : "0 2px 8px rgba(0,0,0,0.3)"
            }
      }
    >
      {/* Top accent bar for highlighted card */}
      {tier.highlighted && (
        <div
          className="absolute top-0 left-0 right-0"
          style={{
            height: '2px',
            background: 'linear-gradient(90deg, var(--color-accent-warm), transparent)',
          }}
        />
      )}

      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs uppercase tracking-[0.2em] text-text-tertiary">
          {tier.name}
        </span>
        {tier.highlighted && (
          <span className="text-xs px-2 py-0.5 rounded" style={{ color: 'var(--color-accent-warm)', background: 'var(--color-accent-warm-muted)' }}>
            Most Popular
          </span>
        )}
      </div>
      <div className="mb-2">
        <span className="font-mono text-4xl text-text-primary">{tier.price}</span>
        {tier.period && (
          <span className="text-sm text-text-tertiary ml-1">{tier.period}</span>
        )}
      </div>
      <p className="text-sm text-text-secondary mb-1">{tier.description}</p>
      {tier.period ? (
        <p className="text-xs text-text-tertiary font-mono mb-5">billed monthly</p>
      ) : (
        <div className="mb-6" />
      )}
      <ul className="space-y-2 mb-8 flex-1">
        {tier.features.map((feature) => (
          <li key={feature} className="flex items-start gap-2 text-sm text-text-secondary">
            <span style={{ color: 'var(--color-accent)' }} className="text-base">&#10003;</span>
            <span>{feature}</span>
          </li>
        ))}
      </ul>
      {tier.highlighted ? (
        <Link
          href="/onboarding"
          className="block text-center text-sm font-medium rounded-lg py-2.5 transition-colors"
          style={{
            background: 'var(--color-accent)',
            color: 'var(--color-bg-primary)',
            border: 'none',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-accent-hover)' }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--color-accent)' }}
        >
          {CTA_TEXT[tier.name] ?? "Get Started"}
        </Link>
      ) : (
        <Link
          href="/onboarding"
          className="block text-center text-sm font-medium text-accent border border-accent/30 rounded-lg py-2.5 hover:bg-accent/5 transition-colors opacity-70"
        >
          {CTA_TEXT[tier.name] ?? "Get Started"}
        </Link>
      )}
    </motion.div>
  )

  if (tier.highlighted) {
    return <div className="-mt-2">{card}</div>
  }

  return card
}
