"""Tests for expanded EmailService methods."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from margin_api.services.email import EmailService


class TestSendWelcome:
    def test_calls_resend_with_correct_params(self):
        """send_welcome calls Resend with correct to, subject, and name in html."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_welcome(to_email="user@example.com", name="Alice")

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert call_args["from"] == "Margin Invest <noreply@margin-invest.com>"
            assert "Alice" in call_args["html"]
            assert result is True

    def test_dev_mode_returns_true_without_calling_resend(self):
        """In dev mode, send_welcome returns True without calling Resend."""
        service = EmailService(api_key="")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_welcome(to_email="user@example.com", name="Alice")

            mock_resend.Emails.send.assert_not_called()
            assert result is True

    def test_returns_false_on_resend_error(self):
        """send_welcome returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_welcome(to_email="user@example.com", name="Alice")

            assert result is False


class TestSendOnboardingTips:
    def test_calls_resend_with_correct_params(self):
        """send_onboarding_tips calls Resend with day included in html."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_onboarding_tips(
                to_email="user@example.com", name="Bob", day=3
            )

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert call_args["from"] == "Margin Invest <noreply@margin-invest.com>"
            assert "Bob" in call_args["html"]
            assert "3" in call_args["html"]
            assert result is True

    def test_dev_mode_returns_true_without_calling_resend(self):
        """In dev mode, send_onboarding_tips returns True without calling Resend."""
        service = EmailService(api_key="")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_onboarding_tips(
                to_email="user@example.com", name="Bob", day=3
            )

            mock_resend.Emails.send.assert_not_called()
            assert result is True

    def test_returns_false_on_resend_error(self):
        """send_onboarding_tips returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_onboarding_tips(
                to_email="user@example.com", name="Bob", day=3
            )

            assert result is False


class TestSendPaymentReceived:
    def test_calls_resend_with_correct_params(self):
        """send_payment_received calls Resend with plan and amount in html."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_payment_received(
                to_email="user@example.com", plan="Pro", amount="$29.00"
            )

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert call_args["from"] == "Margin Invest <noreply@margin-invest.com>"
            assert "Pro" in call_args["html"]
            assert "$29.00" in call_args["html"]
            assert result is True

    def test_dev_mode_returns_true_without_calling_resend(self):
        """In dev mode, send_payment_received returns True without calling Resend."""
        service = EmailService(api_key="")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_payment_received(
                to_email="user@example.com", plan="Pro", amount="$29.00"
            )

            mock_resend.Emails.send.assert_not_called()
            assert result is True

    def test_returns_false_on_resend_error(self):
        """send_payment_received returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_payment_received(
                to_email="user@example.com", plan="Pro", amount="$29.00"
            )

            assert result is False


class TestSendPaymentFailed:
    def test_calls_resend_with_correct_params(self):
        """send_payment_failed calls Resend with update_url in html."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_payment_failed(
                to_email="user@example.com",
                update_url="https://app.test/billing/update",
            )

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert call_args["from"] == "Margin Invest <noreply@margin-invest.com>"
            assert "https://app.test/billing/update" in call_args["html"]
            assert result is True

    def test_dev_mode_returns_true_without_calling_resend(self):
        """In dev mode, send_payment_failed returns True without calling Resend."""
        service = EmailService(api_key="")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_payment_failed(
                to_email="user@example.com",
                update_url="https://app.test/billing/update",
            )

            mock_resend.Emails.send.assert_not_called()
            assert result is True

    def test_returns_false_on_resend_error(self):
        """send_payment_failed returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_payment_failed(
                to_email="user@example.com",
                update_url="https://app.test/billing/update",
            )

            assert result is False


class TestSendTrialEnding:
    def test_calls_resend_with_correct_params(self):
        """send_trial_ending calls Resend with days_remaining in html."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_trial_ending(
                to_email="user@example.com", days_remaining=3
            )

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert call_args["from"] == "Margin Invest <noreply@margin-invest.com>"
            assert "3" in call_args["html"]
            assert result is True

    def test_dev_mode_returns_true_without_calling_resend(self):
        """In dev mode, send_trial_ending returns True without calling Resend."""
        service = EmailService(api_key="")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_trial_ending(
                to_email="user@example.com", days_remaining=3
            )

            mock_resend.Emails.send.assert_not_called()
            assert result is True

    def test_returns_false_on_resend_error(self):
        """send_trial_ending returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_trial_ending(
                to_email="user@example.com", days_remaining=3
            )

            assert result is False


class TestSendSubscriptionCancelled:
    def test_calls_resend_with_correct_params(self):
        """send_subscription_cancelled calls Resend with correct params."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_subscription_cancelled(to_email="user@example.com")

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert call_args["from"] == "Margin Invest <noreply@margin-invest.com>"
            assert result is True

    def test_dev_mode_returns_true_without_calling_resend(self):
        """In dev mode, send_subscription_cancelled returns True without calling Resend."""
        service = EmailService(api_key="")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_subscription_cancelled(to_email="user@example.com")

            mock_resend.Emails.send.assert_not_called()
            assert result is True

    def test_returns_false_on_resend_error(self):
        """send_subscription_cancelled returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_subscription_cancelled(to_email="user@example.com")

            assert result is False


class TestSendWeeklyDigest:
    def test_calls_resend_with_correct_params(self):
        """send_weekly_digest calls Resend and passes digest_data into html."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        digest_data = {"top_mover": "AAPL", "score": 95}

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_weekly_digest(
                to_email="user@example.com", digest_data=digest_data
            )

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert call_args["from"] == "Margin Invest <noreply@margin-invest.com>"
            assert result is True

    def test_dev_mode_returns_true_without_calling_resend(self):
        """In dev mode, send_weekly_digest returns True without calling Resend."""
        service = EmailService(api_key="")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_weekly_digest(
                to_email="user@example.com", digest_data={}
            )

            mock_resend.Emails.send.assert_not_called()
            assert result is True

    def test_returns_false_on_resend_error(self):
        """send_weekly_digest returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_weekly_digest(
                to_email="user@example.com", digest_data={}
            )

            assert result is False


class TestSendCustom:
    def test_calls_resend_with_correct_params(self):
        """send_custom calls Resend with the exact subject and html_body provided."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_custom(
                to_email="user@example.com",
                subject="Special announcement",
                html_body="<p>Hello world</p>",
            )

            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == "user@example.com"
            assert call_args["from"] == "Margin Invest <noreply@margin-invest.com>"
            assert call_args["subject"] == "Special announcement"
            assert call_args["html"] == "<p>Hello world</p>"
            assert result is True

    def test_dev_mode_returns_true_without_calling_resend(self):
        """In dev mode, send_custom returns True without calling Resend."""
        service = EmailService(api_key="")
        mock_resend = MagicMock()

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_custom(
                to_email="user@example.com",
                subject="Special announcement",
                html_body="<p>Hello world</p>",
            )

            mock_resend.Emails.send.assert_not_called()
            assert result is True

    def test_returns_false_on_resend_error(self):
        """send_custom returns False when Resend raises."""
        service = EmailService(api_key="re_test_key")
        mock_resend = MagicMock()
        mock_resend.Emails.send.side_effect = Exception("API error")

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = service.send_custom(
                to_email="user@example.com",
                subject="Special announcement",
                html_body="<p>Hello world</p>",
            )

            assert result is False
