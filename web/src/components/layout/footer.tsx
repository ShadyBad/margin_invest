import Link from "next/link"

const footerLinks = [
  { href: "/support", label: "Support" },
  { href: "/methodology", label: "Methodology" },
  { href: "/legal", label: "Legal" },
]

export function Footer() {
  return (
    <footer className="border-t border-border-subtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-wrap items-center justify-center gap-6 text-[12px] text-text-tertiary">
        {footerLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="hover:text-text-secondary transition-colors duration-200"
          >
            {link.label}
          </Link>
        ))}
        <span>&copy; {new Date().getFullYear()} Margin</span>
      </div>
    </footer>
  )
}
