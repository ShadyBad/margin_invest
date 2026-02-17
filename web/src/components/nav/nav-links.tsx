import Link from "next/link"
import type { NavLink } from "@/hooks/use-navigation"

interface NavLinksProps {
  links: NavLink[]
}

export function NavLinks({ links }: NavLinksProps) {
  return (
    <div className="hidden md:flex items-center gap-8">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={`text-[14px] font-medium tracking-[-0.01em] transition-colors duration-200 ease-out ${
            link.isActive
              ? "text-text-primary"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          {link.label}
        </Link>
      ))}
    </div>
  )
}
