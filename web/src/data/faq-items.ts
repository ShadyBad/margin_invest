export interface FaqEntry {
  question: string
  answer: string
}

export const FAQ_ITEMS: FaqEntry[] = [
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
    question: "What are the elimination filters?",
    answer:
      "Six forensic screens including: Beneish M-Score (earnings manipulation detection), Altman Z-Score (bankruptcy probability), penny stock exclusion, delisting detection, minimum liquidity thresholds, and data sufficiency requirements. 70%+ of US equities fail at least one filter.",
  },
  {
    question: 'What does "sector-neutral" mean?',
    answer:
      "We compare stocks to their sector peers, not to the entire market. A bank with 15% ROIC is excellent \u2014 among banks. A tech company with 15% ROIC is below average \u2014 among tech. Sector-neutral scoring prevents false comparisons.",
  },
  {
    question: "Do you have a track record?",
    answer:
      "We publish every score in real time with timestamps. You can track what the system scored highly and compare it to actual outcomes over time. We\u2019re building the track record live, in public, starting at launch.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      "Yes. Cancel in your account settings. Takes effect immediately. No penalties, no calls with a \u201Cretention specialist.\u201D",
  },
]
