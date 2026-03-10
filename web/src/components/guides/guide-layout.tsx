import type { ReactNode } from "react"
import type { TocHeading } from "@/lib/guides"
import { TableOfContents } from "./table-of-contents"

interface GuideLayoutProps {
  children: ReactNode
  headings: TocHeading[]
}

export function GuideLayout({ children, headings }: GuideLayoutProps) {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="lg:grid lg:grid-cols-[1fr_220px] lg:gap-12">
        <article className="min-w-0 max-w-3xl">{children}</article>
        <aside className="hidden lg:block">
          <div className="sticky top-24">
            <TableOfContents headings={headings} />
          </div>
        </aside>
      </div>
    </div>
  )
}
