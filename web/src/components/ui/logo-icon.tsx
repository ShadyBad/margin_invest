/**
 * LogoIcon — The Margin Invest brand mark (funnel with 3 narrowing lines).
 *
 * Shared across: landing navbar, app shell top bar, sidebar.
 * Uses currentColor so it inherits from parent text color.
 */

interface LogoIconProps {
  size?: number
  className?: string
}

export function LogoIcon({ size = 24, className }: LogoIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      stroke="currentColor"
      aria-hidden="true"
      className={className}
    >
      {/* Top line (widest) */}
      <line x1="2" y1="4" x2="18" y2="4" />
      {/* Middle line (medium) */}
      <line x1="5" y1="10" x2="15" y2="10" />
      {/* Bottom line (narrowest) */}
      <line x1="8" y1="16" x2="12" y2="16" />
    </svg>
  )
}
