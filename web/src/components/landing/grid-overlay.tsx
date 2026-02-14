interface GridOverlayProps {
  opacity?: number
}

export function GridOverlay({ opacity = 0.03 }: GridOverlayProps) {
  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity }}
      aria-hidden="true"
    >
      <defs>
        <pattern id="grid" width="64" height="64" patternUnits="userSpaceOnUse">
          <path
            d="M 64 0 L 0 0 0 64"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
    </svg>
  )
}
