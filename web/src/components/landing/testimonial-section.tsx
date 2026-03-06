"use client"

const TESTIMONIALS = [
  {
    quote: "Margin Invest cuts through the noise. Instead of chasing headlines, I can see exactly which companies actually pass the filters. It's the first tool I've used that feels built for serious decision-making.",
    name: "Daniel K.",
    role: "Beta Tester",
  },
  {
    quote: "The scoring system is what sold me. I can instantly understand why a company ranks where it does. It's like having an institutional research workflow condensed into one dashboard.",
    name: "Sarah L.",
    role: "Beta Tester",
  },
  {
    quote: "What I appreciate most is the discipline it enforces. Margin Invest removes the emotional side of investing and forces me to focus on companies that truly meet the criteria.",
    name: "Michael R.",
    role: "Beta Tester",
  },
  {
    quote: "I've tried dozens of stock research tools. Margin Invest is the only one that actually helps me narrow thousands of companies down to the few that matter.",
    name: "Jason M.",
    role: "Beta Tester",
  },
  {
    quote: "The transparency is refreshing. Every score, every filter, every decision has an explanation behind it. It makes the entire process feel rigorous and trustworthy.",
    name: "Emily T.",
    role: "Beta Tester",
  },
]

function getInitials(name: string): string {
  const parts = name.replace(".", "").trim().split(/\s+/)
  return parts.map((p) => p[0]).join("").toUpperCase()
}

function TestimonialCard({ testimonial }: { testimonial: typeof TESTIMONIALS[number] }) {
  return (
    <div
      className="flex-shrink-0 flex flex-col"
      style={{
        width: '320px',
        marginRight: '16px',
        background: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: '12px',
        padding: '24px',
      }}
    >
      <div style={{ fontFamily: 'var(--font-display)', fontSize: '48px', lineHeight: 1, color: 'rgba(26,122,90,0.25)', display: 'block', marginBottom: '8px' }}>
        &ldquo;
      </div>
      <p className="text-sm leading-relaxed text-text-secondary italic flex-1">
        {testimonial.quote}
      </p>
      <div className="mt-4 pt-4 border-t border-border-subtle flex items-center gap-3">
        <div
          className="flex items-center justify-center rounded-full font-mono text-[11px] font-bold"
          style={{
            width: '32px',
            height: '32px',
            background: 'rgba(26,122,90,0.15)',
            color: 'var(--color-accent)',
          }}
        >
          {getInitials(testimonial.name)}
        </div>
        <div>
          <div className="text-sm font-medium text-text-primary">{testimonial.name}</div>
          <div className="text-xs text-text-tertiary font-mono">{testimonial.role}</div>
        </div>
      </div>
    </div>
  )
}

export function TestimonialSection() {
  return (
    <section className="py-16 px-6">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-text-tertiary text-center mb-8">
        Early Access &middot; What beta testers are saying
      </p>

      {/* Mobile: stacked list */}
      <div className="flex flex-col gap-4 md:hidden">
        {TESTIMONIALS.map((t) => (
          <div key={t.name} className="w-full" style={{ marginRight: 0 }}>
            <TestimonialCard testimonial={t} />
          </div>
        ))}
      </div>

      {/* Desktop: marquee */}
      <div
        className="hidden md:block relative"
        style={{ overflow: 'hidden', width: '100%' }}
      >
        {/* Left fade mask */}
        <div
          className="absolute left-0 top-0 bottom-0 z-10 pointer-events-none"
          style={{
            width: '120px',
            background: 'linear-gradient(to right, #0A0F0D, transparent)',
          }}
        />
        {/* Right fade mask */}
        <div
          className="absolute right-0 top-0 bottom-0 z-10 pointer-events-none"
          style={{
            width: '120px',
            background: 'linear-gradient(to left, #0A0F0D, transparent)',
          }}
        />

        <div
          style={{
            display: 'flex',
            width: 'fit-content',
            animation: 'marquee 50s linear infinite',
            willChange: 'transform',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.animationPlayState = 'paused' }}
          onMouseLeave={(e) => { e.currentTarget.style.animationPlayState = 'running' }}
        >
          {[...TESTIMONIALS, ...TESTIMONIALS].map((t, i) => (
            <TestimonialCard key={`${t.name}-${i}`} testimonial={t} />
          ))}
        </div>
      </div>

      <style jsx>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </section>
  )
}
