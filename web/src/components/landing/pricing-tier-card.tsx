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

interface PricingTierCardProps {
  tier: Tier
}

const spring = { stiffness: 400, damping: 25 }

export function PricingTierCard({ tier }: PricingTierCardProps) {
  const prefersReducedMotion = useReducedMotion()

  const card = (
    <motion.div
      className="terminal-card p-6 md:p-8 flex flex-col h-full focus-visible:outline-2 focus-visible:outline-accent/40 focus-visible:outline-offset-2"
      style={
        tier.highlighted
          ? { borderColor: "color-mix(in srgb, var(--color-accent), transparent 70%)" }
          : undefined
      }
      whileHover={
        prefersReducedMotion
          ? {}
          : { y: -4, boxShadow: "0 2px 8px rgba(0,0,0,0.3)" }
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
          : { y: -4, boxShadow: "0 2px 8px rgba(0,0,0,0.3)" }
      }
    >
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs uppercase tracking-[0.2em] text-text-tertiary">
          {tier.name}
        </span>
        {tier.highlighted && (
          <span className="text-[10px] text-accent bg-accent/10 px-2 py-0.5 rounded">
            Most Popular
          </span>
        )}
      </div>
      <div className="mb-2">
        <span className="font-display text-4xl text-text-primary">{tier.price}</span>
        {tier.period && (
          <span className="text-sm text-text-tertiary ml-1">{tier.period}</span>
        )}
      </div>
      <p className="text-sm text-text-secondary mb-6">{tier.description}</p>
      <ul className="space-y-2 mb-8 flex-1">
        {tier.features.map((feature) => (
          <li key={feature} className="flex items-start gap-2 text-sm text-text-secondary">
            <span className="text-accent mt-0.5">&#10003;</span>
            <span>{feature}</span>
          </li>
        ))}
      </ul>
      <Link
        href="/onboarding"
        className="block text-center text-sm font-medium text-accent border border-accent/30 rounded-lg py-2.5 hover:bg-accent/5 transition-colors"
      >
        Get Started
      </Link>
    </motion.div>
  )

  if (tier.highlighted) {
    return <div className="-mt-2">{card}</div>
  }

  return card
}
