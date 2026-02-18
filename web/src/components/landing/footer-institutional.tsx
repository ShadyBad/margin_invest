import Link from "next/link"

const links = [
  { href: "/support", label: "Support" },
  { href: "/methodology", label: "Methodology" },
  { href: "/security", label: "Security" },
  { href: "/legal", label: "Legal" },
  { href: "/status", label: "Status" },
  { href: "/api", label: "API" },
  { href: "/support", label: "Contact" },
]

export function FooterInstitutional() {
  return (
    <footer className="border-t border-border-subtle py-12">
      <div className="max-w-6xl mx-auto px-6">
        <nav className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 mb-8" aria-label="Footer">
          {links.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-xs text-text-tertiary hover:text-text-secondary transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <p className="text-center text-[11px] text-text-tertiary">
          &copy; {new Date().getFullYear()} Margin Invest &middot;{" "}
          <span className="font-mono">Engine v1.3.2</span>
        </p>
      </div>
    </footer>
  )
}
