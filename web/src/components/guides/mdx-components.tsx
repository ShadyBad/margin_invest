import type { ReactNode } from "react"
import { KnownLimitations } from "./known-limitations"
import { TechnicalDetail } from "./technical-detail"
import { VerifyItYourself } from "./verify-it-yourself"

// ---------------------------------------------------------------------------
// Slugify helper (mirrors lib/guides.ts slugify for heading ID consistency)
// ---------------------------------------------------------------------------

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^\w-]/g, "")
}

// ---------------------------------------------------------------------------
// Custom components
// ---------------------------------------------------------------------------

const calloutConfig = {
  info: {
    label: "Note",
    border: "border-l-accent",
    bg: "bg-accent-subtle",
  },
  warning: {
    label: "Warning",
    border: "border-l-warning",
    bg: "bg-[rgba(184,134,11,0.08)]",
  },
  tip: {
    label: "Tip",
    border: "border-l-bullish",
    bg: "bg-[rgba(16,185,129,0.08)]",
  },
} as const

interface CalloutProps {
  type?: "info" | "warning" | "tip"
  children: ReactNode
}

export function Callout({ type = "info", children }: CalloutProps) {
  const config = calloutConfig[type]

  return (
    <div
      className={`border-l-4 ${config.border} ${config.bg} rounded-r-lg px-5 py-4 my-6`}
    >
      <div className="text-[13px] uppercase tracking-wider font-semibold text-text-secondary mb-2">
        {config.label}
      </div>
      <div className="body-text text-text-secondary">{children}</div>
    </div>
  )
}

interface FormulaProps {
  children: ReactNode
}

export function Formula({ children }: FormulaProps) {
  return (
    <div className="bg-bg-subtle rounded-lg px-4 py-3 my-6 font-mono text-[14px] text-text-primary overflow-x-auto">
      {children}
    </div>
  )
}

interface ExampleProps {
  title?: string
  children: ReactNode
}

export function Example({ title, children }: ExampleProps) {
  return (
    <div className="bg-bg-elevated border border-border-subtle rounded-lg px-5 py-4 my-6">
      {title && (
        <div className="text-[13px] uppercase tracking-wider font-semibold text-text-secondary mb-2">
          {title}
        </div>
      )}
      <div className="body-text text-text-secondary">{children}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Heading components with auto-generated IDs for TOC scroll-spy
// ---------------------------------------------------------------------------

function H2({ children }: { children?: ReactNode }) {
  const text = typeof children === "string" ? children : String(children ?? "")
  const id = slugify(text)

  return (
    <h2
      id={id}
      className="heading-3 text-text-primary mt-12 mb-4 scroll-mt-24"
    >
      {children}
    </h2>
  )
}

function H3({ children }: { children?: ReactNode }) {
  const text = typeof children === "string" ? children : String(children ?? "")
  const id = slugify(text)

  return (
    <h3
      id={id}
      className="text-[18px] md:text-[20px] font-semibold text-text-primary mt-8 mb-3 scroll-mt-24"
    >
      {children}
    </h3>
  )
}

// ---------------------------------------------------------------------------
// mdxComponents map — passed to compileMDX from next-mdx-remote
// ---------------------------------------------------------------------------

export const mdxComponents = {
  // Headings
  h2: H2,
  h3: H3,

  // Block elements
  p: ({ children }: { children?: ReactNode }) => (
    <p className="body-text text-text-secondary mb-4 leading-relaxed">
      {children}
    </p>
  ),
  ul: ({ children }: { children?: ReactNode }) => (
    <ul className="list-disc list-outside ml-5 mb-4 space-y-1 text-text-secondary body-text">
      {children}
    </ul>
  ),
  ol: ({ children }: { children?: ReactNode }) => (
    <ol className="list-decimal list-outside ml-5 mb-4 space-y-1 text-text-secondary body-text">
      {children}
    </ol>
  ),
  li: ({ children }: { children?: ReactNode }) => (
    <li className="text-text-secondary">{children}</li>
  ),

  // Inline elements
  strong: ({ children }: { children?: ReactNode }) => (
    <strong className="font-semibold text-text-primary">{children}</strong>
  ),
  a: ({ href, children }: { href?: string; children?: ReactNode }) => (
    <a
      href={href}
      className="text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
    >
      {children}
    </a>
  ),
  code: ({ children }: { children?: ReactNode }) => (
    <code className="bg-bg-subtle rounded px-1.5 py-0.5 text-[14px] font-mono text-text-primary">
      {children}
    </code>
  ),

  // Table elements
  table: ({ children }: { children?: ReactNode }) => (
    <div className="overflow-x-auto my-6">
      <table className="w-full text-[14px] text-text-secondary">
        {children}
      </table>
    </div>
  ),
  th: ({ children }: { children?: ReactNode }) => (
    <th className="text-left text-text-primary font-semibold pb-2 pr-4 border-b border-border-primary">
      {children}
    </th>
  ),
  td: ({ children }: { children?: ReactNode }) => (
    <td className="py-2 pr-4 border-b border-border-subtle">{children}</td>
  ),

  // Thematic break
  hr: () => <hr className="border-border-subtle my-8" />,

  // Custom components (available in MDX content)
  Callout,
  Example,
  Formula,
  KnownLimitations,
  TechnicalDetail,
  VerifyItYourself,
}
