"use client"

import { useEffect, useRef, useState } from "react"

const SECTIONS = [
  { id: "hero", label: "Hero" },
  { id: "pricing", label: "Pricing" },
  { id: "faq", label: "FAQ" },
  { id: "footer", label: "Footer" },
]

export function SectionIndicator() {
  const [activeIndex, setActiveIndex] = useState(0)
  const observerRef = useRef<IntersectionObserver | null>(null)

  useEffect(() => {
    const elements = SECTIONS.map(({ id }) => document.getElementById(id)).filter(Boolean) as HTMLElement[]
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
      { threshold: 0.3 },
    )

    for (const el of elements) observerRef.current.observe(el)
    return () => observerRef.current?.disconnect()
  }, [])

  if (process.env.NODE_ENV === 'production') return null
  if (!process.env.NEXT_PUBLIC_SHOW_DEV_TOOLS) return null

  function handleNavigate(index: number) {
    const id = SECTIONS[index]?.id
    if (id) document.getElementById(id)?.scrollIntoView({ behavior: "smooth" })
  }

  return (
    <nav
      aria-label="Page sections"
      className="fixed right-6 top-1/2 -translate-y-1/2 z-50 hidden lg:flex flex-col gap-2"
    >
      {SECTIONS.map((section, i) => (
        <button
          key={section.id}
          aria-label={section.label}
          aria-current={i === activeIndex ? "step" : undefined}
          onClick={() => handleNavigate(i)}
          className={`w-1.5 h-1.5 rounded-full transition-all duration-200 ${
            i === activeIndex
              ? "bg-accent scale-150"
              : "bg-text-tertiary opacity-30 hover:opacity-60"
          }`}
        />
      ))}
    </nav>
  )
}
