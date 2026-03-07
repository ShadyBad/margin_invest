import Link from "next/link"
import { ENGINE_VERSION } from "./candidate-data"

const navLinks = [
  { label: "Support", href: "/support" },
  { label: "Methodology", href: "/methodology" },
  { label: "Security", href: "/security" },
  { label: "Legal", href: "/legal" },
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
  { label: "Status", href: "/status" },
  { label: "API", href: "/api-docs" },
  { label: "Contact", href: "/contact" },
]

const trustBadges = [
  "SEC Filings + Earnings Transcripts",
  "Daily Market Data Refresh",
  "Encrypted API Key Storage",
  "Deterministic Scoring",
  "No Hidden Heuristics",
]

export function FooterSection() {
  return (
    <footer id="footer" className="border-t border-border-subtle">
      {/* Trust strip */}
      <div className="max-w-6xl mx-auto px-6 py-8 border-b border-border-subtle">
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          {trustBadges.map((badge) => (
            <span key={badge} className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-tertiary">
              {badge}
            </span>
          ))}
        </div>
      </div>
      <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row justify-between gap-8">
        <nav className="flex flex-wrap gap-x-6 gap-y-2">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="font-mono text-xs text-text-tertiary md:text-right">
          <div>Engine {ENGINE_VERSION}</div>
          <div>&copy; 2026 Margin Invest</div>
        </div>
      </div>
    </footer>
  )
}
