interface KpiCellProps {
  label: string
  value: string
  context?: string
  testId?: string
}

export function KpiCell({ label, value, context, testId }: KpiCellProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-sans uppercase tracking-[0.05em] text-[#5C5955]">
        {label}
      </span>
      <span className="text-[20px] font-mono text-[#E8E6E3] leading-tight" data-testid={testId}>
        {value}
      </span>
      {context && (
        <span className="text-[11px] text-[#1A7A5A]">{context}</span>
      )}
    </div>
  )
}
