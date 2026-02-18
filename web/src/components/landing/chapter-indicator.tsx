"use client"

import { useEffect, useRef, useState } from "react"

const SECTIONS = [
  { id: "signal", label: "The Signal" },
  { id: "engine", label: "The Engine" },
  { id: "path", label: "The Path" },
]

export function ChapterIndicator() {
  const [activeIndex, setActiveIndex] = useState(0)
  const observerRef = useRef<IntersectionObserver | null>(null)

  useEffect(() => {
    const elements = SECTIONS.map(({ id }) => document.getElementById(id)).filter(
      Boolean,
    ) as HTMLElement[]

    if (elements.length === 0) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const index = SECTIONS.findIndex((s) => s.id === entry.target.id)
            if (index !== -1) setActiveIndex(index)
          }
        }
      },
      { threshold: 0.4 },
    )

    for (const el of elements) {
      observerRef.current.observe(el)
    }

    return () => observerRef.current?.disconnect()
  }, [])

  function handleNavigate(index: number) {
    const id = SECTIONS[index]?.id
    if (id) {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth" })
    }
  }

  return (
    <nav
      aria-label="Page chapters"
      className="fixed right-6 top-1/2 -translate-y-1/2 z-50 hidden lg:flex flex-col gap-3"
    >
      {SECTIONS.map((section, i) => (
        <button
          key={section.id}
          data-chapter-dot
          data-active={i === activeIndex ? "true" : "false"}
          aria-label={section.label}
          aria-current={i === activeIndex ? "step" : undefined}
          onClick={() => handleNavigate(i)}
          className={`w-2 h-2 rounded-full transition-all duration-300 ${
            i === activeIndex
              ? "bg-[var(--color-accent)] scale-125"
              : "bg-[var(--color-text-tertiary)] opacity-40 hover:opacity-70"
          }`}
        />
      ))}
    </nav>
  )
}
