import { type ElementType, type HTMLAttributes, type ReactNode } from "react"

interface GlassSurfaceProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode
  elevated?: boolean
  as?: ElementType
}

export function GlassSurface({
  children,
  elevated = false,
  as: Component = "div",
  className = "",
  ...props
}: GlassSurfaceProps) {
  const baseClass = elevated ? "glass-elevated" : "glass"
  return (
    <Component className={`${baseClass} ${className}`.trim()} {...props}>
      {children}
    </Component>
  )
}
