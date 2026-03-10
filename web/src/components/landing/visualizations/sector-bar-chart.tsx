/**
 * SectorBarChart — Horizontal bar chart of sector distribution.
 *
 * Groups candidates by sector, renders sorted horizontal CSS bars
 * with sector colors from the design system (--color-sector-*).
 */

import type { CandidateCard } from "../shared/types"

interface SectorBarChartProps {
  candidates: CandidateCard[]
}

/** Map sector names to CSS custom property names */
const SECTOR_COLOR_MAP: Record<string, string> = {
  TECHNOLOGY: "var(--color-sector-tech)",
  "HEALTH CARE": "var(--color-sector-healthcare)",
  HEALTHCARE: "var(--color-sector-healthcare)",
  FINANCIALS: "var(--color-sector-financials)",
  "CONSUMER DISCRETIONARY": "var(--color-sector-consumer-disc)",
  "CONSUMER STAPLES": "var(--color-sector-consumer-staples)",
  ENERGY: "var(--color-sector-energy)",
  INDUSTRIALS: "var(--color-sector-industrials)",
  MATERIALS: "var(--color-sector-materials)",
  "REAL ESTATE": "var(--color-sector-real-estate)",
  UTILITIES: "var(--color-sector-utilities)",
  "COMMUNICATION SERVICES": "var(--color-sector-comms)",
}

const DEFAULT_COLOR = "var(--color-accent)"

function getSectorColor(sector: string): string {
  return SECTOR_COLOR_MAP[sector.toUpperCase()] ?? DEFAULT_COLOR
}

interface SectorGroup {
  sector: string
  count: number
}

export function groupBySector(candidates: CandidateCard[]): SectorGroup[] {
  const map = new Map<string, number>()
  for (const c of candidates) {
    const s = c.sector || "Unknown"
    map.set(s, (map.get(s) ?? 0) + 1)
  }
  return Array.from(map.entries())
    .map(([sector, count]) => ({ sector, count }))
    .sort((a, b) => b.count - a.count)
}

export function SectorBarChart({ candidates }: SectorBarChartProps) {
  if (candidates.length === 0) {
    return (
      <div className="flex items-center justify-center h-full min-h-[120px]">
        <p className="text-xs text-text-tertiary font-mono">
          Sector data available after scoring cycle
        </p>
      </div>
    )
  }

  const groups = groupBySector(candidates)
  const maxCount = groups[0]?.count ?? 1

  return (
    <div
      className="flex flex-col gap-1.5"
      aria-label="Sector distribution of surviving candidates"
    >
      {groups.map((g) => {
        const widthPct = Math.max(8, (g.count / maxCount) * 100)
        return (
          <div key={g.sector} data-testid={`sector-row-${g.sector}`} className="group/sector flex items-center gap-2 cursor-default">
            <span className="text-mono-label text-text-tertiary w-[100px] shrink-0 truncate transition-colors duration-200 group-hover/sector:text-text-secondary" title={g.sector}>
              {g.sector}
            </span>
            <div className="flex-1 flex items-center gap-2">
              <div
                className="h-4 rounded-sm transition-all duration-200 group-hover/sector:brightness-125 group-hover/sector:shadow-[0_0_8px_rgba(26,122,90,0.15)]"
                data-testid={`sector-bar-${g.sector}`}
                style={{
                  width: `${widthPct}%`,
                  backgroundColor: getSectorColor(g.sector),
                  opacity: 0.8,
                }}
              />
              <span className="font-mono text-xs text-text-secondary tabular-nums shrink-0 transition-colors duration-200 group-hover/sector:text-text-primary">
                {g.count}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
