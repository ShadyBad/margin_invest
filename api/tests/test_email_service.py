"""Tests for EmailService."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from margin_api.services.email import EmailService


class TestEmailService:
    def test_send_password_reset_calls_resend(self):
        """EmailService calls Resend API with correct params."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            service.send_password_reset(
                to_email="user@example.com",
                reset_url="https://app.test/reset-password?token=abc123",
            )

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert "Reset" in call_args["subject"]
            assert "abc123" in call_args["html"]

    def test_send_password_reset_returns_false_on_error(self):
        """EmailService returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_password_reset(
                to_email="user@example.com",
                reset_url="https://app.test/reset-password?token=abc123",
            )

            assert result is False

    def test_dev_mode_logs_url_when_no_api_key(self):
        """When no API key, logs the URL instead of sending."""
        service = EmailService(api_key="")

        # Should not raise even though there's no real client
        result = service.send_password_reset(
            to_email="user@example.com",
            reset_url="https://app.test/reset-password?token=abc123",
        )

        assert result is True
