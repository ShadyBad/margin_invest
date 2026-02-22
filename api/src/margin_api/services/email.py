"""Email service for transactional emails via Resend."""

from __future__ import annotations

import logging

import resend

logger = logging.getLogger(__name__)


class EmailService:
    """Sends transactional emails. Uses Resend in production, logs in dev."""

    def __init__(self, *, api_key: str = ""):
        self._dev_mode = not api_key
        if api_key:
            resend.api_key = api_key

    def send_password_reset(self, to_email: str, reset_url: str) -> bool:
        """Send password reset email. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Password reset link for %s: %s", to_email, reset_url)
            return True

        try:
            resend.Emails.send(
                {
                    "from": "Margin Invest <noreply@send.margin-invest.com>",
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
