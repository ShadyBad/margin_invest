"""Email service for transactional emails via Resend."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Sends transactional emails. Uses Resend in production, logs in dev."""

    def __init__(self, *, api_key: str = ""):
        self._dev_mode = not api_key
        self._api_key = api_key

    def send_password_reset(self, to_email: str, reset_url: str) -> bool:
        """Send password reset email. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Password reset link for %s: %s", to_email, reset_url)
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": "Reset your Margin Invest password",
                    "html": (
                        "<h2>Reset your password</h2>"
                        f'<p><a href="{reset_url}">Click here to reset your password</a></p>'
                        "<p>This link expires in 1 hour.</p>"
                        "<p>If you didn't request this, ignore this email.</p>"
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send password reset email to %s", to_email)
            return False

    def send_welcome(self, to_email: str, name: str) -> bool:
        """Send welcome email to a new user. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Welcome email for %s (%s)", name, to_email)
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": "Welcome to Margin Invest",
                    "html": (
                        f"<h2>Welcome, {name}!</h2>"
                        "<p>We're glad you're here. Start exploring investment insights now.</p>"
                        "<p>If you have any questions, just reply to this email.</p>"
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send welcome email to %s", to_email)
            return False

    def send_onboarding_tips(self, to_email: str, name: str, day: int) -> bool:
        """Send day-N onboarding tips email. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Onboarding tips day %d for %s (%s)", day, name, to_email)
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": f"Day {day} tip: Getting the most from Margin Invest",
                    "html": (
                        f"<h2>Hi {name}, here's your day {day} tip</h2>"
                        "<p>Here are some things to try today to get the"
                        " most out of Margin Invest.</p>"
                        "<p>Happy investing!</p>"
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send onboarding tips email to %s", to_email)
            return False

    def send_payment_received(self, to_email: str, plan: str, amount: str) -> bool:
        """Send payment received confirmation email. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Payment received email for %s: %s %s", to_email, plan, amount)
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": "Payment received — Margin Invest",
                    "html": (
                        "<h2>Payment received</h2>"
                        "<p>Thank you! We received your payment of"
                        f" {amount} for the {plan} plan.</p>"
                        "<p>Your subscription is active and you"
                        " have full access.</p>"
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send payment received email to %s", to_email)
            return False

    def send_payment_failed(self, to_email: str, update_url: str) -> bool:
        """Send payment failed notification email. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Payment failed email for %s, update_url: %s", to_email, update_url)
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": "Action required: payment failed — Margin Invest",
                    "html": (
                        "<h2>We couldn't process your payment</h2>"
                        "<p>Your most recent payment failed. Please update your billing information"
                        " to keep access to Margin Invest.</p>"
                        f'<p><a href="{update_url}">Update payment method</a></p>'
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send payment failed email to %s", to_email)
            return False

    def send_trial_ending(self, to_email: str, days_remaining: int) -> bool:
        """Send trial ending soon notification email. Returns True on success."""
        if self._dev_mode:
            logger.info(
                "[dev] Trial ending email for %s: %d days remaining",
                to_email,
                days_remaining,
            )
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": f"Your trial ends in {days_remaining} days — Margin Invest",
                    "html": (
                        f"<h2>Your trial ends in {days_remaining} days</h2>"
                        "<p>Upgrade now to keep access to all Margin Invest features.</p>"
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send trial ending email to %s", to_email)
            return False

    def send_subscription_cancelled(self, to_email: str) -> bool:
        """Send subscription cancellation confirmation email. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Subscription cancelled email for %s", to_email)
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": "Your subscription has been cancelled — Margin Invest",
                    "html": (
                        "<h2>Subscription cancelled</h2>"
                        "<p>Your Margin Invest subscription has been cancelled."
                        " You'll retain access until the end of your billing period.</p>"
                        "<p>We're sorry to see you go. You're always welcome back.</p>"
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send subscription cancelled email to %s", to_email)
            return False

    def send_weekly_digest(self, to_email: str, digest_data: dict) -> bool:
        """Send weekly digest email with summary data. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Weekly digest email for %s", to_email)
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": "Your weekly Margin Invest digest",
                    "html": (
                        "<h2>Your weekly digest</h2>"
                        "<p>Here's a summary of what happened in your portfolio this week.</p>"
                        f"<pre>{digest_data}</pre>"
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send weekly digest email to %s", to_email)
            return False

    def send_custom(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send a custom transactional email. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Custom email to %s: %s", to_email, subject)
            return True

        try:
            import resend

            resend.api_key = self._api_key
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@margin-invest.com>",
                    "to": to_email,
                    "subject": subject,
                    "html": html_body,
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send custom email to %s", to_email)
            return False
