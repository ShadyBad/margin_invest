import Link from "next/link"
import { LogoIcon } from "@/components/ui/logo-icon"

interface NavLogoProps {
  href: string
}

export function NavLogo({ href }: NavLogoProps) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2 text-text-primary opacity-80 hover:opacity-100 transition-opacity duration-200"
      aria-label="Margin Invest home"
    >
      <LogoIcon />
      <span
        className="hidden md:inline font-display opacity-90"
        style={{ fontSize: '15px', color: 'var(--color-text-primary)' }}
      >
        Margin Invest
      </span>
    </Link>
  )
}
