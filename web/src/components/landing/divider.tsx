interface DividerProps {
  opacity?: number
}

export function Divider({ opacity }: DividerProps) {
  return (
    <hr
      role="separator"
      className="border-0 h-px bg-divider"
      style={opacity !== undefined ? { opacity } : undefined}
    />
  )
}
