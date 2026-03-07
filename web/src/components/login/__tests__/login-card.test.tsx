import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { LoginCard } from "../login-card"

const { mockSignIn } = vi.hoisted(() => ({
  mockSignIn: vi.fn(),
}))

vi.mock("next-auth/react", () => ({
  signIn: mockSignIn,
}))

describe("LoginCard", () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    mockSignIn.mockClear()
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  describe("structure", () => {
    it("renders the heading", () => {
      render(<LoginCard />)
      expect(screen.getByRole("heading", { name: /sign in to margin invest/i })).toBeInTheDocument()
    })

    it("renders the sign-in subtext", () => {
      render(<LoginCard />)
      expect(screen.getByText(/access your investment analysis/i)).toBeInTheDocument()
    })

    it("does not render the old register link (replaced by segmented control)", () => {
      render(<LoginCard />)
      expect(screen.queryByRole("link", { name: /create one/i })).not.toBeInTheDocument()
    })
  })

  describe("OAuth icons", () => {
    it("renders Google and GitHub buttons", () => {
      render(<LoginCard />)
      expect(screen.getByLabelText("Sign in with Google")).toBeInTheDocument()
      expect(screen.getByLabelText("Sign in with GitHub")).toBeInTheDocument()
    })

    it("calls signIn with google on Google click", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByLabelText("Sign in with Google"))
      expect(mockSignIn).toHaveBeenCalledWith("google", { callbackUrl: "/dashboard" })
    })

    it("calls signIn with github on GitHub click", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByLabelText("Sign in with GitHub"))
      expect(mockSignIn).toHaveBeenCalledWith("github", { callbackUrl: "/dashboard" })
    })

    it("does not render Apple button", () => {
      render(<LoginCard />)
      expect(screen.queryByLabelText(/sign in with apple/i)).not.toBeInTheDocument()
    })
  })

  describe("credentials form", () => {
    it("shows 'Continue with email →' toggle by default", () => {
      render(<LoginCard />)
      expect(screen.getByText("Continue with email →")).toBeInTheDocument()
    })

    it("shows credentials form when 'Continue with email →' is clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByLabelText("Email")).toBeInTheDocument()
      expect(screen.getByLabelText("Password", { selector: "input" })).toBeInTheDocument()
    })

    it("toggles text to '← Back to social login' when expanded", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByText("← Back to social login")).toBeInTheDocument()
    })

    it("submits credentials with signIn", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      await user.type(screen.getByLabelText("Email"), "testuser")
      await user.type(screen.getByLabelText("Password", { selector: "input" }), "testpass123")
      // Find the form submit button (type="submit"), not the segmented control tab
      const allSignInButtons = screen.getAllByRole("button", { name: /^sign in$/i })
      const formSubmitButton = allSignInButtons.find(btn => btn.getAttribute("type") === "submit")!
      await user.click(formSubmitButton)
      expect(mockSignIn).toHaveBeenCalledWith("credentials", {
        username: "testuser",
        password: "testpass123",
        callbackUrl: "/dashboard",
      })
    })

    it("toggles password visibility", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      const passwordInput = screen.getByLabelText("Password", { selector: "input" })
      expect(passwordInput).toHaveAttribute("type", "password")
      await user.click(screen.getByLabelText("Show password"))
      expect(passwordInput).toHaveAttribute("type", "text")
      await user.click(screen.getByLabelText("Hide password"))
      expect(passwordInput).toHaveAttribute("type", "password")
    })
  })

  describe("sign-up form", () => {
    it("shows confirm password field in sign-up mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument()
    })

    it("does not show confirm password in sign-in mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.queryByLabelText("Confirm Password")).not.toBeInTheDocument()
    })

    it("shows password checklist in sign-up mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByText("At least 12 characters")).toBeInTheDocument()
      expect(screen.getByText("One uppercase letter")).toBeInTheDocument()
      expect(screen.getByText("One lowercase letter")).toBeInTheDocument()
      expect(screen.getByText("One digit")).toBeInTheDocument()
      expect(screen.getByText("One special character")).toBeInTheDocument()
    })

    it("does not show password checklist in sign-in mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.queryByText("At least 12 characters")).not.toBeInTheDocument()
    })

    it("shows 'Create Account' button in sign-up mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument()
    })

    it("uses type=email for email field in sign-up mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByLabelText("Email")).toHaveAttribute("type", "email")
    })
  })

  describe("segmented control", () => {
    it("renders Sign In and Sign Up tabs", () => {
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      expect(within(segmented).getByRole("button", { name: "Sign In" })).toBeInTheDocument()
      expect(within(segmented).getByRole("button", { name: "Sign Up" })).toBeInTheDocument()
    })

    it("defaults to Sign In mode", () => {
      render(<LoginCard />)
      expect(
        screen.getByRole("heading", { name: /sign in to margin invest/i })
      ).toBeInTheDocument()
    })

    it("switches to Sign Up mode when Sign Up tab clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      expect(
        screen.getByRole("heading", { name: /create your account/i })
      ).toBeInTheDocument()
    })

    it("switches back to Sign In mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(within(segmented).getByRole("button", { name: "Sign In" }))
      expect(
        screen.getByRole("heading", { name: /sign in to margin invest/i })
      ).toBeInTheDocument()
    })
  })

  describe("sign-up validation", () => {
    it("shows error when password rules not met on submit", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      await user.type(screen.getByLabelText("Email"), "test@example.com")
      await user.type(screen.getByLabelText("Password", { selector: "input" }), "short")
      await user.type(screen.getByLabelText("Confirm Password"), "short")
      await user.click(screen.getByTestId("tos-checkbox"))
      await user.click(screen.getByRole("button", { name: /create account/i }))
      expect(screen.getByText(/password does not meet all requirements/i)).toBeInTheDocument()
    })

    it("shows error when passwords do not match on submit", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      await user.type(screen.getByLabelText("Email"), "test@example.com")
      await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
      await user.type(screen.getByLabelText("Confirm Password"), "MyPassword1!x")
      await user.click(screen.getByTestId("tos-checkbox"))
      await user.click(screen.getByRole("button", { name: /create account/i }))
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument()
    })

    it("shows confirm password mismatch error on blur", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
      await user.type(screen.getByLabelText("Confirm Password"), "different")
      await user.tab()
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument()
    })
  })

  describe("initialMode prop", () => {
    it("starts in sign-up mode when initialMode is signup", () => {
      render(<LoginCard initialMode="signup" />)
      expect(
        screen.getByRole("heading", { name: /create your account/i })
      ).toBeInTheDocument()
    })
  })

  describe("auth error display", () => {
    it("shows invalid credentials error message", () => {
      render(<LoginCard authError="CredentialsSignin" authCode="invalid_credentials" />)
      expect(screen.getByText("Invalid username or password.")).toBeInTheDocument()
    })

    it("shows API unreachable error message", () => {
      render(<LoginCard authError="CredentialsSignin" authCode="api_unreachable" />)
      expect(screen.getByText(/unable to reach the authentication service/i)).toBeInTheDocument()
    })

    it("shows account locked error message", () => {
      render(<LoginCard authError="CredentialsSignin" authCode="account_locked" />)
      expect(screen.getByText(/account locked/i)).toBeInTheDocument()
    })

    it("auto-expands credentials form when auth error is present", () => {
      render(<LoginCard authError="CredentialsSignin" authCode="invalid_credentials" />)
      expect(screen.getByLabelText("Email")).toBeInTheDocument()
      expect(screen.getByLabelText("Password", { selector: "input" })).toBeInTheDocument()
    })

    it("shows default error for unknown code", () => {
      render(<LoginCard authError="CredentialsSignin" authCode="credentials" />)
      expect(screen.getByText("Invalid username or password.")).toBeInTheDocument()
    })

    it("does not show error when no auth error prop", () => {
      render(<LoginCard />)
      expect(screen.queryByText("Invalid username or password.")).not.toBeInTheDocument()
    })
  })

  describe("ToS acceptance checkbox", () => {
    it("shows ToS checkbox in signup mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByTestId("tos-checkbox")).toBeInTheDocument()
      expect(screen.getByText(/Terms of Service/)).toBeInTheDocument()
      expect(screen.getByText(/Privacy Policy/)).toBeInTheDocument()
    })

    it("does not show ToS checkbox in signin mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.queryByTestId("tos-checkbox")).not.toBeInTheDocument()
    })

    it("Create Account button is disabled when ToS unchecked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByRole("button", { name: /create account/i })).toBeDisabled()
    })

    it("Create Account button is enabled when ToS checked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      await user.click(screen.getByTestId("tos-checkbox"))
      expect(screen.getByRole("button", { name: /create account/i })).not.toBeDisabled()
    })

    it("ToS links point to /terms and /privacy", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      const termsLink = screen.getByRole("link", { name: /terms of service/i })
      const privacyLink = screen.getByRole("link", { name: /privacy policy/i })
      expect(termsLink).toHaveAttribute("href", "/terms")
      expect(privacyLink).toHaveAttribute("href", "/privacy")
    })
  })

  describe("sign-up registration", () => {
    it("calls register API and switches to sign-in on success", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: 1, username: "test@example.com", email: "test@example.com" }),
      })

      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      await user.type(screen.getByLabelText("Email"), "test@example.com")
      await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
      await user.type(screen.getByLabelText("Confirm Password"), "MyPassword1!!")
      await user.click(screen.getByTestId("tos-checkbox"))
      await user.click(screen.getByRole("button", { name: /create account/i }))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith("/api/v1/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: "test@example.com",
            email: "test@example.com",
            password: "MyPassword1!!",
          }),
        })
      })

      await waitFor(() => {
        expect(screen.getByText(/account created/i)).toBeInTheDocument()
      })

      // Should switch back to sign-in mode
      expect(
        screen.getByRole("heading", { name: /sign in to margin invest/i })
      ).toBeInTheDocument()
    })

    it("shows server error on failed registration", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ detail: "A user with this email already exists" }),
      })

      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      await user.type(screen.getByLabelText("Email"), "test@example.com")
      await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
      await user.type(screen.getByLabelText("Confirm Password"), "MyPassword1!!")
      await user.click(screen.getByTestId("tos-checkbox"))
      await user.click(screen.getByRole("button", { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText("A user with this email already exists")).toBeInTheDocument()
      })
    })

    it("shows network error message when fetch fails", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockRejectedValue(new Error("Network error"))

      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      await user.type(screen.getByLabelText("Email"), "test@example.com")
      await user.type(screen.getByLabelText("Password", { selector: "input" }), "MyPassword1!!")
      await user.type(screen.getByLabelText("Confirm Password"), "MyPassword1!!")
      await user.click(screen.getByTestId("tos-checkbox"))
      await user.click(screen.getByRole("button", { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText(/unable to reach the server/i)).toBeInTheDocument()
      })
    })
  })

  describe("forgot password", () => {
    it("shows 'Forgot password?' link in sign-in mode when credentials visible", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.getByText("Forgot password?")).toBeInTheDocument()
    })

    it("does not show 'Forgot password?' in sign-up mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email →"))
      expect(screen.queryByText("Forgot password?")).not.toBeInTheDocument()
    })

    it("switches to reset request form when clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      await user.click(screen.getByText("Forgot password?"))
      expect(screen.getByText("Send reset link")).toBeInTheDocument()
      // Password field should be gone
      expect(screen.queryByLabelText("Password", { selector: "input" })).not.toBeInTheDocument()
    })

    it("returns to sign-in form when 'Back to sign in' clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      await user.click(screen.getByText("Forgot password?"))
      await user.click(screen.getByText("Back to sign in"))
      expect(screen.getByLabelText("Password", { selector: "input" })).toBeInTheDocument()
    })

    it("shows success message after submitting email", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })

      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email →"))
      await user.click(screen.getByText("Forgot password?"))
      await user.type(screen.getByLabelText("Email"), "test@example.com")
      await user.click(screen.getByText("Send reset link"))

      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeInTheDocument()
      })
    })

    it("shows resetSuccess message when prop is true", () => {
      render(<LoginCard resetSuccess={true} />)
      expect(screen.getByText(/password reset successfully/i)).toBeInTheDocument()
    })
  })
})
