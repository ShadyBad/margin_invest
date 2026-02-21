import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode
    href: string
    [key: string]: unknown
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

import { MfaRequiredModal } from "../mfa-required-modal"

describe("MfaRequiredModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Clean up any event listeners
  })

  it("is not visible initially", () => {
    render(<MfaRequiredModal />)
    expect(screen.queryByTestId("mfa-required-modal")).not.toBeInTheDocument()
  })

  it("appears when mfa-required event is dispatched", () => {
    render(<MfaRequiredModal />)

    act(() => {
      window.dispatchEvent(
        new CustomEvent("mfa-required", {
          detail: { error: "mfa_required", message: "MFA required" },
        }),
      )
    })

    expect(screen.getByTestId("mfa-required-modal")).toBeInTheDocument()
  })

  it("displays correct title", () => {
    render(<MfaRequiredModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })

    expect(
      screen.getByRole("heading", { name: "MFA Required" }),
    ).toBeInTheDocument()
  })

  it("displays MFA required message", () => {
    render(<MfaRequiredModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })

    expect(
      screen.getByText(
        /Multi-factor authentication is required to perform this action/,
      ),
    ).toBeInTheDocument()
  })

  it("has Set Up MFA link pointing to /mfa/setup", () => {
    render(<MfaRequiredModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })

    const link = screen.getByText("Set Up MFA")
    expect(link.closest("a")).toHaveAttribute("href", "/mfa/setup")
  })

  it("has Go back button that dismisses the modal", () => {
    render(<MfaRequiredModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })

    expect(screen.getByTestId("mfa-required-modal")).toBeInTheDocument()

    fireEvent.click(screen.getByText("Go back"))

    expect(screen.queryByTestId("mfa-required-modal")).not.toBeInTheDocument()
  })

  it("closes on Escape key press", () => {
    render(<MfaRequiredModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })

    expect(screen.getByTestId("mfa-required-modal")).toBeInTheDocument()

    fireEvent.keyDown(window, { key: "Escape" })

    expect(screen.queryByTestId("mfa-required-modal")).not.toBeInTheDocument()
  })

  it("closes when backdrop is clicked", () => {
    render(<MfaRequiredModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })

    expect(screen.getByTestId("mfa-required-modal")).toBeInTheDocument()

    // Click the backdrop (the aria-hidden overlay)
    const backdrop = screen.getByTestId("mfa-required-modal").querySelector("[aria-hidden='true']")
    expect(backdrop).toBeTruthy()
    fireEvent.click(backdrop!)

    expect(screen.queryByTestId("mfa-required-modal")).not.toBeInTheDocument()
  })

  it("has proper dialog role and aria attributes", () => {
    render(<MfaRequiredModal />)

    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })

    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveAttribute("aria-modal", "true")
    expect(dialog).toHaveAttribute("aria-labelledby", "mfa-required-title")
  })

  it("can reopen after being dismissed", () => {
    render(<MfaRequiredModal />)

    // Open
    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })
    expect(screen.getByTestId("mfa-required-modal")).toBeInTheDocument()

    // Dismiss
    fireEvent.click(screen.getByText("Go back"))
    expect(screen.queryByTestId("mfa-required-modal")).not.toBeInTheDocument()

    // Reopen
    act(() => {
      window.dispatchEvent(new CustomEvent("mfa-required"))
    })
    expect(screen.getByTestId("mfa-required-modal")).toBeInTheDocument()
  })
})
