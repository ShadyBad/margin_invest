import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ConfirmationModal } from "../confirmation-modal"

describe("ConfirmationModal", () => {
  const defaultProps = {
    open: true,
    title: "Confirm Action",
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    confirmLabel: "Remove",
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders title and description", () => {
    render(
      <ConfirmationModal
        {...defaultProps}
        description="Are you sure you want to proceed?"
      />
    )
    expect(screen.getByText("Confirm Action")).toBeInTheDocument()
    expect(screen.getByText("Are you sure you want to proceed?")).toBeInTheDocument()
  })

  it("renders nothing when open=false", () => {
    const { container } = render(
      <ConfirmationModal {...defaultProps} open={false} />
    )
    expect(container.innerHTML).toBe("")
  })

  it("renders input fields when provided", () => {
    render(
      <ConfirmationModal
        {...defaultProps}
        fields={[
          { name: "password", label: "Current Password", type: "password" },
          { name: "reason", label: "Reason", type: "text" },
        ]}
      />
    )
    expect(screen.getByLabelText("Current Password")).toBeInTheDocument()
    expect(screen.getByLabelText("Reason")).toBeInTheDocument()
    expect(screen.getByLabelText("Current Password")).toHaveAttribute("type", "password")
    expect(screen.getByLabelText("Reason")).toHaveAttribute("type", "text")
  })

  it("calls onConfirm with field values on submit", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <ConfirmationModal
        {...defaultProps}
        onConfirm={onConfirm}
        fields={[
          { name: "password", label: "Current Password", type: "password" },
        ]}
      />
    )

    await user.type(screen.getByLabelText("Current Password"), "MySecret123!")
    await user.click(screen.getByRole("button", { name: /remove/i }))

    expect(onConfirm).toHaveBeenCalledWith({ password: "MySecret123!" })
  })

  it("calls onClose on Cancel click", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ConfirmationModal {...defaultProps} onClose={onClose} />)

    await user.click(screen.getByRole("button", { name: /cancel/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it("calls onClose on backdrop click", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ConfirmationModal {...defaultProps} onClose={onClose} />)

    await user.click(screen.getByTestId("modal-backdrop"))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it("disables confirm button when loading", () => {
    render(<ConfirmationModal {...defaultProps} loading={true} />)
    const confirmBtn = screen.getByRole("button", { name: /removing/i })
    expect(confirmBtn).toBeDisabled()
  })

  it("shows error message", () => {
    render(
      <ConfirmationModal {...defaultProps} error="Something went wrong" />
    )
    expect(screen.getByText("Something went wrong")).toBeInTheDocument()
  })

  it("has correct accessibility attributes", () => {
    render(<ConfirmationModal {...defaultProps} />)
    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveAttribute("aria-modal", "true")
    expect(dialog).toHaveAttribute("aria-labelledby", "modal-title")
  })

  it("calls onClose on Escape key", () => {
    const onClose = vi.fn()
    render(<ConfirmationModal {...defaultProps} onClose={onClose} />)
    fireEvent.keyDown(document, { key: "Escape" })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it("calls onConfirm with empty object when no fields", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(<ConfirmationModal {...defaultProps} onConfirm={onConfirm} />)

    await user.click(screen.getByRole("button", { name: /remove/i }))
    expect(onConfirm).toHaveBeenCalledWith({})
  })

  it("uses danger variant styling when confirmVariant is danger", () => {
    render(<ConfirmationModal {...defaultProps} confirmVariant="danger" />)
    const confirmBtn = screen.getByRole("button", { name: /remove/i })
    expect(confirmBtn.className).toMatch(/bg-red-500/)
  })

  it("uses accent variant styling by default", () => {
    render(<ConfirmationModal {...defaultProps} />)
    const confirmBtn = screen.getByRole("button", { name: /remove/i })
    expect(confirmBtn.className).toMatch(/bg-accent/)
  })

  it("resets field values when modal opens", async () => {
    const user = userEvent.setup()
    const { rerender } = render(
      <ConfirmationModal
        {...defaultProps}
        fields={[
          { name: "password", label: "Password", type: "password" },
        ]}
      />
    )

    await user.type(screen.getByLabelText("Password"), "typed-value")
    expect(screen.getByLabelText("Password")).toHaveValue("typed-value")

    // Close and re-open
    rerender(
      <ConfirmationModal
        {...defaultProps}
        open={false}
        fields={[
          { name: "password", label: "Password", type: "password" },
        ]}
      />
    )
    rerender(
      <ConfirmationModal
        {...defaultProps}
        open={true}
        fields={[
          { name: "password", label: "Password", type: "password" },
        ]}
      />
    )

    expect(screen.getByLabelText("Password")).toHaveValue("")
  })

  it("uses field input ids with modal- prefix", () => {
    render(
      <ConfirmationModal
        {...defaultProps}
        fields={[
          { name: "password", label: "Password", type: "password" },
        ]}
      />
    )
    expect(screen.getByLabelText("Password")).toHaveAttribute("id", "modal-password")
  })

  it("does not propagate backdrop click to dialog", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ConfirmationModal {...defaultProps} onClose={onClose} />)

    // Clicking the dialog card itself should NOT trigger onClose
    await user.click(screen.getByRole("dialog"))
    expect(onClose).not.toHaveBeenCalled()
  })

  it("transforms confirm label to -ing form when loading", () => {
    render(<ConfirmationModal {...defaultProps} confirmLabel="Delete" loading={true} />)
    expect(screen.getByRole("button", { name: /deleting/i })).toBeInTheDocument()
  })
})
