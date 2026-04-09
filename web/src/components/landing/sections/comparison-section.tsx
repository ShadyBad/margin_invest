const ROWS = [
  { label: "Scoring", us: "Sector-neutral percentiles", screeners: "Absolute filters", blackbox: "Opaque composite" },
  { label: "Transparency", us: "Every formula documented", screeners: "Filter-based", blackbox: "Hidden methodology" },
  { label: "Filters", us: "6 forensic (Beneish, Altman)", screeners: "Price/volume only", blackbox: "None" },
  { label: "Auditability", us: "Spreadsheet-verifiable", screeners: "Limited", blackbox: "None" },
  { label: "Bias", us: "Deterministic, zero discretion", screeners: "User-configured", blackbox: "Analyst opinions" },
]

export function ComparisonSection() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-[28px] md:text-[36px] font-bold text-text-primary tracking-tight text-center mb-12">
          How We Compare
        </h2>

        <div className="terminal-card overflow-x-auto">
          <table className="w-full text-left min-w-[600px]">
            <caption className="sr-only">
              Comparison of Margin Invest vs Finviz / Screener.co vs Zacks / Morningstar
            </caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-6 py-3 text-xs uppercase tracking-wider text-text-tertiary font-medium w-1/6" />
                <th scope="col" className="px-6 py-3 text-xs uppercase tracking-wider text-accent font-semibold w-[28%] bg-bg-secondary/50 border-t-2 border-accent">
                  Margin Invest
                </th>
                <th scope="col" className="px-6 py-3 text-xs uppercase tracking-wider text-text-tertiary font-medium w-[28%]">
                  Finviz / Screener.co
                </th>
                <th scope="col" className="px-6 py-3 text-xs uppercase tracking-wider text-text-tertiary font-medium w-[28%]">
                  Zacks / Morningstar
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.label} className="border-b border-border-subtle last:border-b-0">
                  <th scope="row" className="px-6 py-4 text-sm font-medium text-text-primary">
                    {row.label}
                  </th>
                  <td className="px-6 py-4 text-sm text-text-primary bg-bg-secondary/30">{row.us}</td>
                  <td className="px-6 py-4 text-sm text-text-tertiary">{row.screeners}</td>
                  <td className="px-6 py-4 text-sm text-text-tertiary">{row.blackbox}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
