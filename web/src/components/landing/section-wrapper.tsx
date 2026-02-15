import { type ReactNode } from "react"

interface SectionWrapperProps {
  children: ReactNode
  id?: string
  className?: string
  padding?: string
}

export function SectionWrapper({
  children,
  id,
  className,
  padding = "py-24",
}: SectionWrapperProps) {
  return (
    <section id={id} className={`${padding} ${className ?? ""}`.trim()}>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{ maxWidth: "1280px", paddingLeft: "8vw", paddingRight: "8vw" }}
      >
        {children}
      </div>
    </section>
  )
}
