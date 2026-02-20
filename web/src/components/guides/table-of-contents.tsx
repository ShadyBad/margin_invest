"use client"

import { useEffect, useRef, useState } from "react"
import type { TocHeading } from "@/lib/guides"

interface TableOfContentsProps {
  headings: TocHeading[]
}

export function TableOfContents({ headings }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>("")
  const observerRef = useRef<IntersectionObserver | null>(null)

  useEffect(() => {
    if (headings.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id)
          }
        }
      },
      { rootMargin: "-96px 0px -80% 0px", threshold: 0 },
    )

    observerRef.current = observer

    for (const heading of headings) {
      const element = document.getElementById(heading.id)
      if (element) {
        observer.observe(element)
      }
    }

    return () => {
      observer.disconnect()
    }
  }, [headings])

  if (headings.length === 0) {
    return null
  }

  function handleClick(e: React.MouseEvent<HTMLAnchorElement>, id: string) {
    e.preventDefault()
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: "smooth" })
    }
    setActiveId(id)
  }

  return (
    <nav>
      <p className="mb-3 text-[13px] font-semibold uppercase tracking-wider text-text-primary">
        On this page
      </p>
      <ul className="space-y-2">
        {headings.map((heading) => (
          <li key={heading.id} className={heading.level === 3 ? "pl-4" : ""}>
            <a
              href={`#${heading.id}`}
              onClick={(e) => handleClick(e, heading.id)}
              className={`text-sm transition-colors duration-200 ${
                activeId === heading.id
                  ? "font-medium text-accent"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
            >
              {heading.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
