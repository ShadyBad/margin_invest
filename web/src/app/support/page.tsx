import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"
import { PageHeader } from "@/components/shared/page-header"
import {
  TopicCards,
  FaqAccordion,
  ContactSection,
  faqCategories,
  contactCards,
} from "@/components/support"

export const metadata: Metadata = {
  title: "Support | Margin Invest",
  description:
    "Get help with Margin Invest -- account access, scoring questions, billing, security, and contact information.",
}

export default function SupportPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <PageHeader
            category="SUPPORT"
            title="How can we help?"
            description="Find answers to common questions or reach out to our team directly."
          />

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
