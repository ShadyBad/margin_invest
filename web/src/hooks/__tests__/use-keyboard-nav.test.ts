import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { useKeyboardNav } from "../use-keyboard-nav"

describe("useKeyboardNav", () => {
  it("Cmd+K focuses search input ref", () => {
    const searchInput = document.createElement("input")
    document.body.appendChild(searchInput)
    const ref = { current: searchInput }

    renderHook(() => useKeyboardNav({ searchInputRef: ref }))

    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", metaKey: true })
    )
    expect(document.activeElement).toBe(searchInput)

    document.body.removeChild(searchInput)
  })

  it("Ctrl+K focuses search input ref (Windows)", () => {
    const searchInput = document.createElement("input")
    document.body.appendChild(searchInput)
    const ref = { current: searchInput }

    renderHook(() => useKeyboardNav({ searchInputRef: ref }))

    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", ctrlKey: true })
    )
    expect(document.activeElement).toBe(searchInput)

    document.body.removeChild(searchInput)
  })

  it("calls onCmdK when Cmd+K is pressed", () => {
    const onCmdK = vi.fn()
    renderHook(() => useKeyboardNav({ onCmdK }))
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", metaKey: true })
    )
    expect(onCmdK).toHaveBeenCalledOnce()
  })

  it("calls onCmdK when Ctrl+K is pressed", () => {
    const onCmdK = vi.fn()
    renderHook(() => useKeyboardNav({ onCmdK }))
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", ctrlKey: true })
    )
    expect(onCmdK).toHaveBeenCalledOnce()
  })

  it("Escape calls onEscape callback", () => {
    const onEscape = vi.fn()
    renderHook(() => useKeyboardNav({ onEscape }))
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }))
    expect(onEscape).toHaveBeenCalledOnce()
  })

  it("Escape blurs the active element", () => {
    const input = document.createElement("input")
    document.body.appendChild(input)
    input.focus()
    expect(document.activeElement).toBe(input)

    renderHook(() => useKeyboardNav({}))
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }))
    expect(document.activeElement).not.toBe(input)

    document.body.removeChild(input)
  })

  it("does not call handlers for unrelated keys", () => {
    const onCmdK = vi.fn()
    const onEscape = vi.fn()
    renderHook(() => useKeyboardNav({ onCmdK, onEscape }))
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }))
    expect(onCmdK).not.toHaveBeenCalled()
    expect(onEscape).not.toHaveBeenCalled()
  })

  it("cleans up event listeners on unmount", () => {
    const spy = vi.spyOn(document, "removeEventListener")
    const { unmount } = renderHook(() => useKeyboardNav({}))
    unmount()
    expect(spy).toHaveBeenCalledWith("keydown", expect.any(Function))
    spy.mockRestore()
  })

  it("does not fire after unmount", () => {
    const onCmdK = vi.fn()
    const { unmount } = renderHook(() => useKeyboardNav({ onCmdK }))
    unmount()
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", metaKey: true })
    )
    expect(onCmdK).not.toHaveBeenCalled()
  })
})
