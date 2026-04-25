interface SeverityPillProps {
  severity: number
}

function getSeverityColor(severity: number): string {
  if (severity >= 9) return "var(--color-bearish)"
  if (severity >= 7) return "#f97316"
  if (severity >= 4) return "var(--color-warning)"
  return "var(--color-bullish)"
}

export function SeverityPill({ severity }: SeverityPillProps) {
  const color = getSeverityColor(severity)

  return (
    <span
      data-testid="severity_pill"
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: "1.5rem",
        height: "1.5rem",
        borderRadius: "9999px",
        fontSize: "0.75rem",
        fontWeight: 600,
        fontFamily: "var(--font-data)",
        color: "#fff",
        backgroundColor: color,
        flexShrink: 0,
      }}
    >
      {severity}
    </span>
  )
}
