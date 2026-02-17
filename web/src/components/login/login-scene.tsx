"use client"

import dynamic from "next/dynamic"

const LoginCanvas = dynamic(() => import("./login-canvas").then((mod) => ({ default: mod.LoginCanvas })), {
  ssr: false,
})

export function LoginScene() {
  return <LoginCanvas />
}
