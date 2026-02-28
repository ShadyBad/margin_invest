import Link from "next/link"

const footerLinks = [
  { href: "/support", label: "Support" },
  { href: "/methodology", label: "Methodology" },
  { href: "/legal", label: "Legal" },
  { href: "/terms", label: "Terms" },
  { href: "/privacy", label: "Privacy" },
  { href: "/security", label: "Security" },
  { href: "/api-docs", label: "API" },
  { href: "/contact", label: "Contact" },
]

export function Footer() {
  return (
    <footer className="border-t border-border-subtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col sm:flex-row items-center sm:justify-between gap-4 text-[12px] text-text-tertiary">
        <nav className="flex items-center gap-6" aria-label="Footer">
          {footerLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="hover:text-text-secondary transition-colors duration-200"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <span>&copy; {new Date().getFullYear()} Margin Invest</span>
      </div>
    </footer>
  )
}
