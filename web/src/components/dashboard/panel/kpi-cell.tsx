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
      <span className="text-xs font-sans uppercase tracking-[0.05em] text-text-tertiary">
        {label}
      </span>
      <span className={`text-[20px] font-mono leading-tight ${color ?? "text-text-primary"}`} data-testid={testId}>
        {value}
      </span>
      {context && (
        <span className="text-xs text-accent">{context}</span>
      )}
      {unavailableReason && value === "\u2014" && (
        <span className="text-xs text-zinc-500 mt-0.5">{unavailableReason}</span>
      )}
    </div>
  )
}
