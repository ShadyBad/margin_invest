import Link from "next/link"
import type { HomepageData } from "../shared/types"

interface SocialProofSectionProps {
  data: HomepageData | null
}

export function SocialProofSection({ data }: SocialProofSectionProps) {
  if (!data) return null

  const failRate =
    data.total_universe > 0
      ? Math.round(((data.total_universe - data.surviving_count) / data.total_universe) * 100)
      : 0

  const stats = [
    {
      value: data.total_scored.toLocaleString("en-US"),
      label: "positions scored this cycle",
      detail: "Five-factor analysis across quality, value, momentum, sentiment, and growth.",
    },
    {
      value: `${failRate}%`,
      label: "fail at least one forensic filter",
      detail: "Beneish M-Score, Altman Z-Score, and four other fraud and distress screens.",
    },
    {
      value: "100%",
      label: "every score links to its formula",
      detail: "No black boxes. Verify any score with a spreadsheet.",
      link: { href: "/methodology", text: "See methodology →" },
    },
    {
      value: "Daily",
      label: "updates, every market day",
      detail: "Automated pipeline. No human overrides. Same inputs always produce same outputs.",
    },
  ]

  return (
    <section className="py-16 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="terminal-card p-5 space-y-2">
              <p className="text-2xl font-mono font-semibold text-accent">{stat.value}</p>
              <p className="text-sm font-medium text-text-primary">{stat.label}</p>
              <p className="text-xs text-text-tertiary leading-relaxed">{stat.detail}</p>
              {stat.link && (
                <Link
                  href={stat.link.href}
                  className="inline-block text-xs text-accent hover:underline underline-offset-2 mt-1"
                >
                  {stat.link.text}
                </Link>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
