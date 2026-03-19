import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import AdminLoginPage from "../page"

// Mock next/navigation
const mockPush = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}))

describe("AdminLoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  // ── Render ────────────────────────────────────────────────────────────────

  it("renders the admin login page", () => {
    render(<AdminLoginPage />)
    expect(screen.getByTestId("admin-login-page")).toBeInTheDocument()
  })

  it("renders 'Admin Console' heading", () => {
    render(<AdminLoginPage />)
    expect(screen.getByText("Admin Console")).toBeInTheDocument()
  })

  it("renders email and password inputs on step 1", () => {
    render(<AdminLoginPage />)
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it("renders the credentials form on step 1", () => {
    render(<AdminLoginPage />)
    expect(screen.getByTestId("credentials-form")).toBeInTheDocument()
  })

  it("renders 'Continue' button on step 1", () => {
    render(<AdminLoginPage />)
    expect(screen.getByRole("button", { name: /continue/i })).toBeInTheDocument()
  })

  it("does not render the MFA form on initial load", () => {
    render(<AdminLoginPage />)
    expect(screen.queryByTestId("mfa-form")).not.toBeInTheDocument()
  })

  // ── Step 1 → Step 2 transition ────────────────────────────────────────────

  it("advances to MFA step when credentials succeed with mfa_required", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ mfa_required: true, challenge_str: "jwt-challenge" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    )

    const user = userEvent.setup()
    render(<AdminLoginPage />)

    await user.type(screen.getByLabelText(/email/i), "admin@example.com")
    await user.type(screen.getByLabelText(/password/i), "secret")
    await user.click(screen.getByRole("button", { name: /continue/i }))

    await waitFor(() => {
      expect(screen.getByTestId("mfa-form")).toBeInTheDocument()
    })
    expect(screen.queryByTestId("credentials-form")).not.toBeInTheDocument()
  })

  it("redirects directly to /admin/approvals when credentials succeed without mfa_required", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ mfa_required: false }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    )

    const user = userEvent.setup()
    render(<AdminLoginPage />)

    await user.type(screen.getByLabelText(/email/i), "admin@example.com")
    await user.type(screen.getByLabelText(/password/i), "secret")
    await user.click(screen.getByRole("button", { name: /continue/i }))

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/admin/approvals")
    })
  })

  // ── Step 1 error handling ─────────────────────────────────────────────────

  it("shows error banner on 401 from credentials endpoint", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid credentials" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    )

    const user = userEvent.setup()
    render(<AdminLoginPage />)

    await user.type(screen.getByLabelText(/email/i), "admin@example.com")
    await user.type(screen.getByLabelText(/password/i), "wrong")
    await user.click(screen.getByRole("button", { name: /continue/i }))

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeInTheDocument()
    })
    expect(screen.getByTestId("error-banner")).toHaveTextContent("Invalid credentials")
  })

  it("shows error banner on network failure at step 1", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network error"))

    const user = userEvent.setup()
    render(<AdminLoginPage />)

    await user.type(screen.getByLabelText(/email/i), "admin@example.com")
    await user.type(screen.getByLabelText(/password/i), "secret")
    await user.click(screen.getByRole("button", { name: /continue/i }))

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeInTheDocument()
    })
    expect(screen.getByTestId("error-banner")).toHaveTextContent(
      "Unable to reach the server"
    )
  })

  // ── Step 2: MFA form ──────────────────────────────────────────────────────

  it("renders TOTP code input and Verify button on step 2", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ mfa_required: true, challenge_str: "jwt-challenge" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    )

    const user = userEvent.setup()
    render(<AdminLoginPage />)

    await user.type(screen.getByLabelText(/email/i), "admin@example.com")
    await user.type(screen.getByLabelText(/password/i), "secret")
    await user.click(screen.getByRole("button", { name: /continue/i }))

    await waitFor(() => {
      expect(screen.getByLabelText(/totp code/i)).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: /verify/i })).toBeInTheDocument()
  })

  it("submits TOTP code to admin-mfa-complete and redirects on success", async () => {
    // Step 1 succeeds
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ mfa_required: true, challenge_str: "jwt-challenge" }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      // Step 2 succeeds
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ success: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )

    const user = userEvent.setup()
    render(<AdminLoginPage />)

    // Complete step 1
    await user.type(screen.getByLabelText(/email/i), "admin@example.com")
    await user.type(screen.getByLabelText(/password/i), "secret")
    await user.click(screen.getByRole("button", { name: /continue/i }))

    await waitFor(() => {
      expect(screen.getByTestId("mfa-form")).toBeInTheDocument()
    })

    // Complete step 2
    await user.type(screen.getByLabelText(/totp code/i), "123456")
    await user.click(screen.getByRole("button", { name: /verify/i }))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining("/api/v1/auth/admin-mfa-complete"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ totp_code: "123456", challenge_str: "jwt-challenge" }),
        })
      )
    })

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/admin/approvals")
    })
  })

  it("shows error on MFA failure", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ mfa_required: true, challenge_str: "jwt-challenge" }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Invalid TOTP code" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        })
      )

    const user = userEvent.setup()
    render(<AdminLoginPage />)

    await user.type(screen.getByLabelText(/email/i), "admin@example.com")
    await user.type(screen.getByLabelText(/password/i), "secret")
    await user.click(screen.getByRole("button", { name: /continue/i }))

    await waitFor(() => {
      expect(screen.getByTestId("mfa-form")).toBeInTheDocument()
    })

    await user.type(screen.getByLabelText(/totp code/i), "000000")
    await user.click(screen.getByRole("button", { name: /verify/i }))

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toHaveTextContent("Invalid TOTP code")
    })
  })

  it("returns to step 1 when Back to credentials is clicked", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ mfa_required: true, challenge_str: "jwt-challenge" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    )

    const user = userEvent.setup()
    render(<AdminLoginPage />)

    await user.type(screen.getByLabelText(/email/i), "admin@example.com")
    await user.type(screen.getByLabelText(/password/i), "secret")
    await user.click(screen.getByRole("button", { name: /continue/i }))

    await waitFor(() => {
      expect(screen.getByTestId("mfa-form")).toBeInTheDocument()
    })

    await user.click(screen.getByRole("button", { name: /back to credentials/i }))

    await waitFor(() => {
      expect(screen.getByTestId("credentials-form")).toBeInTheDocument()
    })
    expect(screen.queryByTestId("mfa-form")).not.toBeInTheDocument()
  })
})
