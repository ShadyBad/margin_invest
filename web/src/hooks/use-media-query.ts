"use client"

import { useCallback, useSyncExternalStore } from "react"

/**
 * SSR-safe media query hook using useSyncExternalStore.
 * Returns `false` on the server, then matches the query on the client.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      if (typeof window === "undefined") return () => {}
      const mql = window.matchMedia(query)
      mql.addEventListener("change", onStoreChange)
      return () => mql.removeEventListener("change", onStoreChange)
    },
    [query]
  )

  const getSnapshot = useCallback(() => {
    if (typeof window === "undefined") return false
    return window.matchMedia(query).matches
  }, [query])

  const getServerSnapshot = useCallback(() => false, [])

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}

/**
 * Convenience: returns `true` when viewport is <= 768px.
 */
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 768px)")
}
