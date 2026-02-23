export interface FaqItem {
  question: string
  answer: string
}

export interface FaqCategory {
  id: string
  title: string
  icon: "shield" | "chart" | "card" | "fingerprint"
  description: string
  items: FaqItem[]
}

export interface ContactCard {
  title: string
  email: string
  description: string
}

export const faqCategories: FaqCategory[] = [
  {
    id: "account",
    title: "Account & Access",
    icon: "shield",
    description: "Login issues, email verification, MFA, and account settings",
    items: [
      {
        question: "I can't log in to my account",
        answer:
          "Check that your email and password are correct, clear your browser cache, and try again in an incognito window. If you have MFA enabled, make sure your authenticator app is synced. If the issue persists, contact support@margin-invest.com.",
      },
      {
        question: "How do I reset my password?",
        answer:
          'Click "Forgot password" on the login page. A reset link will be sent to your registered email address. If you don\'t see it within a few minutes, check your spam folder.',
      },
      {
        question: "How do I enable or disable MFA?",
        answer:
          "Go to Account Settings > Security. You can enable TOTP-based multi-factor authentication with any standard authenticator app.",
      },
      {
        question: "How do I update my email address?",
        answer:
          "Contact support@margin-invest.com from your currently registered email address to request a change.",
      },
    ],
  },
  {
    id: "scores",
    title: "Scores & Data",
    icon: "chart",
    description: "How scores update, missing data, methodology questions",
    items: [
      {
        question: "How often are scores updated?",
        answer:
          "Scores refresh periodically based on data source reporting cycles. Real-time price data updates more frequently than fundamental metrics like earnings or balance sheet figures.",
      },
      {
        question: "Why is a company missing from the platform?",
        answer:
          "The scoring engine requires a minimum set of financial data to produce reliable results. Companies with insufficient reporting history may not pass the elimination filters.",
      },
      {
        question: "Why does a metric show as unavailable?",
        answer:
          "Some securities lack the reporting depth needed for certain calculations. This is expected for newer listings or foreign-domiciled companies.",
      },
      {
        question: "Where can I learn how scoring works?",
        answer:
          "Visit the How It Works page for a full breakdown of the pipeline — from elimination filters through multi-factor scoring to conviction ranking.",
      },
    ],
  },
  {
    id: "billing",
    title: "Billing & Subscription",
    icon: "card",
    description: "Plan details, payment questions, cancellations",
    items: [
      {
        question: "What plans are available?",
        answer:
          "Visit the pricing page for current plan details and feature comparisons.",
      },
      {
        question: "How do I cancel my subscription?",
        answer:
          "Go to Account Settings > Subscription. Cancellation takes effect at the end of your current billing period. You'll retain access until then.",
      },
      {
        question: "I was charged incorrectly",
        answer:
          "Contact support@margin-invest.com with your account email and a description of the charge in question. We'll investigate and resolve it promptly.",
      },
    ],
  },
  {
    id: "security",
    title: "Security & Privacy",
    icon: "fingerprint",
    description: "Data protection, vulnerability reporting, privacy practices",
    items: [
      {
        question: "How is my data protected?",
        answer:
          "All data is encrypted at rest and in transit. We do not sell personal data to third parties. For full details, see our legal page.",
      },
      {
        question: "I want to report a security vulnerability",
        answer:
          "Email security@margin-invest.com with details of the vulnerability. We take all reports seriously and will respond within 48 hours.",
      },
      {
        question: "How do I request deletion of my data?",
        answer:
          "Email legal@margin-invest.com from your registered email address. We process deletion requests in accordance with applicable privacy regulations.",
      },
    ],
  },
]

export const contactCards: ContactCard[] = [
  {
    title: "General Support",
    email: "support@margin-invest.com",
    description: "Platform questions, account help, billing issues",
  },
  {
    title: "Security",
    email: "security@margin-invest.com",
    description: "Vulnerability reports, suspicious activity",
  },
  {
    title: "Legal & Privacy",
    email: "legal@margin-invest.com",
    description: "Data deletion requests, legal inquiries, privacy questions",
  },
]
