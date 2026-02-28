"use client"

import { useState } from "react"

const subjectOptions = [
  "General",
  "API Integration",
  "Security Report",
  "Business Inquiry",
  "Other",
]

export function ContactForm() {
  const [submitted, setSubmitted] = useState(false)

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
        <select
          id="contact-subject"
          name="subject"
          required
          className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-text-primary focus:outline-none focus:border-accent transition-colors"
        >
          <option value="">Select a topic...</option>
          {subjectOptions.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
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
