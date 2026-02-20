"""Tests for ErrorResponse schema."""

from __future__ import annotations

from margin_api.schemas.errors import ErrorResponse


class TestErrorResponse:
    def test_model_fields(self):
        err = ErrorResponse(
            error_code="SCORE_NOT_FOUND",
            message="No score found for XYZ",
            request_id="abc-123",
            status_code=404,
        )
        assert err.error_code == "SCORE_NOT_FOUND"
        assert err.message == "No score found for XYZ"
        assert err.detail == "No score found for XYZ"
        assert err.request_id == "abc-123"
        assert err.status_code == 404

    def test_detail_synced_from_message(self):
        err = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            request_id="def-456",
            status_code=500,
        )
        assert err.detail == "An unexpected error occurred."

    def test_model_dump(self):
        err = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            request_id="def-456",
            status_code=500,
        )
        d = err.model_dump()
        assert d == {
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.",
            "detail": "An unexpected error occurred.",
            "request_id": "def-456",
            "status_code": 500,
        }
