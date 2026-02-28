"use client"

import { useState } from "react"

interface FaqEntry {
  question: string
  answer: string
}

const FAQ_ITEMS: FaqEntry[] = [
  {
    question: "What is Margin Invest?",
    answer:
      "A deterministic scoring engine that evaluates every US-listed equity using forensic elimination filters and multi-factor analysis. It has no analysts, no opinions, and no override button. Same inputs, same outputs, every time.",
  },
  {
    question: "Is this investment advice?",
    answer:
      "No. Margin Invest is an analytical tool, not a financial advisor. We don\u2019t make recommendations \u2014 we show you what the math says and let you decide. All scores are informational and educational. You are responsible for your own investment decisions.",
  },
  {
    question: "How is this different from Zacks or Morningstar?",
    answer:
      "Zacks shows you a rank. We show you the formula. Every score links to its calculation, every threshold is published, and every elimination is explained. You can verify any number with a spreadsheet and the same data sources. Transparency is the product.",
  },
  {
    question: "How is this different from an \u201CAI stock picker\u201D?",
    answer:
      "We don\u2019t use AI for scoring. Every calculation is deterministic \u2014 mathematical formulas applied consistently to public data. No machine learning black box. No \u201CAI-powered insights.\u201D The system is auditable, reproducible, and can\u2019t hallucinate a buy signal.",
  },
  {
    question: "What are the elimination filters?",
    answer:
      "Six forensic screens including: Beneish M-Score (earnings manipulation detection), Altman Z-Score (bankruptcy probability), penny stock exclusion, delisting detection, minimum liquidity thresholds, and data sufficiency requirements. 70%+ of US equities fail at least one filter.",
  },
  {
    question: "What factors are used in scoring?",
    answer:
      "Five factors: Quality (ROIC, margins, balance sheet strength), Value (earnings yield, book value, cash flow), Momentum (price trend, relative strength, earnings revisions), plus Growth and Sentiment as modifiers. Each factor is scored as a percentile rank within the stock\u2019s GICS sector.",
  },
  {
    question: "What does \u201Csector-neutral\u201D mean?",
    answer:
      "We compare stocks to their sector peers, not to the entire market. A bank with 15% ROIC is excellent \u2014 among banks. A tech company with 15% ROIC is below average \u2014 among tech. Sector-neutral scoring prevents false comparisons.",
  },
  {
    question: "Can I change the factor weights or customize the scoring?",
    answer:
      "No \u2014 and that\u2019s by design. Custom weights inject your bias back into the system. The weights are fixed, published, and the same for everyone. The system\u2019s value is that it can\u2019t be influenced by your preferences.",
  },
  {
    question: "What if the system finds nothing worth buying?",
    answer:
      "It tells you. An empty dashboard means the system found nothing meeting its quality threshold in the current market. That\u2019s not a bug \u2014 it\u2019s the most valuable signal we can give. Cash is a position.",
  },
  {
    question: "How often is data updated?",
    answer:
      "Market data refreshes daily. SEC filings are ingested as they\u2019re published. Institutional holdings (13F) update quarterly. Scores recalculate after each data refresh.",
  },
  {
    question: "Do you have a track record?",
    answer:
      "We publish every score in real time with timestamps. You can track what the system scored highly and compare it to actual outcomes over time. We\u2019re building the track record live, in public, starting at launch.",
  },
  {
    question: "What\u2019s the free tier like?",
    answer:
      "Search unlimited tickers and see composite scores, factor breakdowns, and elimination results. Get one full forensic report per month. Enough to understand how the system works before you pay anything.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      "Yes. Cancel in your account settings. Takes effect immediately. No penalties, no calls with a \u201Cretention specialist.\u201D",
  },
  {
    question: "Is my data secure?",
    answer:
      "Yes. JWT authentication, encrypted API keys, rate limiting, security headers, and audit logging. We don\u2019t sell user data. We don\u2019t share your watchlist or search history.",
  },
  {
    question: "Who builds this?",
    answer:
      "A small team of engineers obsessed with removing human bias from investment analysis. We use the system for our own portfolios.",
  },
]

function FaqItem({ item }: { item: FaqEntry }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border-b border-border-subtle">
      <button
        type="button"
        className="w-full flex items-center justify-between py-5 text-left group"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="text-sm font-medium text-text-primary group-hover:text-accent transition-colors pr-4">
          {item.question}
        </span>
        <span
          className="text-text-tertiary shrink-0 transition-transform duration-200"
          style={{ transform: open ? "rotate(45deg)" : "rotate(0deg)" }}
          aria-hidden="true"
        >
          +
        </span>
      </button>
      {open && (
        <p className="text-sm text-text-secondary pb-5 pr-8 leading-relaxed">
          {item.answer}
        </p>
      )}
    </div>
  )
}

export function FaqSection() {
  return (
    <section id="faq" className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <h2 className="font-display text-3xl md:text-4xl text-text-primary text-center mb-16">
          Questions
        </h2>
        <div>
          {FAQ_ITEMS.map((item) => (
            <FaqItem key={item.question} item={item} />
          ))}
        </div>
      </div>
    </section>
  )
}
