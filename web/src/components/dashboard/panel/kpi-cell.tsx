interface KpiCellProps {
  label: string
  value: string
  context?: string
  testId?: string
  color?: string
  unavailableReason?: string
}

export function KpiCell({ label, value, context, testId, color, unavailableReason }: KpiCellProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-sans uppercase tracking-[0.05em] text-[#5C5955]">
        {label}
      </span>
      <span className={`text-[20px] font-mono leading-tight ${color ?? "text-[#E8E6E3]"}`} data-testid={testId}>
        {value}
      </span>
      {context && (
        <span className="text-[11px] text-[#1A7A5A]">{context}</span>
      )}
      {unavailableReason && value === "\u2014" && (
        <span className="text-[10px] text-zinc-500 mt-0.5">{unavailableReason}</span>
      )}
    </div>
  )
}
