interface DiagramNodeLabelProps {
  label: string
  active: boolean
}

export function DiagramNodeLabel({ label, active }: DiagramNodeLabelProps) {
  return (
    <span
      className={`text-[14px] font-medium tracking-[0.2px] ${
        active ? "text-accent" : "text-text-secondary"
      }`}
    >
      {label}
    </span>
  )
}
