"""Test that admin key comparison uses constant-time comparison."""

import hmac

from margin_api.routes.admin import _verify_admin_key


def test_verify_admin_key_uses_hmac_compare_digest(monkeypatch):
    """Verify the function uses hmac.compare_digest, not == operator."""
    # Patch settings to return a known admin key
    from margin_api.config import Settings

    monkeypatch.setattr(
        "margin_api.routes.admin.get_settings",
        lambda: Settings(admin_key="test-admin-key-123"),
    )

    # Valid key should not raise
    _verify_admin_key("test-admin-key-123")

    # Invalid key should raise 403
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _verify_admin_key("wrong-key")
    assert exc_info.value.status_code == 403


def test_verify_admin_key_empty_input(monkeypatch):
    """Empty admin key input should not crash."""
    from margin_api.config import Settings

    monkeypatch.setattr(
        "margin_api.routes.admin.get_settings",
        lambda: Settings(admin_key="test-admin-key-123"),
    )

    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _verify_admin_key("")
    assert exc_info.value.status_code == 403
