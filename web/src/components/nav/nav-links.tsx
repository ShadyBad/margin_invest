import Link from "next/link"
import type { NavLink } from "@/hooks/use-navigation"

interface NavLinksProps {
  links: NavLink[]
}

export function NavLinks({ links }: NavLinksProps) {
  return (
    <div className="flex items-center gap-8">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={`relative text-[14px] font-medium tracking-[-0.01em] transition-colors duration-200 ease-out after:absolute after:left-0 after:-bottom-1 after:h-[1.5px] after:w-full after:origin-center after:scale-x-0 after:bg-text-primary after:transition-transform after:duration-300 after:ease-out ${
            link.isActive
              ? "text-text-primary after:scale-x-100"
              : "text-text-secondary hover:text-text-primary hover:after:scale-x-100 hover:after:opacity-50"
          }`}
        >
          {link.label}
        </Link>
      ))}
    </div>
  )
}
