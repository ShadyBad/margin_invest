import type { ContactCard } from "./support-data"

export function ContactSection({ cards }: { cards: ContactCard[] }) {
  return (
    <section>
      <h2 className="heading-3 text-text-primary mb-2">Still need help?</h2>
      <p className="text-[14px] text-text-secondary mb-6">
        If you couldn&apos;t find what you were looking for, reach out directly.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {cards.map((card) => (
          <div
            key={card.email}
            className="p-5 border border-border-primary rounded-lg bg-bg-elevated"
          >
            <h3 className="text-[15px] font-semibold text-text-primary mb-1">{card.title}</h3>
            <p className="text-[13px] text-text-tertiary mb-3">{card.description}</p>
            <a
              href={`mailto:${card.email}`}
              className="text-[13px] text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
            >
              {card.email}
            </a>
          </div>
        ))}
      </div>
      <p className="text-[13px] text-text-tertiary">
        Check our{" "}
        <a
          href="https://status.margin-invest.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
        >
          system status
        </a>{" "}
        page for real-time platform availability.
      </p>
    </section>
  )
}
