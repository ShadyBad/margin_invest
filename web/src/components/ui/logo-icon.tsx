/**
 * LogoIcon — The Margin Invest brand mark (polyline chart "M").
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
      <polyline points="2,16 6,6 10,12 14,4 18,16" />
    </svg>
  )
}
