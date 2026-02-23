"use client"

import { useState } from "react"
import type { FaqCategory } from "./support-data"

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={`text-text-tertiary transition-transform duration-200 ${open ? "rotate-180" : ""}`}
    >
      <path
        d="M4 6L8 10L12 6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function FaqAccordion({ categories }: { categories: FaqCategory[] }) {
  const [openItems, setOpenItems] = useState<Record<string, number | null>>({})

  function toggle(categoryId: string, index: number) {
    setOpenItems((prev) => ({
      ...prev,
      [categoryId]: prev[categoryId] === index ? null : index,
    }))
  }

  return (
    <div className="space-y-12">
      {categories.map((category) => (
        <section key={category.id} id={`faq-${category.id}`}>
          <h2 className="heading-3 text-text-primary mb-4">{category.title}</h2>
          <div className="border border-border-primary rounded-lg divide-y divide-border-subtle overflow-hidden">
            {category.items.map((item, index) => {
              const isOpen = openItems[category.id] === index
              return (
                <div key={index}>
                  <button
                    onClick={() => toggle(category.id, index)}
                    className="w-full flex items-center justify-between px-5 py-4 text-left text-text-primary hover:bg-bg-secondary transition-colors"
                    aria-expanded={isOpen}
                  >
                    <span className="text-[14px] sm:text-[15px] font-medium pr-4">
                      {item.question}
                    </span>
                    <ChevronIcon open={isOpen} />
                  </button>
                  {isOpen && (
                    <div className="px-5 pb-4 text-[14px] text-text-secondary leading-relaxed">
                      {item.answer}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}
