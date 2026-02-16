"use client"

import { useState } from "react"
import { getInitials, getAvatarColor } from "@/lib/avatar"

const SIZES = { sm: 24, md: 32, lg: 48 } as const
type AvatarSize = keyof typeof SIZES

interface AvatarProps {
  name: string
  avatarUrl?: string | null
  oauthAvatarUrl?: string | null
  size: AvatarSize
  className?: string
}

function InitialsAvatar({
  name,
  size,
  className,
}: {
  name: string
  size: number
  className?: string
}) {
  const initials = getInitials(name)
  const color = getAvatarColor(name)
  const fontSize = Math.round(size * 0.4)

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={`rounded-full flex-shrink-0 ${className ?? ""}`}
    >
      <circle cx={size / 2} cy={size / 2} r={size / 2} fill={color} />
      <text
        x="50%"
        y="50%"
        dy=".1em"
        textAnchor="middle"
        dominantBaseline="central"
        fill="white"
        fontSize={fontSize}
        fontWeight="600"
        fontFamily="system-ui, sans-serif"
      >
        {initials}
      </text>
    </svg>
  )
}

export function Avatar({ name, avatarUrl, oauthAvatarUrl, size, className }: AvatarProps) {
  const px = SIZES[size]
  const [failedUrls, setFailedUrls] = useState<Set<string>>(new Set())

  const urls = [avatarUrl, oauthAvatarUrl].filter(
    (u): u is string => !!u && !failedUrls.has(u),
  )
  const activeUrl = urls[0]

  if (!activeUrl) {
    return <InitialsAvatar name={name} size={px} className={className} />
  }

  return (
    <img
      src={activeUrl}
      alt={`${name}'s avatar`}
      width={px}
      height={px}
      className={`rounded-full object-cover flex-shrink-0 ${className ?? ""}`}
      onError={() => setFailedUrls((prev) => new Set(prev).add(activeUrl))}
    />
  )
}
