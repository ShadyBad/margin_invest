import { type ReactNode } from "react"
import Link from "next/link"

interface ButtonPrimaryProps {
  children: ReactNode
  href: string
  size?: "default" | "large"
}

export function ButtonPrimary({
  children,
  href,
  size = "default",
}: ButtonPrimaryProps) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center bg-accent text-white font-semibold text-[15px] rounded-[6px] hover:bg-accent-hover transition-all hover:shadow-[0_0_20px_rgba(26,122,90,0.2)] px-6 ${
        size === "large" ? "h-14" : "h-12"
      }`}
    >
      {children}
    </Link>
  )
}
