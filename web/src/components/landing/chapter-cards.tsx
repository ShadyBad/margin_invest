"use client"

import { useRef } from "react"
import { motion, useScroll, useTransform, useReducedMotion, type MotionValue } from "framer-motion"
import { FlowCard } from "./flow-card"

const engineCards = [
  {
    title: "Raw Signal",
    subtitle: "The Engine",
    content:
      "Earnings transcripts, SEC filings, price targets, institutional flows — hundreds of data points per ticker, gathered and normalized in real time.",
  },
  {
    title: "Elimination Filters",
    subtitle: "The Engine",
    content:
      "Penny stocks, delistings, insufficient data — fail-fast filters eliminate noise before scoring begins. Only investable assets proceed.",
  },
  {
    title: "Factor Analysis",
    subtitle: "The Engine",
    content:
      "Five scoring factors — valuation, quality, momentum, growth, and sentiment — each ranked against sector peers using percentile normalization.",
  },
  {
    title: "Sector Normalization",
    subtitle: "The Engine",
    content:
      "Rank within GICS sector first, then combine. A 60th-percentile bank is compared to banks, not to tech stocks. Sector-neutral by design.",
  },
  {
    title: "Conviction Output",
    subtitle: "The Engine",
    content:
      "A composite conviction score from 0 to 100 with a clear signal: strong buy, buy, hold, or avoid. Factor breakdowns show exactly what's driving it.",
  },
]

const proofCards = [
  {
    title: "Sample Score",
    subtitle: "The Proof",
    content:
      "AAPL scores 78 — Strong Buy. Driven by quality fundamentals and institutional accumulation. Valuation slightly below sector median.",
  },
  {
    title: "Factor Breakdown",
    subtitle: "The Proof",
    content:
      "Valuation 62 · Quality 85 · Momentum 71 · Growth 68 · Sentiment 89. Every factor transparent, every percentile verifiable.",
  },
  {
    title: "Growth vs Value",
    subtitle: "The Proof",
    content:
      "Growth-stage companies weight momentum and growth higher. Mature companies weight valuation and quality. The engine adapts automatically.",
  },
  {
    title: "Portfolio View",
    subtitle: "The Proof",
    content:
      "AAPL 78 · MSFT 72 · GOOGL 65 · NVDA 58 · AMZN 45. Compare conviction across your entire portfolio at a glance.",
  },
  {
    title: "Historical Accuracy",
    subtitle: "The Proof",
    content:
      "Backtest any scoring period against actual returns. No curve-fitting, no survivorship bias. The same deterministic engine, applied historically.",
  },
]

/**
 * Compute opacity for a card based on its index distance from the current
 * focal point. The focal card shifts as the section scrolls:
 * progress 0 → focal index ~1, progress 0.5 → focal index 2, progress 1 → focal index ~3
 */
function useCardSpotlight(
  scrollYProgress: MotionValue<number>,
  cardIndex: number,
) {
  // Focal card index shifts from 1 to 3 as scroll progresses
  const opacity = useTransform(scrollYProgress, (progress) => {
    const focal = 1 + progress * 2
    const distance = Math.abs(cardIndex - focal)
    // Smooth falloff: 1.0 at center, 0.6 at distance 1, 0.3 at 2, 0.15 at 3+
    return Math.max(0.15, 1 - distance * 0.35)
  })

  return { opacity }
}

function CardRow({
  cards,
  direction,
  scrollYProgress,
}: {
  cards: typeof engineCards
  direction: "left" | "right"
  scrollYProgress: MotionValue<number>
}) {
  const prefersReducedMotion = useReducedMotion()

  const x = useTransform(
    scrollYProgress,
    [0, 1],
    prefersReducedMotion
      ? ["0%", "0%"]
      : direction === "left"
        ? ["30%", "-30%"]
        : ["-30%", "30%"],
  )

  return (
    <motion.div
      data-card-row
      data-direction={direction}
      className="flex gap-6 py-4"
      style={{ x }}
    >
      {cards.map((card, index) => (
        <SpotlightCard
          key={card.title}
          card={card}
          index={index}
          scrollYProgress={scrollYProgress}
        />
      ))}
    </motion.div>
  )
}

function SpotlightCard({
  card,
  index,
  scrollYProgress,
}: {
  card: (typeof engineCards)[number]
  index: number
  scrollYProgress: MotionValue<number>
}) {
  const { opacity } = useCardSpotlight(scrollYProgress, index)

  return (
    <FlowCard
      title={card.title}
      subtitle={card.subtitle}
      motionStyle={{ opacity }}
    >
      <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
        {card.content}
      </p>
    </FlowCard>
  )
}

export function ChapterCards() {
  const sectionRef = useRef<HTMLDivElement>(null)

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  })

  return (
    <section
      ref={sectionRef}
      data-chapter-cards
      id="engine"
      className="relative overflow-hidden py-24"
    >
      <div className="flex flex-col items-center justify-center gap-8">
        {/* Desktop: two counter-flowing rows */}
        <div className="hidden md:block w-full">
          <CardRow
            cards={engineCards}
            direction="left"
            scrollYProgress={scrollYProgress}
          />
          <CardRow
            cards={proofCards}
            direction="right"
            scrollYProgress={scrollYProgress}
          />
        </div>

        {/* Mobile: single interleaved column (FlowCard self-tracks vertically) */}
        <div className="md:hidden flex flex-col items-center gap-4 px-6 max-w-[360px] mx-auto py-8">
          {engineCards.map((card, i) => (
            <div key={card.title} className="w-full">
              <FlowCard title={card.title} subtitle={card.subtitle}>
                <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                  {card.content}
                </p>
              </FlowCard>
              {proofCards[i] && (
                <div className="mt-4">
                  <FlowCard
                    title={proofCards[i].title}
                    subtitle={proofCards[i].subtitle}
                  >
                    <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                      {proofCards[i].content}
                    </p>
                  </FlowCard>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
