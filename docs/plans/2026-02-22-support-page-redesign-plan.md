# Support Page Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current flat support page with a categorized support hub featuring topic cards, accordion FAQs, and context-routed contact emails.

**Architecture:** Single page component (`page.tsx`) as a thin server shell for metadata. All interactive content lives in `web/src/components/support/` — a `SupportPage` client component composed of `TopicCards`, `FaqAccordion`, and `ContactSection`. Accordion state managed with `useState`, single-expand per category.

**Tech Stack:** Next.js 15, React, Tailwind CSS (existing design tokens), Vitest + Testing Library

**Design doc:** `docs/plans/2026-02-22-support-page-redesign-design.md`

---

### Task 1: Create FAQ data file

**Files:**
- Create: `web/src/components/support/support-data.ts`

**Step 1: Create the data file**

This is a plain TypeScript file exporting typed FAQ data and contact card data. No test needed — it's static data with type safety.

```ts
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
```

**Step 2: Commit**

```bash
git add web/src/components/support/support-data.ts
git commit -m "feat(web): add support page FAQ and contact data"
```

---

### Task 2: Create FaqAccordion component with tests

**Files:**
- Create: `web/src/components/support/faq-accordion.tsx`
- Create: `web/src/components/support/__tests__/faq-accordion.test.tsx`

**Step 1: Write the failing tests**

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { FaqAccordion } from "../faq-accordion"
import type { FaqCategory } from "../support-data"

const mockCategories: FaqCategory[] = [
  {
    id: "test-cat",
    title: "Test Category",
    icon: "shield",
    description: "Test description",
    items: [
      { question: "First question?", answer: "First answer." },
      { question: "Second question?", answer: "Second answer." },
    ],
  },
  {
    id: "other-cat",
    title: "Other Category",
    icon: "chart",
    description: "Other description",
    items: [{ question: "Other question?", answer: "Other answer." }],
  },
]

describe("FaqAccordion", () => {
  it("renders all category headings", () => {
    render(<FaqAccordion categories={mockCategories} />)
    expect(screen.getByText("Test Category")).toBeInTheDocument()
    expect(screen.getByText("Other Category")).toBeInTheDocument()
  })

  it("renders all questions", () => {
    render(<FaqAccordion categories={mockCategories} />)
    expect(screen.getByText("First question?")).toBeInTheDocument()
    expect(screen.getByText("Second question?")).toBeInTheDocument()
    expect(screen.getByText("Other question?")).toBeInTheDocument()
  })

  it("hides answers by default", () => {
    render(<FaqAccordion categories={mockCategories} />)
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument()
  })

  it("shows answer when question is clicked", async () => {
    const user = userEvent.setup()
    render(<FaqAccordion categories={mockCategories} />)
    await user.click(screen.getByText("First question?"))
    expect(screen.getByText("First answer.")).toBeInTheDocument()
  })

  it("collapses previous answer in same category when another is clicked", async () => {
    const user = userEvent.setup()
    render(<FaqAccordion categories={mockCategories} />)
    await user.click(screen.getByText("First question?"))
    expect(screen.getByText("First answer.")).toBeInTheDocument()
    await user.click(screen.getByText("Second question?"))
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument()
    expect(screen.getByText("Second answer.")).toBeInTheDocument()
  })

  it("collapses answer when same question is clicked again", async () => {
    const user = userEvent.setup()
    render(<FaqAccordion categories={mockCategories} />)
    await user.click(screen.getByText("First question?"))
    expect(screen.getByText("First answer.")).toBeInTheDocument()
    await user.click(screen.getByText("First question?"))
    expect(screen.queryByText("First answer.")).not.toBeInTheDocument()
  })

  it("allows independent open state across categories", async () => {
    const user = userEvent.setup()
    render(<FaqAccordion categories={mockCategories} />)
    await user.click(screen.getByText("First question?"))
    await user.click(screen.getByText("Other question?"))
    expect(screen.getByText("First answer.")).toBeInTheDocument()
    expect(screen.getByText("Other answer.")).toBeInTheDocument()
  })

  it("sets id attributes on category sections for anchor linking", () => {
    const { container } = render(<FaqAccordion categories={mockCategories} />)
    expect(container.querySelector("#faq-test-cat")).toBeInTheDocument()
    expect(container.querySelector("#faq-other-cat")).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/support/__tests__/faq-accordion.test.tsx`
Expected: FAIL — module not found

**Step 3: Implement FaqAccordion**

```tsx
"use client"

import { useState } from "react"
import type { FaqCategory } from "./support-data"

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={`text-text-tertiary transition-transform duration-200 ${open ? "rotate-180" : ""}`}
    >
      <path
        d="M4 6L8 10L12 6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function FaqAccordion({ categories }: { categories: FaqCategory[] }) {
  // Track open item per category: { [categoryId]: questionIndex | null }
  const [openItems, setOpenItems] = useState<Record<string, number | null>>({})

  function toggle(categoryId: string, index: number) {
    setOpenItems((prev) => ({
      ...prev,
      [categoryId]: prev[categoryId] === index ? null : index,
    }))
  }

  return (
    <div className="space-y-12">
      {categories.map((category) => (
        <section key={category.id} id={`faq-${category.id}`}>
          <h2 className="heading-3 text-text-primary mb-4">{category.title}</h2>
          <div className="border border-border-primary rounded-lg divide-y divide-border-subtle overflow-hidden">
            {category.items.map((item, index) => {
              const isOpen = openItems[category.id] === index
              return (
                <div key={index}>
                  <button
                    onClick={() => toggle(category.id, index)}
                    className="w-full flex items-center justify-between px-5 py-4 text-left text-text-primary hover:bg-bg-secondary transition-colors"
                    aria-expanded={isOpen}
                  >
                    <span className="text-[14px] sm:text-[15px] font-medium pr-4">
                      {item.question}
                    </span>
                    <ChevronIcon open={isOpen} />
                  </button>
                  {isOpen && (
                    <div className="px-5 pb-4 text-[14px] text-text-secondary leading-relaxed">
                      {item.answer}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/support/__tests__/faq-accordion.test.tsx`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/support/faq-accordion.tsx web/src/components/support/__tests__/faq-accordion.test.tsx
git commit -m "feat(web): add FaqAccordion component with tests"
```

---

### Task 3: Create TopicCards component with tests

**Files:**
- Create: `web/src/components/support/topic-cards.tsx`
- Create: `web/src/components/support/__tests__/topic-cards.test.tsx`

**Step 1: Write the failing tests**

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { TopicCards } from "../topic-cards"
import type { FaqCategory } from "../support-data"

const mockCategories: FaqCategory[] = [
  {
    id: "account",
    title: "Account & Access",
    icon: "shield",
    description: "Login issues and account settings",
    items: [],
  },
  {
    id: "scores",
    title: "Scores & Data",
    icon: "chart",
    description: "How scores update",
    items: [],
  },
]

describe("TopicCards", () => {
  it("renders all category titles", () => {
    render(<TopicCards categories={mockCategories} />)
    expect(screen.getByText("Account & Access")).toBeInTheDocument()
    expect(screen.getByText("Scores & Data")).toBeInTheDocument()
  })

  it("renders all category descriptions", () => {
    render(<TopicCards categories={mockCategories} />)
    expect(screen.getByText("Login issues and account settings")).toBeInTheDocument()
    expect(screen.getByText("How scores update")).toBeInTheDocument()
  })

  it("renders anchor links to FAQ sections", () => {
    render(<TopicCards categories={mockCategories} />)
    const links = screen.getAllByRole("link")
    expect(links[0]).toHaveAttribute("href", "#faq-account")
    expect(links[1]).toHaveAttribute("href", "#faq-scores")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/support/__tests__/topic-cards.test.tsx`
Expected: FAIL — module not found

**Step 3: Implement TopicCards**

```tsx
import type { FaqCategory } from "./support-data"

const icons: Record<FaqCategory["icon"], React.ReactNode> = {
  shield: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-accent">
      <path
        d="M12 3L4 7V12C4 16.4 7.4 20.5 12 21.5C16.6 20.5 20 16.4 20 12V7L12 3Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  chart: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-accent">
      <path
        d="M8 17V10M12 17V7M16 17V13M4 21H20"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  card: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-accent">
      <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3 10H21" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  fingerprint: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-accent">
      <path
        d="M12 10V14M8 12C8 9.8 9.8 8 12 8S16 9.8 16 12M5 12C5 8.1 8.1 5 12 5S19 8.1 19 12M12 18C9.2 18 7 15.8 7 13M17 13C17 15.8 14.8 18 12 18"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
}

export function TopicCards({ categories }: { categories: FaqCategory[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {categories.map((category) => (
        <a
          key={category.id}
          href={`#faq-${category.id}`}
          className="p-5 border border-border-primary rounded-lg bg-bg-elevated hover:border-accent/40 transition-colors group"
        >
          <div className="mb-3">{icons[category.icon]}</div>
          <h3 className="text-[15px] font-semibold text-text-primary mb-1 group-hover:text-accent transition-colors">
            {category.title}
          </h3>
          <p className="text-[13px] text-text-tertiary leading-relaxed">
            {category.description}
          </p>
        </a>
      ))}
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/support/__tests__/topic-cards.test.tsx`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/support/topic-cards.tsx web/src/components/support/__tests__/topic-cards.test.tsx
git commit -m "feat(web): add TopicCards component with tests"
```

---

### Task 4: Create ContactSection component with tests

**Files:**
- Create: `web/src/components/support/contact-section.tsx`
- Create: `web/src/components/support/__tests__/contact-section.test.tsx`

**Step 1: Write the failing tests**

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ContactSection } from "../contact-section"
import type { ContactCard } from "../support-data"

const mockCards: ContactCard[] = [
  {
    title: "General Support",
    email: "support@margin-invest.com",
    description: "Platform questions",
  },
  {
    title: "Security",
    email: "security@margin-invest.com",
    description: "Vulnerability reports",
  },
]

describe("ContactSection", () => {
  it("renders the heading", () => {
    render(<ContactSection cards={mockCards} />)
    expect(screen.getByText("Still need help?")).toBeInTheDocument()
  })

  it("renders all contact card titles", () => {
    render(<ContactSection cards={mockCards} />)
    expect(screen.getByText("General Support")).toBeInTheDocument()
    expect(screen.getByText("Security")).toBeInTheDocument()
  })

  it("renders mailto links for each email", () => {
    render(<ContactSection cards={mockCards} />)
    const links = screen.getAllByRole("link")
    const mailtoLinks = links.filter((l) => l.getAttribute("href")?.startsWith("mailto:"))
    expect(mailtoLinks).toHaveLength(2)
    expect(mailtoLinks[0]).toHaveAttribute("href", "mailto:support@margin-invest.com")
    expect(mailtoLinks[1]).toHaveAttribute("href", "mailto:security@margin-invest.com")
  })

  it("renders descriptions", () => {
    render(<ContactSection cards={mockCards} />)
    expect(screen.getByText("Platform questions")).toBeInTheDocument()
    expect(screen.getByText("Vulnerability reports")).toBeInTheDocument()
  })

  it("renders the status page link", () => {
    render(<ContactSection cards={mockCards} />)
    const statusLink = screen.getByRole("link", { name: /system status/i })
    expect(statusLink).toHaveAttribute("href", "https://status.margin-invest.com")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/support/__tests__/contact-section.test.tsx`
Expected: FAIL — module not found

**Step 3: Implement ContactSection**

```tsx
import type { ContactCard } from "./support-data"

export function ContactSection({ cards }: { cards: ContactCard[] }) {
  return (
    <section>
      <h2 className="heading-3 text-text-primary mb-2">Still need help?</h2>
      <p className="text-[14px] text-text-secondary mb-6">
        If you couldn&apos;t find what you were looking for, reach out directly.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {cards.map((card) => (
          <div
            key={card.email}
            className="p-5 border border-border-primary rounded-lg bg-bg-elevated"
          >
            <h3 className="text-[15px] font-semibold text-text-primary mb-1">{card.title}</h3>
            <p className="text-[13px] text-text-tertiary mb-3">{card.description}</p>
            <a
              href={`mailto:${card.email}`}
              className="text-[13px] text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
            >
              {card.email}
            </a>
          </div>
        ))}
      </div>
      <p className="text-[13px] text-text-tertiary">
        Check our{" "}
        <a
          href="https://status.margin-invest.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
        >
          system status
        </a>{" "}
        page for real-time platform availability.
      </p>
    </section>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/support/__tests__/contact-section.test.tsx`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/support/contact-section.tsx web/src/components/support/__tests__/contact-section.test.tsx
git commit -m "feat(web): add ContactSection component with tests"
```

---

### Task 5: Create barrel export and assemble page

**Files:**
- Create: `web/src/components/support/index.ts`
- Modify: `web/src/app/support/page.tsx` (full replacement)

**Step 1: Create barrel export**

```ts
export { TopicCards } from "./topic-cards"
export { FaqAccordion } from "./faq-accordion"
export { ContactSection } from "./contact-section"
export { faqCategories, contactCards } from "./support-data"
```

**Step 2: Replace the page component**

Replace the entire contents of `web/src/app/support/page.tsx`:

```tsx
import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"
import { TopicCards, FaqAccordion, ContactSection, faqCategories, contactCards } from "@/components/support"

export const metadata: Metadata = {
  title: "Support | Margin Invest",
  description:
    "Get help with Margin Invest — account access, scoring questions, billing, security, and contact information.",
}

export default function SupportPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <div className="text-center mb-12">
            <h1 className="heading-2 text-text-primary mb-3">How can we help?</h1>
            <p className="body-text text-text-secondary">
              Find answers to common questions or reach out to our team directly.
            </p>
          </div>

          <div className="mb-16">
            <TopicCards categories={faqCategories} />
          </div>

          <div className="mb-16">
            <FaqAccordion categories={faqCategories} />
          </div>

          <div className="mb-12">
            <ContactSection cards={contactCards} />
          </div>

          <div className="pt-8 border-t border-border-subtle">
            <Link
              href="/"
              className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
            >
              &larr; Back to home
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
```

**Step 3: Verify the dev server renders the page**

Run: `cd web && npx next build` (or open `http://localhost:3000/support` if dev server is running)
Expected: Page renders without errors

**Step 4: Commit**

```bash
git add web/src/components/support/index.ts web/src/app/support/page.tsx
git commit -m "feat(web): assemble redesigned support page"
```

---

### Task 6: Add page-level integration test

**Files:**
- Create: `web/src/components/support/__tests__/support-page.test.tsx`

**Step 1: Write the integration test**

This test renders the full assembled component tree (minus `Navbar` and Next.js metadata) to verify everything wires together.

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { TopicCards, FaqAccordion, ContactSection, faqCategories, contactCards } from "../index"

describe("Support page integration", () => {
  function renderSupportContent() {
    return render(
      <>
        <TopicCards categories={faqCategories} />
        <FaqAccordion categories={faqCategories} />
        <ContactSection cards={contactCards} />
      </>
    )
  }

  it("renders all four topic cards", () => {
    renderSupportContent()
    expect(screen.getByText("Account & Access")).toBeInTheDocument()
    expect(screen.getByText("Scores & Data")).toBeInTheDocument()
    expect(screen.getByText("Billing & Subscription")).toBeInTheDocument()
    expect(screen.getByText("Security & Privacy")).toBeInTheDocument()
  })

  it("renders all FAQ questions from real data", () => {
    renderSupportContent()
    for (const category of faqCategories) {
      for (const item of category.items) {
        expect(screen.getByText(item.question)).toBeInTheDocument()
      }
    }
  })

  it("accordion opens and shows answer from real data", async () => {
    const user = userEvent.setup()
    renderSupportContent()
    await user.click(screen.getByText("I can't log in to my account"))
    expect(screen.getByText(/Check that your email and password are correct/)).toBeInTheDocument()
  })

  it("renders all three contact cards with mailto links", () => {
    renderSupportContent()
    expect(screen.getByText("support@margin-invest.com")).toBeInTheDocument()
    expect(screen.getByText("security@margin-invest.com")).toBeInTheDocument()
    expect(screen.getByText("legal@margin-invest.com")).toBeInTheDocument()
  })

  it("renders status page link", () => {
    renderSupportContent()
    expect(screen.getByRole("link", { name: /system status/i })).toHaveAttribute(
      "href",
      "https://status.margin-invest.com"
    )
  })

  it("topic cards link to correct FAQ sections", () => {
    renderSupportContent()
    const links = screen.getAllByRole("link").filter((l) => l.getAttribute("href")?.startsWith("#"))
    expect(links).toHaveLength(4)
    expect(links.map((l) => l.getAttribute("href"))).toEqual([
      "#faq-account",
      "#faq-scores",
      "#faq-billing",
      "#faq-security",
    ])
  })
})
```

**Step 2: Run the full test suite**

Run: `cd web && npx vitest run src/components/support/`
Expected: All tests pass (unit + integration)

**Step 3: Commit**

```bash
git add web/src/components/support/__tests__/support-page.test.tsx
git commit -m "test(web): add support page integration tests"
```

---

### Task Summary

| Task | Component | Tests |
|------|-----------|-------|
| 1 | `support-data.ts` — FAQ + contact data | Type-checked, no runtime tests needed |
| 2 | `faq-accordion.tsx` — Accordion with single-expand per category | 7 tests |
| 3 | `topic-cards.tsx` — 2x2 grid with anchor links | 3 tests |
| 4 | `contact-section.tsx` — Contact cards + status link | 5 tests |
| 5 | `index.ts` + `page.tsx` — Barrel export + assembled page | Build verification |
| 6 | `support-page.test.tsx` — Integration test | 6 tests |
