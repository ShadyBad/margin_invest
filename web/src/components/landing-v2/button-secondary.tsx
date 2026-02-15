import { type ReactNode } from "react"
import Link from "next/link"

interface ButtonSecondaryProps {
  children: ReactNode
  href: string
}

export function ButtonSecondary({ children, href }: ButtonSecondaryProps) {
  return (
    <Link
      href={href}
      className="text-[15px] font-medium text-text-secondary hover:text-text-primary transition-colors underline-offset-4 hover:underline"
    >
      {children}
    </Link>
  )
}
