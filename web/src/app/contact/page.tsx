import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"
import { ContactForm } from "@/components/contact"

export const metadata: Metadata = {
  title: "Contact | Margin Invest",
  description:
    "Get in touch with Margin Invest — support, security reports, legal inquiries, and business partnerships.",
  alternates: { canonical: "https://margin-invest.com/contact" },
}

const channels = [
  {
    title: "General Support",
    email: "support@margin-invest.com",
    description: "Platform questions, account help, billing issues",
    sla: "Within 24 hours",
  },
  {
    title: "Security",
    email: "security@margin-invest.com",
    description: "Vulnerability reports, suspicious activity",
    sla: "Within 48 hours",
  },
  {
    title: "Legal & Privacy",
    email: "legal@margin-invest.com",
    description: "Data deletion, compliance, legal notices",
    sla: "Within 5 business days",
  },
  {
    title: "Business & Partnerships",
    email: "partnerships@margin-invest.com",
    description: "Enterprise inquiries, API partnerships, data licensing",
    sla: "Within 3 business days",
  },
]

const quickLinks = [
  { label: "Looking for answers? Visit Support", href: "/support" },
  { label: "Security practices", href: "/security" },
  { label: "API documentation", href: "/api-docs" },
  { label: "Legal & terms", href: "/legal" },
]

export default function ContactPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <h1 className="heading-2 text-text-primary mb-4">Get in Touch</h1>
          <p className="body-text text-text-secondary mb-12">
            Whether you&apos;re a developer, investor, or researcher — we&apos;ll route you to
            the right person.
          </p>

          <div className="space-y-12">
            <section>
              <h2 className="heading-3 text-text-primary mb-4">Contact Channels</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {channels.map((ch) => (
                  <div
                    key={ch.email}
                    className="p-5 border border-border-primary rounded-lg bg-bg-elevated"
                  >
                    <h3 className="text-[15px] font-semibold text-text-primary mb-1">
                      {ch.title}
                    </h3>
                    <p className="text-[13px] text-text-tertiary mb-2">{ch.description}</p>
                    <a
                      href={`mailto:${ch.email}`}
                      className="text-[13px] text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                    >
                      {ch.email}
                    </a>
                    <p className="text-[12px] text-text-tertiary mt-2">{ch.sla}</p>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Send a Message</h2>
              <ContactForm />
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Availability</h2>
              <ul className="list-disc list-inside space-y-2 text-[14px] text-text-tertiary">
                <li>Support hours: Monday–Friday, 9 AM – 6 PM ET</li>
                <li>Security reports: Monitored 7 days a week</li>
                <li>
                  System health:{" "}
                  <Link
                    href="/status"
                    className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                  >
                    check platform status
                  </Link>
                </li>
              </ul>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Quick Links</h2>
              <ul className="space-y-2">
                {quickLinks.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-[14px] text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          </div>

          <div className="mt-16 pt-8 border-t border-border-subtle">
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
