"""Tests for MFA enforcement middleware."""
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException


class TestCheckMfaRequirement:
    @pytest.mark.asyncio
    async def test_oauth_only_user_passes(self):
        from margin_api.middleware.mfa_enforcement import check_mfa_requirement
        user = MagicMock()
        user.has_password = False
        user.mfa_enabled = False
        user.mfa_grace_deadline = None
        await check_mfa_requirement(user)  # Should not raise

    @pytest.mark.asyncio
    async def test_credential_user_mfa_enabled_passes(self):
        from margin_api.middleware.mfa_enforcement import check_mfa_requirement
        user = MagicMock()
        user.has_password = True
        user.mfa_enabled = True
        user.mfa_grace_deadline = None
        await check_mfa_requirement(user)  # Should not raise

    @pytest.mark.asyncio
    async def test_credential_user_within_grace_passes(self):
        from margin_api.middleware.mfa_enforcement import check_mfa_requirement
        user = MagicMock()
        user.has_password = True
        user.mfa_enabled = False
        user.mfa_grace_deadline = datetime.now(UTC) + timedelta(hours=24)
        await check_mfa_requirement(user)  # Should not raise

    @pytest.mark.asyncio
    async def test_credential_user_past_grace_blocked(self):
        from margin_api.middleware.mfa_enforcement import check_mfa_requirement
        user = MagicMock()
        user.has_password = True
        user.mfa_enabled = False
        user.mfa_grace_deadline = datetime.now(UTC) - timedelta(hours=1)
        with pytest.raises(HTTPException) as exc_info:
            await check_mfa_requirement(user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"] == "mfa_required"

    @pytest.mark.asyncio
    async def test_credential_user_no_grace_deadline_blocked(self):
        from margin_api.middleware.mfa_enforcement import check_mfa_requirement
        user = MagicMock()
        user.has_password = True
        user.mfa_enabled = False
        user.mfa_grace_deadline = None
        with pytest.raises(HTTPException) as exc_info:
            await check_mfa_requirement(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_error_detail_has_correct_message(self):
        from margin_api.middleware.mfa_enforcement import check_mfa_requirement
        user = MagicMock()
        user.has_password = True
        user.mfa_enabled = False
        user.mfa_grace_deadline = None
        with pytest.raises(HTTPException) as exc_info:
            await check_mfa_requirement(user)
        detail = exc_info.value.detail
        assert detail["error"] == "mfa_required"
        assert "Multi-factor authentication" in detail["message"]
