import Link from "next/link"

function LogoIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      stroke="currentColor"
      aria-hidden="true"
    >
      <polyline points="2,16 6,6 10,12 14,4 18,16" />
    </svg>
  )
}

interface NavLogoProps {
  href: string
}

export function NavLogo({ href }: NavLogoProps) {
  return (
    <Link
      href={href}
      className="text-text-primary opacity-80 hover:opacity-100 transition-opacity duration-200"
      aria-label="Margin Invest home"
    >
      <LogoIcon />
    </Link>
  )
}
