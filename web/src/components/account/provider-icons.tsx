"use client"

import { useState } from "react"

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
  apple: "Apple",
  amazon: "Amazon",
  facebook: "Facebook",
}

type ProviderState = "connected" | "available" | "coming_soon"

interface ProviderConfig {
  id: string
  label: string
  state: ProviderState
  icon: React.ReactNode
}

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}

function AppleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.32 2.32-2.11 4.45-3.74 4.25z" />
    </svg>
  )
}

function AmazonIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M13.96 14.37c-1.8 1.33-4.41 2.04-6.66 2.04-3.15 0-5.99-1.17-8.14-3.11-.17-.15-.02-.36.18-.24 2.32 1.35 5.18 2.16 8.13 2.16 1.99 0 4.19-.41 6.2-1.27.3-.13.56.2.29.42z" />
      <path d="M14.68 13.53c-.23-.29-1.5-.14-2.07-.07-.17.02-.2-.13-.04-.24 1.01-.71 2.68-.51 2.87-.27.19.24-.05 1.92-.99 2.73-.15.12-.29.06-.22-.1.22-.54.7-1.76.45-2.05z" />
      <path d="M12.66 9.18V8.5c0-.1.08-.17.17-.17h3.02c.1 0 .17.07.17.17v.58c0 .1-.08.22-.22.41l-1.57 2.24c.58-.01 1.2.07 1.73.37.12.07.15.17.16.26v.73c0 .1-.11.22-.22.16-.93-.49-2.16-.54-3.19.01-.1.06-.22-.06-.22-.16v-.7c0-.11 0-.29.11-.45l1.82-2.61h-1.58c-.1 0-.17-.07-.17-.17z" />
    </svg>
  )
}

function FacebookIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  )
}

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  google: <GoogleIcon />,
  github: <GitHubIcon />,
  apple: <AppleIcon />,
  amazon: <AmazonIcon />,
  facebook: <FacebookIcon />,
}

const AVAILABLE_PROVIDERS = ["google", "github"]
const COMING_SOON_PROVIDERS = ["apple", "amazon", "facebook"]

interface ProviderIconsProps {
  linkedProviders: string[]
  onConnect?: (provider: string) => void
  onDisconnect?: (provider: string) => void
  connecting?: string | null
}

export function ProviderIcons({
  linkedProviders,
  onConnect,
  onDisconnect,
  connecting = null,
}: ProviderIconsProps) {
  function getState(providerId: string): ProviderState {
    if (COMING_SOON_PROVIDERS.includes(providerId)) return "coming_soon"
    if (linkedProviders.includes(providerId)) return "connected"
    return "available"
  }

  const providers: ProviderConfig[] = [
    ...AVAILABLE_PROVIDERS,
    ...COMING_SOON_PROVIDERS,
  ].map((id) => ({
    id,
    label: PROVIDER_LABELS[id] || id,
    state: getState(id),
    icon: PROVIDER_ICONS[id],
  }))

  return (
    <div>
      <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wide mb-3">
        Authentication Methods
      </h3>
      <div className="flex flex-wrap gap-4">
        {providers.map((provider) => (
          <ProviderIcon
            key={provider.id}
            provider={provider}
            onConnect={onConnect}
            onDisconnect={onDisconnect}
            connecting={connecting === provider.id}
          />
        ))}
      </div>
    </div>
  )
}

function ProviderIcon({
  provider,
  onConnect,
  onDisconnect,
  connecting,
}: {
  provider: ProviderConfig
  onConnect?: (provider: string) => void
  onDisconnect?: (provider: string) => void
  connecting: boolean
}) {
  const { id, label, state, icon } = provider

  const stateLabel =
    state === "connected"
      ? "Connected"
      : state === "available"
        ? "Not connected"
        : "Coming soon"

  const ariaLabel = `${label} \u2014 ${stateLabel}`

  const borderClass =
    state === "connected"
      ? "border-solid border-emerald-500/40"
      : state === "available"
        ? "border-dashed border-border-primary"
        : "border-solid border-border-primary"

  const opacityClass = state === "coming_soon" ? "opacity-40" : ""

  return (
    <div
      className={`flex flex-col items-center gap-1.5 ${opacityClass}`}
      aria-label={ariaLabel}
      aria-disabled={state === "coming_soon" ? "true" : undefined}
    >
      <div
        className={`flex items-center justify-center w-12 h-12 rounded-xl border ${borderClass} bg-bg-primary text-text-primary`}
      >
        {icon}
      </div>
      <span className="text-xs text-text-secondary">{label}</span>
      {state === "connected" && (
        <>
          <span className="text-xs text-emerald-400">Connected</span>
          {onDisconnect && (
            <button
              onClick={() => onDisconnect(id)}
              className="text-xs text-text-secondary hover:text-red-400 transition-colors"
              aria-label={`Disconnect ${label} account`}
            >
              Disconnect
            </button>
          )}
        </>
      )}
      {state === "available" && (
        <>
          <span className="text-xs text-text-secondary">Not connected</span>
          {onConnect && (
            <button
              onClick={() => onConnect(id)}
              disabled={connecting}
              className="text-xs text-accent hover:text-accent-hover transition-colors disabled:opacity-50"
              aria-label={`Connect ${label} account`}
            >
              {connecting ? "Connecting..." : "Connect"}
            </button>
          )}
        </>
      )}
      {state === "coming_soon" && (
        <span className="text-xs text-text-secondary">Coming soon</span>
      )}
    </div>
  )
}
