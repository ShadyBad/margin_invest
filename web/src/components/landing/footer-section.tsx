import Link from "next/link"

const productLinks = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Guides", href: "/guides" },
  { label: "Methodology", href: "/methodology" },
  { label: "API", href: "/api-docs" },
  { label: "Status", href: "/status" },
]

const companyLinks = [
  { label: "Legal", href: "/legal" },
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
  { label: "Security", href: "/security" },
  { label: "Contact", href: "/contact" },
  { label: "Support", href: "/support" },
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
    <footer id="footer">
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

      {/* Main footer */}
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr] gap-10">
          {/* Brand column */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="font-display text-lg text-text-primary">Margin Invest</span>
            </div>
            <p className="text-sm text-text-secondary max-w-xs leading-relaxed mb-4">
              A deterministic capital allocation system. Structure replaces narrative. Math replaces opinion.
            </p>
            <div className="font-mono text-[10px] text-text-tertiary">
              Deterministic scoring engine
            </div>
          </div>

          {/* Product column */}
          <div>
            <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">
              Product
            </h4>
            <nav className="flex flex-col gap-2">
              {productLinks.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  className="text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Company column */}
          <div>
            <h4 className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">
              Company
            </h4>
            <nav className="flex flex-col gap-2">
              {companyLinks.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  className="text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 pt-6 border-t border-border-subtle flex flex-col md:flex-row justify-between items-center gap-3">
          <p className="text-xs text-text-tertiary">
            &copy; 2026 Margin Invest. All rights reserved.
          </p>
          <p className="text-[10px] font-mono text-text-tertiary">
            Built on verified public data and deterministic scoring architecture.
          </p>
        </div>
      </div>
    </footer>
  )
}
