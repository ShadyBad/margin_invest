"use client"

import { useState, useEffect } from "react"

const subjectOptions = [
  "General",
  "API Integration",
  "Security Report",
  "Business Inquiry",
  "Other",
]

export function ContactForm() {
  const [submitted, setSubmitted] = useState(false)
  const [subjectOpen, setSubjectOpen] = useState(false)
  const [selectedSubject, setSelectedSubject] = useState("")

  useEffect(() => {
    if (!subjectOpen) return
    const handler = () => setSubjectOpen(false)
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [subjectOpen])

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    const email = "support@margin-invest.com"
    const subject = data.get("subject") as string
    const body = `Name: ${data.get("name")}\n\n${data.get("message")}`
    window.location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated text-center">
        <p className="text-[15px] font-semibold text-text-primary mb-2">Message prepared</p>
        <p className="text-[13px] text-text-tertiary">
          Your email client should have opened with the message. If it didn&apos;t, email us
          directly at{" "}
          <a
            href="mailto:support@margin-invest.com"
            className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
          >
            support@margin-invest.com
          </a>
          .
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="contact-name" className="block text-[13px] font-medium text-text-primary mb-1">
          Name
        </label>
        <input
          id="contact-name"
          name="name"
          type="text"
          required
          className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
          placeholder="Your name"
        />
      </div>

      <div>
        <label htmlFor="contact-email" className="block text-[13px] font-medium text-text-primary mb-1">
          Email
        </label>
        <input
          id="contact-email"
          name="email"
          type="email"
          required
          className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label htmlFor="contact-subject" className="block text-[13px] font-medium text-text-primary mb-1">
          Subject
        </label>
        <input type="hidden" name="subject" value={selectedSubject} required />
        <div className="relative" onClick={(e) => e.stopPropagation()}>
          <button
            type="button"
            onClick={() => setSubjectOpen(!subjectOpen)}
            className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-left flex items-center justify-between transition-colors focus:outline-none focus:border-accent"
            style={{ color: selectedSubject ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)' }}
          >
            <span>{selectedSubject || 'Select a topic...'}</span>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
              style={{ transform: subjectOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 200ms' }}>
              <path d="M2 4l4 4 4-4" />
            </svg>
          </button>
          {subjectOpen && (
            <div className="absolute z-50 w-full mt-1 rounded-lg overflow-hidden"
              style={{
                background: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border-primary)',
                boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
              }}>
              {subjectOptions.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => { setSelectedSubject(opt); setSubjectOpen(false) }}
                  className="w-full px-3 py-2.5 text-left text-[14px] transition-colors"
                  style={{
                    color: selectedSubject === opt
                      ? 'var(--color-accent)'
                      : 'var(--color-text-primary)',
                    background: selectedSubject === opt
                      ? 'var(--color-accent-subtle)'
                      : 'transparent',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-bg-subtle)')}
                  onMouseLeave={e => (e.currentTarget.style.background = selectedSubject === opt ? 'var(--color-accent-subtle)' : 'transparent')}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div>
        <label htmlFor="contact-message" className="block text-[13px] font-medium text-text-primary mb-1">
          Message
        </label>
        <textarea
          id="contact-message"
          name="message"
          required
          rows={5}
          className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors resize-y"
          placeholder="How can we help?"
        />
      </div>

      <button
        type="submit"
        className="px-6 py-2.5 bg-accent hover:bg-accent-hover text-bg-primary text-[14px] font-medium rounded-lg transition-colors"
      >
        Send message
      </button>
    </form>
  )
}
